"""
Pipeline Web Adapter
====================

Thin wrapper around Phase 1 (MRIPreprocessor) and Phase 2
(MRIPreprocessorPhase2) that preprocesses a *single* uploaded MRI file
through the full pipeline and returns the path to the ML-ready result.

Supported input formats
-----------------------
- .dcm         → Phase 1 (DICOM → NIfTI) → Phase 2 (steps 4-8)
- .zip          → extract, Phase 1 → Phase 2
- .nii / .nii.gz → Phase 2 only (already NIfTI)

Usage from views.py
-------------------
    from pipeline.preprocess import preprocess_mri
    preprocessed_path = preprocess_mri("/path/to/upload.dcm")
"""

import os
import sys
import shutil
import zipfile
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PIPELINE_DIR = Path(__file__).resolve().parent


def _add_pipeline_to_path():
    if str(_PIPELINE_DIR) not in sys.path:
        sys.path.insert(0, str(_PIPELINE_DIR))


def _run_phase1(dicom_dir: Path, work_dir: Path) -> Path:
    """Run Phase 1: DICOM → NIfTI → BIDS. Returns path to the BIDS NIfTI."""
    _add_pipeline_to_path()
    from phase1_preprocessing import MRIPreprocessor

    phase1_out = work_dir / "phase1"
    phase1_out.mkdir(parents=True, exist_ok=True)

    proc = MRIPreprocessor(
        input_dir=str(dicom_dir),
        output_dir=str(phase1_out),
    )

    nifti_files = proc.convert_to_nifti()
    if not nifti_files:
        raise RuntimeError(
            "Phase 1 failed: no NIfTI files produced from DICOM input"
        )

    proc.organize_bids(nifti_files)

    bids_niftis = sorted(phase1_out.joinpath("bids_structure").rglob("*.nii.gz"))
    if bids_niftis:
        return bids_niftis[0]
    return Path(nifti_files[0])


def _run_phase2(nifti_path: Path, work_dir: Path) -> Path:
    """Run Phase 2 steps 4-8 on a single NIfTI. Returns resampled 128³ path."""
    _add_pipeline_to_path()
    from phase2_preprocessing import MRIPreprocessorPhase2

    phase2_out = work_dir / "phase2"
    phase2_out.mkdir(parents=True, exist_ok=True)

    proc = MRIPreprocessorPhase2(
        input_dir=str(work_dir / "phase1"),
        output_dir=str(phase2_out),
    )

    files = [nifti_path]

    logger.info("Pipeline step 4: skull stripping")
    skull_stripped = proc.skull_stripping(files)
    if not skull_stripped:
        raise RuntimeError("Skull stripping produced no output")

    logger.info("Pipeline step 5: bias field correction")
    bias_corrected = proc.bias_field_correction(skull_stripped)
    if not bias_corrected:
        raise RuntimeError("Bias field correction produced no output")

    logger.info("Pipeline step 6: spatial normalization")
    normalized = proc.spatial_normalization(bias_corrected)
    if not normalized:
        raise RuntimeError("Spatial normalization produced no output")

    logger.info("Pipeline step 7: intensity normalization")
    intensity_normed = proc.intensity_normalization(normalized)
    if not intensity_normed:
        raise RuntimeError("Intensity normalization produced no output")

    logger.info("Pipeline step 8: resampling to 128³")
    resampled = proc.spatial_resampling(intensity_normed)
    if not resampled:
        raise RuntimeError("Spatial resampling produced no output")

    return Path(resampled[0])


def _prepare_dicom_dir(upload_path: Path, work_dir: Path) -> Path:
    """Ensure we have a directory of DICOM files ready for Phase 1.

    Handles two cases:
      - single .dcm file  → copy into a temp dir
      - .zip archive      → extract into a temp dir
    """
    dicom_dir = work_dir / "dicom_input"
    dicom_dir.mkdir(parents=True, exist_ok=True)

    if upload_path.suffix.lower() == ".zip":
        logger.info("Extracting ZIP archive: %s", upload_path.name)
        with zipfile.ZipFile(upload_path, "r") as zf:
            zf.extractall(dicom_dir)
    else:
        shutil.copy2(upload_path, dicom_dir / upload_path.name)

    return dicom_dir


def preprocess_mri(input_path: str, output_dir: str | None = None) -> str:
    """
    Run the full preprocessing pipeline on a single uploaded file.

    Parameters
    ----------
    input_path : str
        Absolute path to the uploaded file (.dcm, .zip, .nii, .nii.gz).
    output_dir : str, optional
        Working directory for intermediate files.  Defaults to a
        ``pipeline_work`` folder next to the input file.

    Returns
    -------
    str
        Absolute path to the final preprocessed NIfTI (128×128×128).

    Raises
    ------
    FileNotFoundError
        If input_path does not exist.
    RuntimeError
        If any pipeline step fails.
    """
    input_path = Path(input_path).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    work_dir = Path(output_dir) if output_dir else input_path.parent / "pipeline_work"
    work_dir.mkdir(parents=True, exist_ok=True)

    fname = input_path.name.lower()
    is_dicom = fname.endswith(".dcm") or fname.endswith(".zip")
    is_nifti = fname.endswith(".nii") or fname.endswith(".nii.gz")

    logger.info("Pipeline: input=%s  format=%s",
                input_path.name,
                "DICOM" if is_dicom else "NIfTI" if is_nifti else "unknown")

    if is_dicom:
        # Phase 1: DICOM → NIfTI
        dicom_dir = _prepare_dicom_dir(input_path, work_dir)
        nifti_path = _run_phase1(dicom_dir, work_dir)
        logger.info("Phase 1 complete → %s", nifti_path)
    elif is_nifti:
        nifti_path = input_path
    else:
        raise RuntimeError(f"Unsupported format for pipeline: {input_path.name}")

    # Phase 2: skull strip → bias → MNI → intensity norm → resample
    result = _run_phase2(nifti_path, work_dir)
    logger.info("Pipeline complete → %s", result)
    return str(result)
