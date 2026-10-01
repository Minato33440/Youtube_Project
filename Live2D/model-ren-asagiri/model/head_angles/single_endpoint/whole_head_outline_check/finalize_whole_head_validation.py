"""Independent readback and provenance summary for whole-head guide assets."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


OUT = Path(__file__).resolve().parent
PROJECT_ROOT = OUT.parents[5]
PYLIB = PROJECT_ROOT / "output" / "live2d" / "risa_parts_v1" / "tools" / "pylib"
# Append so the runtime venv's working NumPy remains authoritative.
sys.path.append(str(PYLIB))
from psd_tools import PSDImage  # noqa: E402


TARGET = OUT / "whole_head_contour_target.json"
PSD = OUT / "whole_head_reference_4000x6000.psd"
PSD_MANIFEST = OUT / "whole_head_reference_psd_manifest.json"
PSD_READBACK = OUT / "whole_head_reference_psd_readback.json"
RUNTIME_REPORT = OUT / "whole_head_runtime_measurement.json"
VALIDATION = OUT / "validation.json"
TEST_REPORT = OUT / "test_report.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    target = json.loads(TARGET.read_text(encoding="utf-8"))
    manifest = json.loads(PSD_MANIFEST.read_text(encoding="utf-8"))
    ag_readback = json.loads(PSD_READBACK.read_text(encoding="utf-8"))
    runtime = json.loads(RUNTIME_REPORT.read_text(encoding="utf-8"))
    problems = []

    source_paths = {name: Path(record["path"]) for name, record in target["inputs"].items()}
    for name, path in source_paths.items():
        if not path.exists() or sha256(path) != target["inputs"][name]["sha256"]:
            problems.append(f"{name} input hash")
    original = np.asarray(Image.open(source_paths["original"]).convert("RGBA"))
    rough = np.asarray(Image.open(source_paths["rough"]).convert("RGBA"))
    outline = np.asarray(Image.open(source_paths["outline"]).convert("RGBA"))
    visible = (original[1:770, 57:729, 3] > 0) | (rough[:, :, 3] > 0)
    if not np.array_equal(original[1:770, 57:729][visible], rough[visible]):
        problems.append("rough exact crop registration")
    if np.any(outline[769:, :, 3]):
        problems.append("outline 15px transparent bottom padding")

    psd = PSDImage.open(PSD)
    psd_layers = [layer.name for layer in psd]
    expected_layers = [layer["name"] for layer in manifest["layers"]]
    if psd.size != (4000, 6000):
        problems.append("psd canvas")
    if psd_layers != expected_layers:
        problems.append("psd layer names/order")
    if ag_readback["status"] != "pass" or ag_readback["sha256"] != sha256(PSD):
        problems.append("ag-psd readback/hash")
    if len(target["evaluation_samples"]["face_visible_2px_spacing"]) != runtime["sample_counts"]["face_visible_observed"]:
        problems.append("face sample count")
    if len(target["evaluation_samples"]["scalp_inferred_3px_spacing"]) != runtime["sample_counts"]["scalp_hair_hidden_inferred"]:
        problems.append("scalp sample count")
    if runtime["models"]["hashes_equal"] or runtime["status"] != "before_after_measurement_complete":
        problems.append("expected actual changed-runtime before-after state")
    for label in ("baseline", "current"):
        model3 = Path(runtime["direct_model_loading"][f"{label}_model3_json"])
        config = json.loads(model3.read_text(encoding="utf-8"))
        if sha256(model3.parent / config["FileReferences"]["Moc"]) != runtime["models"][f"{label}_moc3_sha256"]:
            problems.append(f"{label} runtime hash stale")
    pose_path = OUT.parent / "whole_head_pose_check/whole_head_pose_checks.json"
    pose = json.loads(pose_path.read_text(encoding="utf-8"))
    for name, record in pose["provenance"].items():
        model3 = Path(record["model3"])
        config = json.loads(model3.read_text(encoding="utf-8"))
        if sha256(model3.parent / config["FileReferences"]["Moc"]) != record["moc3_sha256"]:
            problems.append(f"{name} pose runtime hash stale")
    if any(case["display_max"] != 0 for case in pose["front_face_preservation"] + pose["full_front_preservation"]):
        problems.append("frontal displayed image changed")

    artifact_hashes = {}
    for path in sorted(OUT.iterdir()):
        if path.is_file() and path.name not in {VALIDATION.name, TEST_REPORT.name}:
            artifact_hashes[path.name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    registration = target["registration"]
    validation = {
        "status": "pass" if not problems else "fail",
        "scope": "Reference provenance and actual exported-runtime before/after checks. Cubism mesh edits were made separately through its GUI. This is not aesthetic acceptance or a triangle-topology audit.",
        "source_registration": registration,
        "classification": target["classification"],
        "checks": {
            "source_hashes": not any("input hash" in problem for problem in problems),
            "rough_is_exact_visible_rgba_crop_at_original_xy_57_1": "rough exact crop registration" not in problems,
            "outline_bottom_15px_transparent": "outline 15px transparent bottom padding" not in problems,
            "ag_psd_rgba_readback": "ag-psd readback/hash" not in problems,
            "independent_psd_tools_canvas_and_layer_order": not any(problem.startswith("psd ") for problem in problems),
            "runtime_is_actual_before_after": "expected actual changed-runtime before-after state" not in problems,
            "runtime_and_pose_hashes_current": not any("hash stale" in problem for problem in problems),
            "frontal_display_preserved": "frontal displayed image changed" not in problems,
            "runtime_direct_real_model_no_warp": runtime["direct_model_loading"],
        },
        "psd_readback": {
            "canvas": list(psd.size),
            "layer_count": len(psd_layers),
            "layer_names": psd_layers,
            "sha256": sha256(PSD),
        },
        "baseline_diagnostic_distance_canvas_px": runtime["distance_canvas_px"]["baseline"],
        "current_diagnostic_distance_canvas_px": runtime["distance_canvas_px"]["current"],
        "pose_report": {"path": str(pose_path), "sha256": sha256(pose_path), "face_cases": len(pose["face_pose_cases"])},
        "remaining_edge_flags": [{"params": case["params"], "alpha16": case["raster"], "alpha64": case["raster_alpha64"]} for case in pose["face_pose_cases"] if case["raster"]["rows_with_multiple_runs"] or case["raster_alpha64"]["rows_with_multiple_runs"]],
        "artifact_hashes": artifact_hashes,
        "problems": problems,
        "acceptance_boundary": "Real before/after export is verified. Cheek kinks and small translucent edge fragments remain. Alpha64 has a one-row split at X=-15/Y=-30; alpha16 has up to seven split rows at the endpoint. Scalp under hair is inferred. Boss contour acceptance remains pending; do not advance eyes/hair/ears/mouth placement yet.",
    }
    VALIDATION.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    face = runtime["distance_canvas_px"]["baseline"]["face_visible_observed"]
    scalp = runtime["distance_canvas_px"]["baseline"]["scalp_hair_hidden_inferred"]
    current_face = runtime["distance_canvas_px"]["current"]["face_visible_observed"]
    current_scalp = runtime["distance_canvas_px"]["current"]["scalp_hair_hidden_inferred"]
    report = f"""# Whole-head outline guide and actual runtime comparison

