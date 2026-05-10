#!/usr/bin/env python3
"""
MRI Preprocessing Pipeline - Phase 1: Data Preparation
Simple implementation for DICOM to NIfTI conversion, BIDS organization, and quality assessment.
"""

import sys
import io
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import os
import json
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import nibabel as nib
import pydicom
from tqdm import tqdm
from typing import List, Dict

class SeriesSelector:
    """Integrated series selector for automatic series selection."""
    
    def __init__(self, dataset_name: str, output_dir: str = None):
        self.dataset_name = dataset_name
        self.output_dir = output_dir
        self.optimal_series = self._get_optimal_series_criteria()
    
    def _detect_image_type_from_series(self, dicom_file_path: str) -> str:
        """Detect if the series is 2D or 3D based on DICOM metadata."""
        try:
            import pydicom
            ds = pydicom.dcmread(dicom_file_path)
            
            # Check slice thickness and number of slices
            slice_thickness = getattr(ds, 'SliceThickness', None)
            num_slices = len(list(Path(dicom_file_path).parent.glob('*.dcm')))
            
            # Check series description for 2D indicators
            series_desc = getattr(ds, 'SeriesDescription', '').upper()
            is_2d_indicator = any(indicator in series_desc for indicator in [
                '2D', 'SINGLE SLICE', 'SLICE', 'AXIAL 2D', 'SAG 2D', 'COR 2D', 'GRE-MT'
            ])
            
            # Heuristic: if series description indicates 2D or very few slices
            # Also check if it's a GRE-MT sequence (typically 2D)
            if is_2d_indicator or num_slices < 20:
                return '2D'
            else:
                return '3D'
                
        except Exception:
            # Fallback: assume 3D if we can't determine
            return '3D'
    
    def _get_optimal_series_criteria(self) -> Dict:
        """Define optimal series criteria based on dataset."""
        if self.dataset_name.upper() == 'PPMI':
            return {
                "optimal": {
                    "series_descriptions": [
                        "SAG 3D MPRAGE",  # BEST CHOICE - PPMI standard
                        "MPRAGE", 
                        "T1 MPRAGE",
                        "3D MPRAGE",
                        "SAG MPRAGE"
                    ],
                    "weighting": "T1",
                    "slice_thickness_max": 1.5,
                    "acquisition_plane": ["SAGITTAL", "AXIAL"],
                    "priority_score": 100,
                    "disease_suitability": "EXCELLENT",
                    "reasoning": "Single series sufficient for 90-95% Parkinson's classification accuracy"
                },
                "fallback": {
                    "series_descriptions": [
                        "AX T2 GRE MT",
                        "T2 GRE MT",
                        "T2* GRE",
                        "T2 GRE"
                    ],
                    "weighting": "T1",
                    "slice_thickness_max": 2.0,
                    "acquisition_plane": ["AXIAL"],
                    "priority_score": 70,
                    "disease_suitability": "GOOD",
                    "reasoning": "Use only if MPRAGE unavailable"
                }
            }
        elif self.dataset_name.upper() == 'ADNI':
            return {
                "optimal": {
                    "series_descriptions": [
                        "Accelerated Sagittal MPRAGE (MSV22)",  # BEST - 1.0mm resolution
                        "HS Sagittal MPRAGE (MSV22)",          # BEST - 1.0mm resolution  
                        "Accelerated Sagittal MPRAGE (MSV21)", # BEST - 1.0mm resolution
                        "MP-RAGE",                              # EXCELLENT - 1.2mm resolution
                        "MP-RAGE REPEAT",                       # EXCELLENT - 1.2mm resolution
                        "MPRAGE Repeat",                        # EXCELLENT - variant
                        "Sagittal MPRAGE",                      # EXCELLENT - standard
                        "T1 MPRAGE"                             # EXCELLENT - generic
                    ],
                    "weighting": "T1",
                    "slice_thickness_max": 1.5,
                    "acquisition_plane": ["SAGITTAL"],
                    "priority_score": 100,
                    "disease_suitability": "EXCELLENT",
                    "reasoning": "Single series sufficient for 90-95% Alzheimer's classification accuracy"
                },
                "fallback": {
                    "series_descriptions": [
                        "3-pl T2* FGRE",
                        "T2* FGRE",
                        "T2 FLAIR",
                        "FLAIR"
                    ],
                    "weighting": "T1",
                    "slice_thickness_max": 3.0,
                    "acquisition_plane": ["AXIAL", "SAGITTAL"],
                    "priority_score": 70,
                    "disease_suitability": "GOOD",
                    "reasoning": "Use only if MPRAGE unavailable"
                }
            }
        else:  # OASIS or other
            return {
                "optimal": {
                    "series_descriptions": [
                        "MPRAGE",
                        "T1 MPRAGE",
                        "Sagittal MPRAGE",
                        "3D MPRAGE"
                    ],
                    "weighting": "T1",
                    "slice_thickness_max": 1.5,
                    "acquisition_plane": ["SAGITTAL", "AXIAL"],
                    "priority_score": 100,
                    "disease_suitability": "EXCELLENT",
                    "reasoning": "Single series sufficient for general analysis"
                }
            }
    
    def select_optimal_series(self, dicom_files: List[Path], keep_all_repeats: bool = False) -> List[Path]:
        """Select optimal series from DICOM files and print availability.
        keep_all_repeats=False will pick the single best group for the chosen label.
        """
        selected_files = []
        series_scores = {}
        
        # Group files by series (robust to missing DICOM metadata). Use DICOM when possible, otherwise folder-based grouping.
        series_groups = {}
        for dcm_file in dicom_files:
            dicom_descriptor = ''
            series_uid = ''
            try:
                ds = pydicom.dcmread(dcm_file, stop_before_pixels=True)
                # Build a robust, text-based descriptor using multiple DICOM tags
                series_desc = getattr(ds, 'SeriesDescription', '') or ''
                protocol = getattr(ds, 'ProtocolName', '') or ''
                seq_name = getattr(ds, 'SequenceName', '') or ''
                scan_seq = getattr(ds, 'ScanningSequence', '') or ''
                image_type = ' '.join(getattr(ds, 'ImageType', []) or [])
                dicom_descriptor = ' '.join([series_desc, protocol, seq_name, scan_seq, image_type]).strip()
                series_uid = getattr(ds, 'SeriesInstanceUID', '') or ''
            except Exception:
                pass

            # Derive series name from folder structure: walk up until a human-readable series folder (with letters)
            folder_series = ''
            folder_uid = ''
            try:
                def looks_like_meta(name: str) -> bool:
                    n = name.upper()
                    # numeric-only or scanner IDs like I12345678
                    if n.startswith('I') and n[1:].isdigit():
                        return True
                    if n.isdigit():
                        return True
                    # timestamp-like: contains many digits and separators
                    digits = sum(ch.isdigit() for ch in n)
                    if digits >= max(4, len(n)//2):
                        return True
                    return False

                parent = dcm_file.parent
                folder_uid = parent.name if parent else ''
                # try up to 5 levels up to find a name with alphabetic characters
                steps = 0
                while parent is not None and steps < 5:
                    name = parent.name or ''
                    if any(ch.isalpha() for ch in name) and not looks_like_meta(name):
                        folder_series = name
                        break
                    parent = parent.parent
                    steps += 1
                # fallback to immediate parent name
                if not folder_series and dcm_file.parent:
                    folder_series = dcm_file.parent.name
            except Exception:
                pass

            # Compose final descriptor and uid
            descriptor = (dicom_descriptor or folder_series or 'unknown')
            use_uid = series_uid or folder_uid or 'unknown'
            key = f"{descriptor}_{use_uid}"

            if key not in series_groups:
                series_groups[key] = {
                    'files': [],
                    'description': descriptor,
                    'uid': use_uid
                }
            series_groups[key]['files'].append(dcm_file)
        
        # Score each series and compute a canonical label so all repeats are kept
        def canonical_label(desc: str) -> str:
            d = desc.upper()
            for a, b in [("_", " "), ("-", " "), ("  ", " ")]:
                d = d.replace(a, b)
            if any(tok in d for tok in ["MPRAGE", "MP RAGE"]) or ("SAG" in d and "T1" in d and ("FSPGR" in d or "3D" in d)):
                return "T1_MPRAGE"
            if any(tok in d for tok in ["T2 GRE MT", "GRE MT", "2D GRE MT", "GRE  MT", "GRE-MT"]):
                return "T2_GRE_MT"
            if any(tok in d for tok in ["B0", "B0RF", "BOF", "MAP"]):
                return "B0_MAP"
            if any(tok in d for tok in ["LOCALIZER", "SCOUT", "LOC "]):
                return "LOCALIZER"
            return "OTHER"

        for series_id, series_data in series_groups.items():
            desc = series_data['description']
            score = self._score_series(desc)
            # derive a representative folder hint for readability
            try:
                any_file = series_data['files'][0]
                folder_hint = any_file.parent.name
            except Exception:
                folder_hint = ''
            series_scores[series_id] = {
                'score': score,
                'description': desc,
                'label': canonical_label(desc),
                'uid': series_data.get('uid', 'unknown'),
                'folder': folder_hint,
                'files': series_data['files']
            }
        
        # Print available series (top 20 for brevity)
        if series_scores:
            printable = sorted([(v['description'], v['score'], len(v['files'])) for v in series_scores.values()], key=lambda x: (-x[1], -x[2]))
            print("\n📋 Available series (description | score | files):")
            for desc, sc, n in printable[:20]:
                print(f"   - {desc} | score={sc} | files={n}")

        # Select best class label (e.g., T1_MPRAGE) and include ALL repeats of that label
        if series_scores:
            # Find best (score, then prefer T1_MPRAGE when tied)
            items = list(series_scores.items())
            if items:
                items.sort(key=lambda x: (x[1]['score'], 1 if x[1]['label']=="T1_MPRAGE" else 0), reverse=True)
                best = items[0][1]
                if best['score'] > 0:
                    target_label = best['label']
                    selected_files = []
                    chosen_uids = set()
                    folder_samples = []
                    chosen_descs = []
                    if keep_all_repeats:
                        for _, v in series_scores.items():
                            if v['label'] == target_label and v['score'] > 0:
                                selected_files.extend(v['files'])
                                chosen_uids.add(v.get('uid', 'unknown'))
                                if v.get('folder'):
                                    folder_samples.append(v['folder'])
                                chosen_descs.append(v['description'])
                        print(f"🎯 Selected label: {target_label} (Score: {best['score']}/100) — including all repeats: {len(chosen_uids)} groups, {len(selected_files)} files total")
                    else:
                        # choose the single best group for the chosen label using quality heuristics
                        candidates = [v for _, v in series_scores.items() if v['label'] == target_label and v['score'] > 0]
                        best_group = None
                        best_key = None
                        for v in candidates:
                            key = self._group_quality(v['files'])
                            if best_group is None or key > best_key:
                                best_group = v
                                best_key = key
                        if best_group is None:
                            best_group = best
                        selected_files = list(best_group['files'])
                        chosen_uids = {best_group.get('uid','unknown')}
                        if best_group.get('folder'):
                            folder_samples = [best_group['folder']]
                        chosen_descs = [best_group['description']]
                        print(f"🎯 Selected label: {target_label} (Score: {best['score']}/100) — best single group: 1 group, {len(selected_files)} files")
                        for d in folder_samples[:5]:
                            print(f"     • folder: {d}")

                    # Persist a summary for Phase 2 to ensure consistent reporting
                    try:
                        # Detect image type from the selected series
                        print(f"🔍 Detecting image type from: {best['files'][0]}")
                        image_type = self._detect_image_type_from_series(best['files'][0])
                        print(f"🔍 Detected image type: {image_type}")
                        
                        summary = {
                            'dataset': self.dataset_name,
                            'selected_label': target_label,
                            'selected_score': best['score'],
                            'image_type': image_type,  # 2D or 3D
                            'groups': list(chosen_uids),
                            'sample_folders': folder_samples[:10],
                            'descriptions': list(dict.fromkeys(chosen_descs))[:10],
                            'total_files': len(selected_files),
                            'keep_all_repeats': keep_all_repeats,
                        }
                        summary_path = Path(self.output_dir) / "selected_series_summary.json"
                        with open(summary_path, 'w') as f:
                            json.dump(summary, f, indent=2)
                        print(f"📝 Saved series selection summary → {summary_path}")
                    except Exception as e:
                        print(f"⚠️ Error saving series summary: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("⚠️ No suitable series found, using all files")
                    selected_files = dicom_files
        
        return selected_files
    
    def _score_series(self, series_desc: str) -> int:
        """Score a series for disease suitability."""
        score = 0
        series_desc_upper = series_desc.upper()

        # Normalize common synonyms from folder names and scanners (include deeper folder path tokens)
        norm = series_desc_upper
        # unify separators
        for a, b in [("_", " "), ("-", " "), ("  ", " ")]:
            norm = norm.replace(a, b)
        # map GRE MT variants
        if any(tok in norm for tok in ["GRE MT", "GRE  MT", "GREMT", "2D GRE MT"]):
            norm += " T2 GRE MT"
        # map FSPGR sagittal T1 to MPRAGE-like
        if all(t in norm for t in ["SAG", "T1"]) and ("FSPGR" in norm or "3D" in norm):
            norm += " MPRAGE"
        # penalize known non-diagnostic/b0 map series
        if any(tok in norm for tok in ["B0", "B0RF", "BOF", "MAP", "LOCALIZER", "SCOUT"]):
            score -= 40
        
        # Check optimal series
        for desc in self.optimal_series["optimal"]["series_descriptions"]:
            if desc.upper() in norm:
                score += 40
                break
        
        # Check fallback series
        if score == 0 and "fallback" in self.optimal_series:
            for desc in self.optimal_series["fallback"]["series_descriptions"]:
                if desc.upper() in norm:
                    score += 25
                    break

        # Generic boosts when metadata lacks clear names
        # Prefer T1/MPRAGE-like identifiers
        if any(tok in norm for tok in ["T1", "MPRAGE", "MP RAGE", "SAG", "T1W"]):
            score += 20
        # Penalize known non-diagnostic sequences
        if any(tok in norm for tok in ["LOC ", " LOCALIZER", " SCOUT", "CALIBRATION", "B1 ", "B1-"]):
            score -= 30
        
        return min(100, score)

    def _group_quality(self, files: List[Path]):
        """Estimate group quality for tie-breaking among repeats.
        Higher is better. Returns a tuple used for sorting.
        Metrics:
          1) Smaller voxel volume (PixelSpacing*SliceThickness) → higher quality
          2) Larger in-plane matrix (Rows*Columns)
          3) Newer acquisition datetime (AcquisitionDate/Time)
        """
        import datetime
        # defaults when metadata missing
        voxel_vol = 1e9
        rows_cols = 0
        acq_dt = datetime.datetime.min
        try:
            # probe first file in the group
            ds = pydicom.dcmread(files[0], stop_before_pixels=True)
            # voxel volume
            ps = getattr(ds, 'PixelSpacing', None)
            th = getattr(ds, 'SliceThickness', None)
            if ps is not None and len(ps) >= 2 and th is not None:
                try:
                    voxel_vol = float(ps[0]) * float(ps[1]) * float(th)
                except Exception:
                    voxel_vol = 1e9
            # matrix
            rows = int(getattr(ds, 'Rows', 0) or 0)
            cols = int(getattr(ds, 'Columns', 0) or 0)
            rows_cols = rows * cols
            # acquisition datetime
            d = str(getattr(ds, 'AcquisitionDate', '') or '')
            t = str(getattr(ds, 'AcquisitionTime', '') or '')
            # normalize to YYYYMMDD and HHMMSS
            if d and len(d) >= 8:
                y, m, d2 = int(d[0:4]), int(d[4:6]), int(d[6:8])
                hh = int((t + '000000')[0:2]) if t else 0
                mm = int((t + '000000')[2:4]) if t else 0
                ss = int((t + '000000')[4:6]) if t else 0
                acq_dt = datetime.datetime(y, m, d2, hh, mm, ss)
        except Exception:
            pass
        # Sorting: want smaller voxel_vol, larger rows_cols, newer time → use negatives/positives accordingly
        return (-1.0/voxel_vol if voxel_vol and voxel_vol > 0 else -0.0, rows_cols, acq_dt)

class MRIPreprocessor:
    def __init__(self, input_dir, output_dir, dataset_name="Unknown", keep_all_repeats: bool = False):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.dataset_name = dataset_name
        self.keep_all_repeats = keep_all_repeats
        
        # Initialize integrated series selector
        self.series_selector = SeriesSelector(dataset_name, str(self.output_dir))
        
        # Create output directories
        self.nifti_dir = self.output_dir / "nifti_files"
        self.bids_dir = self.output_dir / "bids_structure"
        self.qa_dir = self.output_dir / "quality_assessment"
        
        for d in [self.nifti_dir, self.bids_dir, self.qa_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def find_dicom_files(self):
        """Find all DICOM files."""
        dicom_files = []
        for root, dirs, files in os.walk(self.input_dir):
            for file in files:
                file_path = Path(root) / file
                if self.is_dicom_file(file_path):
                    dicom_files.append(file_path)
        return dicom_files
    
    def is_dicom_file(self, file_path):
        """Check if file is DICOM."""
        try:
            pydicom.dcmread(file_path, stop_before_pixels=True)
            return True
        except:
            return False
    
    def convert_to_nifti(self):
        """Step 1: Convert DICOM to NIfTI with automatic series selection."""
        print("Step 1: Converting DICOM to NIfTI with automatic series selection...")
        
        dicom_files = self.find_dicom_files()
        if not dicom_files:
            print("No DICOM files found!")
            return []
        
        print(f"Found {len(dicom_files)} DICOM files")
        
        # Use integrated series selector to select optimal series
        print(f"🧠 Using {self.dataset_name} series selector for optimal series selection...")
        selected_files = self.series_selector.select_optimal_series(dicom_files, keep_all_repeats=self.keep_all_repeats)
        
        if not selected_files:
            print("⚠️ No suitable series found, using all files")
            selected_files = dicom_files
        
        print(f"Selected {len(selected_files)} files from optimal series")
        
        # Group selected files by series
        series_groups = {}
        for dcm_file in selected_files:
            try:
                ds = pydicom.dcmread(dcm_file, stop_before_pixels=True)
                patient_id = getattr(ds, 'PatientID', 'unknown')
                series_uid = getattr(ds, 'SeriesInstanceUID', 'unknown')
                key = f"{patient_id}_{series_uid}"
                
                if key not in series_groups:
                    series_groups[key] = []
                series_groups[key].append(dcm_file)
            except:
                continue
        
        # Convert each series
        nifti_files = []
        for series_id, dcm_files in tqdm(series_groups.items(), desc="Converting series"):
            try:
                nifti_path = self.convert_series(series_id, dcm_files)
                if nifti_path:
                    nifti_files.append(nifti_path)
            except Exception as e:
                print(f"Error converting {series_id}: {e}")
        
        print(f"Converted {len(nifti_files)} series to NIfTI")
        return nifti_files
    
    def convert_series(self, series_id, dcm_files):
        """Convert a DICOM series to NIfTI."""
        try:
            # Read and sort DICOM slices
            slices = []
            for dcm_file in dcm_files:
                try:
                    ds = pydicom.dcmread(dcm_file)
                    slice_location = float(getattr(ds, 'SliceLocation', getattr(ds, 'InstanceNumber', 0)))
                    slices.append((ds, slice_location))
                except Exception as e:
                    print(f"Warning: Could not read {dcm_file}: {e}")
                    continue
            
            if not slices:
                print(f"No valid slices found for series {series_id}")
                return None
            
            # Sort by slice location
            slices.sort(key=lambda x: x[1])
            
            # Extract pixel data
            pixel_arrays = []
            for ds, _ in slices:
                try:
                    pixel_array = ds.pixel_array
                    # Handle different orientations
                    if len(pixel_array.shape) == 2:
                        pixel_arrays.append(pixel_array)
                except Exception as e:
                    print(f"Warning: Could not extract pixels: {e}")
                    continue
            
            if not pixel_arrays:
                print(f"No valid pixel data found for series {series_id}")
                return None
            
            # Stack into 3D volume
            volume = np.stack(pixel_arrays, axis=2)
            
            # Create proper affine matrix (basic version)
            first_ds = slices[0][0]
            pixel_spacing = getattr(first_ds, 'PixelSpacing', [1.0, 1.0])
            slice_thickness = getattr(first_ds, 'SliceThickness', 1.0)
            
            affine = np.eye(4)
            affine[0, 0] = float(pixel_spacing[0])
            affine[1, 1] = float(pixel_spacing[1])
            affine[2, 2] = float(slice_thickness)
            
            # Create NIfTI image
            nifti_img = nib.Nifti1Image(volume, affine)
            
            # Clean series ID for filename
            clean_series_id = series_id.replace('/', '_').replace('\\', '_')
            output_path = self.nifti_dir / f"{clean_series_id}.nii.gz"
            
            # Save
            nib.save(nifti_img, output_path)
            print(f"Successfully converted series to {output_path}")
            
            return output_path
            
        except Exception as e:
            print(f"Failed to convert series {series_id}: {e}")
            return None
    
    def organize_bids(self, nifti_files):
        """Step 2: Organize to BIDS format."""
        print("Step 2: Organizing to BIDS format...")
        
        # Create BIDS metadata
        dataset_desc = {
            "Name": f"{self.dataset_name} Dataset",
            "BIDSVersion": "1.8.0",
            "Authors": ["FYP Team"]
        }
        
        with open(self.bids_dir / "dataset_description.json", 'w') as f:
            json.dump(dataset_desc, f, indent=2)
        
        # Organize files
        organized_count = 0
        for i, nifti_file in enumerate(tqdm(nifti_files, desc="Organizing files")):
            try:
                # Extract subject ID from filename
                subject_id = f"sub-{i+1:03d}"
                session_id = "ses-001"
                
                # Create BIDS structure
                subject_dir = self.bids_dir / subject_id / session_id / "anat"
                subject_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy to BIDS location
                bids_filename = f"{subject_id}_{session_id}_T1w.nii.gz"
                bids_path = subject_dir / bids_filename
                shutil.copy2(nifti_file, bids_path)
                organized_count += 1
                
            except Exception as e:
                print(f"Error organizing {nifti_file}: {e}")
        
        print(f"Organized {organized_count} files into BIDS structure")
        return organized_count
    
    def quality_assessment(self):
        """Step 3: Quality assessment."""
        print("Step 3: Running quality assessment...")
        
        # Find all NIfTI files in BIDS structure
        nifti_files = list(self.bids_dir.rglob("*.nii.gz"))
        
        if not nifti_files:
            print("No files found for quality assessment")
            return {}
        
        # Assess each file
        qa_data = []
        for nifti_file in tqdm(nifti_files, desc="Assessing quality"):
            try:
                img = nib.load(nifti_file)
                data = img.get_fdata()
                
                metrics = {
                    'filename': str(nifti_file.name),
                    'shape': data.shape,
                    'file_size_mb': nifti_file.stat().st_size / (1024*1024),
                    'min_value': float(np.min(data)),
                    'max_value': float(np.max(data)),
                    'mean_value': float(np.mean(data)),
                    'std_value': float(np.std(data)),
                    'zero_percent': float(np.sum(data == 0) / data.size * 100)
                }
                qa_data.append(metrics)
                
            except Exception as e:
                print(f"Error assessing {nifti_file}: {e}")
        
        # Save QA report
        qa_report = self.qa_dir / "qa_report.json"
        with open(qa_report, 'w') as f:
            json.dump(qa_data, f, indent=2)
        
        # Create simple visualization
        if qa_data:
            self.create_qa_plot(qa_data)
        
        print(f"Quality assessment completed for {len(qa_data)} files")
        return qa_data
    
    def create_qa_plot(self, qa_data):
        """Create quality assessment plots."""
        df = pd.DataFrame(qa_data)
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(f'Quality Assessment - {self.dataset_name}')
        
        # File sizes
        axes[0,0].hist(df['file_size_mb'], bins=10, alpha=0.7)
        axes[0,0].set_title('File Size Distribution')
        axes[0,0].set_xlabel('Size (MB)')
        
        # Dimensions
        x_dims = df['shape'].apply(lambda x: x[0])
        y_dims = df['shape'].apply(lambda x: x[1]) 
        z_dims = df['shape'].apply(lambda x: x[2])
        axes[0,1].boxplot([x_dims, y_dims, z_dims], labels=['X', 'Y', 'Z'])
        axes[0,1].set_title('Image Dimensions')
        
        # Intensity range
        axes[1,0].scatter(df['mean_value'], df['std_value'])
        axes[1,0].set_title('Mean vs Std Intensity')
        axes[1,0].set_xlabel('Mean')
        axes[1,0].set_ylabel('Std')
        
        # Zero percentage
        axes[1,1].hist(df['zero_percent'], bins=10, alpha=0.7)
        axes[1,1].set_title('Zero Voxels Percentage')
        axes[1,1].set_xlabel('Zero %')
        
        plt.tight_layout()
        plt.savefig(self.qa_dir / "qa_plots.png", dpi=150, bbox_inches='tight')
        plt.close()
    
    def run_phase1(self):
        """Run complete Phase 1 preprocessing."""
        print(f"\n=== MRI Preprocessing Phase 1 - {self.dataset_name} ===")
        print(f"Input: {self.input_dir}")
        print(f"Output: {self.output_dir}")
        
        try:
            # Step 1: Convert DICOM to NIfTI with automatic series selection
            print(f"🧠 {self.dataset_name} series selector integrated - automatic optimal series selection")
            nifti_files = self.convert_to_nifti()
            
            # Step 2: Organize to BIDS
            organized_count = self.organize_bids(nifti_files)
            
            # Step 3: Quality assessment
            qa_data = self.quality_assessment()
            
            # Summary
            print(f"\n=== Phase 1 Complete ===")
            print(f"Converted: {len(nifti_files)} NIfTI files")
            print(f"Organized: {organized_count} files to BIDS")
            print(f"QA assessed: {len(qa_data)} files")
            print(f"Results saved to: {self.output_dir}")
            
            return True
            
        except Exception as e:
            print(f"Error in Phase 1 preprocessing: {e}")
            return False
    
    @staticmethod
    def count_subjects_in_directory(input_dir: Path, output_dir: Path) -> dict:
        """
        Count total subjects in input directory and check processing status.
        
        Args:
            input_dir: Path to input directory (raw DICOM folders)
            output_dir: Path to output directory (where processed files go)
            
        Returns:
            dict with total, processed, pending counts and lists
        """
        if not input_dir.exists() or not input_dir.is_dir():
            return {
                'total': 0,
                'processed': 0,
                'pending': 0,
                'total_subjects': [],
                'processed_subjects': [],
                'pending_subjects': []
            }
        
        # Get all subdirectories from INPUT (raw subjects)
        all_subdirs = sorted([d for d in input_dir.iterdir() if d.is_dir()])
        total_subjects = [d.name for d in all_subdirs]
        
        # Check which subjects have been processed (check OUTPUT directory)
        processed_subjects = []
        pending_subjects = []
        
        for subdir in all_subdirs:
            subject_name = subdir.name
            # Check if bids_structure exists in OUTPUT with .nii.gz files
            output_check = output_dir / subject_name / "bids_structure"
            if output_check.exists() and list(output_check.rglob("*.nii.gz")):
                processed_subjects.append(subject_name)
            else:
                pending_subjects.append(subject_name)
        
        return {
            'total': len(total_subjects),
            'processed': len(processed_subjects),
            'pending': len(pending_subjects),
            'total_subjects': total_subjects,
            'processed_subjects': processed_subjects,
            'pending_subjects': pending_subjects
        }

def main():
    """Main function for command line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MRI Preprocessing Phase 1")
    parser.add_argument("--input", required=True, help="Input directory with DICOM files")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--dataset", default="Unknown", help="Dataset name (PPMI/ADNI/OASIS)")
    parser.add_argument("--per-subject", action="store_true", help="Treat each immediate subfolder of --input as a separate subject and write outputs into per-subject subfolders under --output")
    parser.add_argument("--keep-all-repeats", action="store_true", help="Keep all repeats of the chosen series label instead of picking the best single group")
    parser.add_argument("--check-status", action="store_true", help="Check batch processing status without running pipeline")
    
    args = parser.parse_args()
    
    # Check status only (don't run pipeline)
    if args.check_status:
        output_root = Path(args.output)
        input_root = Path(args.input)
        
        print("\n" + "="*70)
        print("📊 PHASE 1 BATCH PROCESSING STATUS CHECK")
        print("="*70)
        
        status = MRIPreprocessor.count_subjects_in_directory(input_root, output_root)
        
        print(f"\n📁 Input directory: {input_root}")
        print(f"📁 Output directory: {output_root}")
        print(f"\n📊 Total subjects found: {status['total']}")
        print(f"✅ Already processed: {status['processed']} ({status['processed']/max(1,status['total'])*100:.1f}%)")
        print(f"⏳ Pending processing: {status['pending']} ({status['pending']/max(1,status['total'])*100:.1f}%)")
        
        if status['processed'] > 0:
            print(f"\n✅ Processed subjects ({status['processed']}):")
            for subj in status['processed_subjects']:
                print(f"   • {subj}")
        
        if status['pending'] > 0:
            print(f"\n⏳ Pending subjects ({status['pending']}):")
            for subj in status['pending_subjects']:
                print(f"   • {subj}")
        
        print("\n" + "="*70)
        
        if status['pending'] == 0 and status['total'] > 0:
            print("✅ All subjects have been processed!")
        elif status['total'] == 0:
            print("⚠️  No subjects found in the directory.")
        else:
            print(f"⏳ {status['pending']} subjects remaining to process.")
        
        print("="*70)
        return 0
    
    # Run preprocessing
    if args.per_subject:
        input_root = Path(args.input)
        output_root = Path(args.output)
        if not input_root.exists() or not input_root.is_dir():
            print(f"❌ --input must be an existing directory: {input_root}")
            return 1
        
        # Count subjects and check processing status
        print("\n" + "="*70)
        print("📊 PHASE 1 BATCH PROCESSING STATUS")
        print("="*70)
        
        status = MRIPreprocessor.count_subjects_in_directory(input_root, output_root)
        
        print(f"\n📁 Directory: {input_root}")
        print(f"📊 Total subjects found: {status['total']}")
        print(f"✅ Already processed: {status['processed']}")
        print(f"⏳ Pending processing: {status['pending']}")
        
        if status['processed'] > 0:
            print(f"\n✅ Processed subjects ({status['processed']}):")
            for subj in status['processed_subjects'][:10]:  # Show first 10
                print(f"   • {subj}")
            if len(status['processed_subjects']) > 10:
                print(f"   ... and {len(status['processed_subjects']) - 10} more")
        
        if status['pending'] > 0:
            print(f"\n⏳ Pending subjects ({status['pending']}):")
            for subj in status['pending_subjects'][:10]:  # Show first 10
                print(f"   • {subj}")
            if len(status['pending_subjects']) > 10:
                print(f"   ... and {len(status['pending_subjects']) - 10} more")
        
        print("\n" + "="*70)
        
        subdirs = sorted([p for p in input_root.iterdir() if p.is_dir()])
        if not subdirs:
            print(f"⚠️ No subfolders found under {input_root}. Nothing to do.")
            return 0
        
        overall_success = True
        processed_count = 0
        failed_count = 0
        
        for idx, subj_dir in enumerate(subdirs, 1):
            subj_name = subj_dir.name
            subj_out = output_root / subj_name
            
            # Display progress
            print(f"\n{'='*70}")
            print(f"📂 Processing Subject {idx}/{len(subdirs)}: {subj_name}")
            print(f"   Progress: {processed_count} completed | {failed_count} failed | {len(subdirs) - idx + 1} remaining")
            print(f"{'='*70}")
            
            processor = MRIPreprocessor(str(subj_dir), str(subj_out), args.dataset, keep_all_repeats=args.keep_all_repeats)
            try:
                success = processor.run_phase1()
                if success:
                    processed_count += 1
                else:
                    failed_count += 1
                overall_success = overall_success and bool(success)
            except Exception as e:
                overall_success = False
                failed_count += 1
                print(f"\n❌ Phase 1 failed for {subj_name}: {e}")
        
        # Final summary
        print("\n" + "="*70)
        print("📊 FINAL PHASE 1 BATCH SUMMARY")
        print("="*70)
        print(f"📁 Total subjects: {len(subdirs)}")
        print(f"✅ Successfully processed: {processed_count}")
        print(f"❌ Failed: {failed_count}")
        print(f"📈 Success rate: {(processed_count/len(subdirs)*100):.1f}%")
        print("="*70)
        
        if overall_success:
            print("\n✅ Phase 1 preprocessing completed successfully for all subjects!")
            return 0
        else:
            print("\n⚠️ Phase 1 completed with errors for some subjects.")
            return 1
    else:
        processor = MRIPreprocessor(args.input, args.output, args.dataset, keep_all_repeats=args.keep_all_repeats)
        success = processor.run_phase1()
        
        if success:
            print("\n✅ Phase 1 preprocessing completed successfully!")
        else:
            print("\n❌ Phase 1 preprocessing failed!")
            return 1

if __name__ == "__main__":
    main()