# Whole-head face-underfill guide

This directory contains the import reference and read-only validation for the Boss-supplied whole-head outline.  The editable Cubism model is in the parent folder; this folder holds its reference and actual exported-runtime comparisons.

## Import into Cubism

Use `whole_head_reference_4000x6000.psd`.  Its five layers keep the observed face-underfill edge, inferred scalp, ear outer reference, outline, and Rough image separate.  Hide every layer before model export.

- Cyan: observed face-underfill boundary from the supplied outline.
- Amber dashed: authorized approximation for the hair-hidden scalp boundary.
- Magenta: ear outer contour for orientation only.  Do not expand the face-underfill mesh to this path.

The Rough image is an exact visible-RGBA crop of `Looking_down (2).png` at original offset `(57, 1)` and scale `1.0`.  Combining that registration with the existing original placement gives outline/Rough-to-canvas scale `1.2904500571168767` and offset `(1478.38207755536, 162.40730217722344)`.  No rotation or un-tilting is applied.

## Current diagnostic (2026-09-26, actual before/after)

`whole_head_runtime_guide_4up.png` shows guide / archived model / newly exported model / overlay at X=-30/Y=-30. Both moc3 files are loaded directly. No pixel warping or reference-image substitution is used.

In 4000x6000 canvas coordinates, the observed face path (344 samples) changed from p50 4.457 / p90 14.333 / max 23.622 px to p50 2.635 / p90 7.279 / max 9.920 px. The inferred scalp path (275 samples) changed from p50 32.775 / p90 92.520 / max 98.555 px to p50 6.760 / p90 14.276 / max 16.856 px. Hidden scalp accuracy is not an anatomical acceptance criterion.

Frontal nod and mouth comparisons have zero displayed-image difference from this task's backup. Small cheek kinks and translucent edge fragments remain, including a one-row alpha64 split in the X=-15/Y=-30 intermediate pose. The 32-pose check is in `../whole_head_pose_check/whole_head_pose_checks.json`. Face contour acceptance is pending; eyes, ears, hair and mouth placement have not been advanced.

See `whole_head_contour_target.json` for coordinates and classification, `validation.json` for hashes and readback checks, and `test_report.md` for the validation boundary.

## Re-run after a real model export

Run these from the project root:

```powershell
& 'output/live2d/runtime_venv/Scripts/python.exe' 'Live2D/model-ren-asagiri/model/head_angles/single_endpoint/whole_head_outline_check/render_whole_head_runtime_comparison.py'
& 'output/live2d/runtime_venv/Scripts/python.exe' 'Live2D/model-ren-asagiri/model/head_angles/single_endpoint/whole_head_outline_check/finalize_whole_head_validation.py'
```

When the current moc3 differs from the archived baseline, the renderer produces a real before/after measurement.  It loads the exported model3/moc3 directly and does not warp rendered model pixels.  Boss visual acceptance is still required before adding hair, eyes, ears, or mouth to endpoint samples.
