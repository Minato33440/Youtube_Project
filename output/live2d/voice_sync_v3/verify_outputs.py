"""Read-only verification of the v3 two-parameter Cubism render outputs."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parent
V2 = ROOT.parent / "voice_sync_v2"
FPS, FRAME_COUNT, DURATION = 30, 478, 478 / 30
VIDEOS = ["Risa_narration_composite.mp4", "Risa_lipsync_closeup.mp4", "Risa_lipsync_comparison.mp4"]


def command(*args: str) -> bytes:
    return subprocess.check_output(args, stderr=subprocess.STDOUT)


def probe(path: Path) -> dict:
    return json.loads(command("ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)))


def pcm(path: Path) -> np.ndarray:
    raw = command("ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "44100", "-f", "s16le", "-")
    return np.frombuffer(raw, dtype="<i2").astype(np.float64)


def decode_ok(path: Path) -> None:
    result = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True)
    assert result.returncode == 0 and not result.stderr, f"Decode failure for {path.name}: {result.stderr}"


def rgba(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)


def main() -> None:
    v2_rows = list(csv.DictReader((V2 / "mouth_curve.csv").open(encoding="utf-8-sig", newline="")))
    rows = list(csv.DictReader((ROOT / "mouth_curve.csv").open(encoding="utf-8-sig", newline="")))
    assert len(v2_rows) == len(rows) == FRAME_COUNT
    assert all(a["mouth_open_y"] == b["mouth_open_y"] for a, b in zip(v2_rows, rows)), "v3 changed a locked v2 OpenY value"
    open_y = np.array([float(r["mouth_open_y"]) for r in rows])
    form = np.array([float(r["mouth_form"]) for r in rows])
    assert np.all((-1.0 <= form) & (form <= 1.0))

    motion = json.loads((ROOT / "voice_sync.motion3.json").read_text(encoding="utf-8"))
    curves = motion["Curves"]
    assert [curve["Id"] for curve in curves] == ["ParamMouthOpenY", "ParamMouthForm"]
    assert motion["Meta"]["CurveCount"] == 2 and motion["Meta"]["TotalPointCount"] == FRAME_COUNT * 2
    for curve, expected in zip(curves, (open_y, form)):
        segments = curve["Segments"]
        actual = np.array([segments[1], *segments[4::3]], dtype=float)
        times = np.array([segments[0], *segments[3::3]], dtype=float)
        assert np.allclose(times, np.array([float(r["time_s"]) for r in rows]), atol=1e-6, rtol=0)
        assert len(actual) == FRAME_COUNT and np.allclose(actual, expected, atol=0, rtol=0), f"CSV/motion mismatch: {curve['Id']}"

    report: dict = {"checks": {"v2_open_y_verbatim": True, "motion_csv_exact": True}, "outputs": {}}
    reference_audio = pcm(ROOT / "audio_mono_44100_pcm16.wav")
    assert np.array_equal(reference_audio, pcm(Path("C:/Users/Setona/Desktop/Voicd-Sample.mp4")))
    report["checks"]["source_pcm_exact"] = True
    for name in VIDEOS:
        path = ROOT / name
        assert path.exists() and path.stat().st_size > 10000, f"Missing/incomplete video: {name}"
        info = probe(path)
        video = next(s for s in info["streams"] if s["codec_type"] == "video")
        audio = next(s for s in info["streams"] if s["codec_type"] == "audio")
        assert int(video["nb_frames"]) == FRAME_COUNT and video["r_frame_rate"] == "30/1"
        assert abs(float(video["duration"]) - DURATION) < .001
        assert abs(float(video["start_time"]) - float(audio["start_time"])) < .001
        decode_ok(path)
        out_audio = pcm(path)
        n = min(len(reference_audio), len(out_audio))
        corr = float(np.corrcoef(reference_audio[:n], out_audio[:n])[0, 1])
        assert corr > .99, f"Audio correlation too low for {name}: {corr}"
        report["outputs"][name] = {"decode_pass": True, "video_frames": int(video["nb_frames"]), "fps": video["r_frame_rate"], "duration_s": float(video["duration"]), "audio_zero_offset_correlation": corr, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    frame_paths = sorted((ROOT / "frames").glob("*.png"))
    assert len(frame_paths) == FRAME_COUNT, f"Expected {FRAME_COUNT} PNG frames, got {len(frame_paths)}"
    baseline = rgba(frame_paths[0])
    changed = np.zeros(baseline.shape[:2], dtype=bool)
    for path in frame_paths:
        changed |= np.any(rgba(path) != baseline, axis=2)
    yy, xx = np.where(changed)
    assert len(xx) > 100
    actual_bbox = [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1]
    # Restrict all changing pixels to the mouth and its immediate lip margin.
    allowed = [330, 175, 430, 245]
    assert actual_bbox[0] >= allowed[0] and actual_bbox[1] >= allowed[1] and actual_bbox[2] <= allowed[2] and actual_bbox[3] <= allowed[3], f"Changes outside mouth ROI: {actual_bbox}"

    # OpenY=0 can still have lip-width transitions. Check closed-lip calibration
    # variation here; visible closure is reviewed separately on the contact sheet.
    # This script does not classify an aperture from image pixels.
    calibration = sorted((ROOT / "calibration").glob("*.png"))
    assert len(calibration) == 15, f"Expected 15 v3 calibration PNGs, got {len(calibration)}"
    cal = [rgba(path) for path in calibration]
    neutral_pairs = []
    v2_calibration = sorted((V2 / "calibration").glob("[0-9][0-9][0-9][0-9][0-9].png"))
    assert len(v2_calibration) == 7, "Expected seven v2 aperture calibration PNGs"
    for level, v2_path in zip([0, .15, .3, .45, .6, .75, .9], v2_calibration):
        # v3 form=0 at opens 0,.3,.6,.9 preserves the pre-existing neutral shape
        # at the overlapping 0,.3,.6,.9 calibration levels.
        if level in {0, .3, .6, .9}:
            v3_path = calibration[[0, .3, .6, .9].index(level) * 3 + 1]
            delta = int(np.any(rgba(v2_path) != rgba(v3_path), axis=2).sum())
            neutral_pairs.append({"open_y": level, "v2_frame": v2_path.name, "v3_frame": v3_path.name, "different_pixels": delta})
            assert delta == 0, f"Form=0 changed neutral image at OpenY={level}"
    zero_open_forms = cal[:3]
    zero_open_deltas = [int(np.any(image != zero_open_forms[1], axis=2).sum()) for image in zero_open_forms]
    assert zero_open_deltas[0] > 0 and zero_open_deltas[2] > 0, "Form extremes did not visibly affect closed lips"
    report["render"] = {"png_frames": len(frame_paths), "only_mouth_region_changes": True, "changed_bbox_xyxy": actual_bbox, "allowed_bbox_xyxy": allowed, "zero_open_form_variation_pixels": zero_open_deltas, "zero_open_aperture_parameter_zero": True, "form_zero_neutral_pixel_diffs_vs_v2": neutral_pairs, "transparent_background": bool(baseline[0, 0, 3] == 0)}
    report["curve"] = {"mouth_form_range": [float(form.min()), float(form.max())], "last_10_form": form[-10:].tolist(), "zero_open_frame_count": int((open_y == 0).sum()), "closure_image_classification": "not performed; calibration sheet reviewed visually by parent"}
    (ROOT / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"checks": report["checks"], "render": report["render"], "audio": {k: v["audio_zero_offset_correlation"] for k, v in report["outputs"].items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
