"""
RAG (Retrieval-Augmented Generation) engine for the DementiaNext Companion.

Uses ChromaDB with sentence-transformers to embed curated dementia clinical
knowledge and retrieve relevant passages at query time, grounding LLM
responses in verified medical information.

Mode-aware dual collections:
  - caregiver: all knowledge files, larger chunks, more results (clinical depth)
  - patient:   scenario/emotional files only, smaller chunks, fewer results
"""

import hashlib
import logging
import os
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

logger = logging.getLogger(__name__)

# Default Chroma ONNX embedder uses `np.iterable`, removed in NumPy 2.x, and can
# break under some SciPy / NumPy import orders. SentenceTransformer matches FAQ.
_EMBED_FN_CACHE: SentenceTransformerEmbeddingFunction | None = None
_EMBED_META_KEY = "embed_fn"
_EMBED_META_VAL = "st_minilm_v6"


def _get_chroma_embed_fn() -> SentenceTransformerEmbeddingFunction:
    global _EMBED_FN_CACHE
    if _EMBED_FN_CACHE is None:
        _EMBED_FN_CACHE = SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2",
        )
    return _EMBED_FN_CACHE

_KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge_base"
_CHROMA_DIR = Path(__file__).resolve().parent.parent / ".chroma_db"

# --- mode-specific settings ------------------------------------------------

_MODE_CONFIG = {
    "caregiver": {
        "collection": "dementia_knowledge_caregiver",
        "chunk_size": 800,
        "chunk_overlap": 100,
        "default_n": 8,
        # include all txt files
        "include_files": None,  # None == all
    },
    "patient": {
        "collection": "dementia_knowledge_patient",
        "chunk_size": 400,
        "chunk_overlap": 60,
        "default_n": 3,
        # only emotional / scenario / communication files
        "include_files": {
            "01_dementia_stages.txt",
            "04_communication_therapy.txt",
            "06_patient_specific_scenarios.txt",
            "07_caregiver_emotional_support.txt",
        },
    },
}