## Result

The import-ready 4000x6000 PSD passed ag-psd RGBA readback and independent psd-tools canvas/layer-order checks.  The Rough image is an exact visible-RGBA crop of the original at original offset `(57, 1)` with scale `1.0`; therefore the outline-to-canvas transform is uniform scale `{registration['rough_outline_to_canvas']['scale']}` and translation `({registration['rough_outline_to_canvas']['translation_px'][0]}, {registration['rough_outline_to_canvas']['translation_px'][1]})`.  No rotation or un-tilting is applied.

- `whole_head_reference_4000x6000.psd`: five separate import layers for observed face edge, inferred scalp, ear outer reference, Boss outline, and Rough.
- `whole_head_outline_guide_4000x6000.png`: transparent 4000x6000 whole-head overlay.
- `whole_head_outline_source_audit.png`: cyan is the observed face-underfill edge; amber dashed is the inferred hair-hidden scalp; magenta ears are separate and excluded from the face target.
- `whole_head_runtime_guide_4up.png`: real direct-SDK face-runtime comparison at X=-30/Y=-30.

## Before and after measurement

The archived baseline and newly exported moc3 hashes differ and both hashes match files on disk. The observed face path has p50 `{face['p50']} -> {current_face['p50']}` px, p90 `{face['p90']} -> {current_face['p90']}` px, max `{face['max']} -> {current_face['max']}` px over `{face['count']}` samples. The inferred scalp path has p50 `{scalp['p50']} -> {current_scalp['p50']}` px, p90 `{scalp['p90']} -> {current_scalp['p90']}` px, max `{scalp['max']} -> {current_scalp['max']}` px over `{scalp['count']}` samples. These are 4000x6000 canvas distances, using the same fixed registration for both models.

## Preservation and remaining work

The 15 face-only frontal angle/mouth cases and eight full-model frontal/mouth cases have zero displayed-image difference from this task's backup. The three other endpoint poses have zero alpha-boundary difference. Thirty-two face-only pose/mouth cases were checked and the comparison sheets visually inspected.

This does not pass a perfect-edge acceptance gate. Small cheek kinks remain. At alpha>=16, endpoint rows show up to seven tiny edge splits; at alpha>=64, X=-15/Y=-30 has a one-row split in each mouth state. These are recorded rather than removed from the report. The public wrapper has no vertex/index buffer access for a numerical triangle inversion audit. No new continuous-motion or physics acceptance is claimed.

The renderer loads the exported model3/moc3 directly, disables blink/breath, does not call physics, and does not warp a model render. Ear outer contours are not included in face-underfill distance metrics. The hidden scalp remains an authorized approximation. Boss visual review of the face contour is pending; other facial parts have not been adjusted.
"""
    TEST_REPORT.write_text(report, encoding="utf-8")
    print(json.dumps({"status": validation["status"], "problems": problems, "psd_sha256": validation["psd_readback"]["sha256"], "validation": str(VALIDATION), "report": str(TEST_REPORT)}, ensure_ascii=False))
    if problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