_collections: dict[str, object] = {}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split *text* into overlapping chunks by paragraph boundaries."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 > chunk_size and current:
            chunks.append(current.strip())
            words = current.split()
            overlap_words = words[-overlap // 4:] if len(words) > overlap // 4 else []
            current = " ".join(overlap_words) + "\n\n" + para
        else:
            current = (current + "\n\n" + para).strip()

    if current.strip():
        chunks.append(current.strip())

    return chunks


def _file_content_hash(directory: Path, include_files: set[str] | None) -> str:
    """Hash knowledge-base files that belong to a given collection."""
    h = hashlib.sha256()
    for fpath in sorted(directory.glob("*.txt")):
        if include_files is not None and fpath.name not in include_files:
            continue
        h.update(fpath.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# collection management
# ---------------------------------------------------------------------------

def _get_collection(mode: str = "caregiver"):
    """Return the ChromaDB collection for *mode*, building the index if needed."""
    global _collections

    cfg = _MODE_CONFIG.get(mode, _MODE_CONFIG["caregiver"])
    col_name = cfg["collection"]
    include_files = cfg["include_files"]
    chunk_size = cfg["chunk_size"]
    chunk_overlap = cfg["chunk_overlap"]

    os.makedirs(_CHROMA_DIR, exist_ok=True)

    settings = ChromaSettings(
        anonymized_telemetry=False,
        allow_reset=True,
    )

    try:
        client = chromadb.PersistentClient(path=str(_CHROMA_DIR), settings=settings)
    except Exception:
        import shutil
        shutil.rmtree(_CHROMA_DIR, ignore_errors=True)
        os.makedirs(_CHROMA_DIR, exist_ok=True)
        client = chromadb.PersistentClient(path=str(_CHROMA_DIR), settings=settings)

    current_hash_probe = _file_content_hash(_KNOWLEDGE_DIR, include_files)
    if mode in _collections:
        cached = _collections[mode]
        cmeta = getattr(cached, "metadata", None) or {}
        if (
            cmeta.get(_EMBED_META_KEY) == _EMBED_META_VAL
            and cmeta.get("content_hash") == current_hash_probe
        ):
            return cached

    existing = [c.name for c in client.list_collections()]
    needs_rebuild = col_name not in existing

    if not needs_rebuild:
        col = client.get_collection(col_name)
        meta = col.metadata or {}
        stored_hash = meta.get("content_hash", "")
        stored_embed = meta.get(_EMBED_META_KEY, "")
        current_hash = current_hash_probe
        if stored_hash != current_hash or stored_embed != _EMBED_META_VAL:
            client.delete_collection(col_name)
            _collections.pop(mode, None)
            needs_rebuild = True

    if needs_rebuild:
        logger.info("Building RAG index [%s] from %s …", col_name, _KNOWLEDGE_DIR)
        current_hash = _file_content_hash(_KNOWLEDGE_DIR, include_files)

        col = client.create_collection(
            name=col_name,
            metadata={
                "content_hash": current_hash,
                _EMBED_META_KEY: _EMBED_META_VAL,
            },
            embedding_function=_get_chroma_embed_fn(),
        )

        all_docs: list[str] = []
        all_ids: list[str] = []
        all_meta: list[dict] = []

        for fpath in sorted(_KNOWLEDGE_DIR.glob("*.txt")):
            if include_files is not None and fpath.name not in include_files:
                continue
            text = fpath.read_text(encoding="utf-8")
            source = fpath.stem
            chunks = _chunk_text(text, chunk_size, chunk_overlap)

            for i, chunk in enumerate(chunks):
                doc_id = f"{col_name}__{source}__chunk_{i}"
                all_docs.append(chunk)
                all_ids.append(doc_id)
                all_meta.append({
                    "source": source,
                    "source_file": fpath.name,
                    "chunk_index": i,
                    "mode": mode,
                })

        if all_docs:
            batch = 40
            for start in range(0, len(all_docs), batch):
                col.add(
                    documents=all_docs[start:start + batch],
                    ids=all_ids[start:start + batch],
                    metadatas=all_meta[start:start + batch],
                )

        logger.info(
            "RAG index [%s] built: %d chunks from %d files.",
            col_name, len(all_docs),
            len([f for f in _KNOWLEDGE_DIR.glob("*.txt")
                 if include_files is None or f.name in include_files]),
        )

    col = client.get_collection(col_name)
    _collections[mode] = col
    return col


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def retrieve(query: str, mode: str = "caregiver", n_results: int | None = None) -> str:
    """
    Retrieve the most relevant knowledge passages for *query*.

    *mode* selects the collection (caregiver → clinical depth, patient →
    concise emotional).  Returns a formatted string ready for injection into
    the LLM system prompt.
    """
    cfg = _MODE_CONFIG.get(mode, _MODE_CONFIG["caregiver"])
    if n_results is None:
        n_results = cfg["default_n"]

    try:
        col = _get_collection(mode)
    except Exception:
        logger.exception("Failed to initialise RAG collection [%s]", mode)
        return ""

    try:
        results = col.query(query_texts=[query], n_results=n_results)
    except Exception:
        logger.exception("RAG query failed for: %s", query[:80])
        return ""

    if not results or not results["documents"] or not results["documents"][0]:
        return ""

    passages: list[str] = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        source = meta.get("source", "unknown").replace("_", " ").title()
        passages.append(f"[{source}]\n{doc}")

    if mode == "caregiver":
        header = (
            "REFERENCE KNOWLEDGE (base ALL clinical answers, medication "
            "information, behavioral protocols, and care recommendations on "
            "this material ONLY — do NOT fabricate statistics, dosages, or "
            "care protocols):"
        )
    else:
        header = (
            "REFERENCE KNOWLEDGE (this is your INTERNAL BEHAVIORAL GUIDANCE "
            "on how to navigate this conversation — DO NOT quote this text "
            "verbatim to the patient, but follow its principles):"
        )

    return header + "\n\n" + "\n\n---\n\n".join(passages)


def warm_up():
    """Pre-load both collections at app startup."""
    for mode in ("caregiver", "patient"):
        try:
            col = _get_collection(mode)
            logger.info(
                "RAG engine [%s] ready — %d documents indexed.", mode, col.count()
            )
        except Exception:
            logger.exception(
                "RAG warm-up [%s] failed; will retry on first query.", mode
            )
