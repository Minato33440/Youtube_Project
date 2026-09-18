#!/usr/bin/env python3
"""Verify that a Filmora export contains advancing source video, not still frames.

The expected timeline is the 4,745-frame / 30-fps Risa trial.  This is a
source-reference check: it samples five interior frames of every cut and N01
and requires both temporal motion and agreement with the corresponding source
frame.  It deliberately does not treat successful decoding as proof of motion.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np


FPS = 30
MODEL_ROI = (1275, 99, 384, 420)  # x, y, width, height in the 1920x1080 export
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "Politics_Economics" / "2026-09-09_fiscal_policy"
MEDIA = BASE / "media" / "sample_v1_risa"
SEGMENTS = (
    ("HOOK", 0, 643, MEDIA / "video" / "HOOK.mp4", "cut"),
    ("N01", 643, 1122, MEDIA / "live2d" / "N01.mov", "live2d"),
    ("C01a", 1122, 2243, MEDIA / "video" / "C01a.mp4", "cut"),
    ("C01b", 2243, 2716, MEDIA / "video" / "C01b.mp4", "cut"),
    ("C02a", 2716, 3900, MEDIA / "video" / "C02a.mp4", "cut"),
    ("C02b", 3900, 4745, MEDIA / "video" / "C02b.mp4", "cut"),
)


def probe(path: Path) -> tuple[int, int]:
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
           "stream=width,height", "-of", "json", str(path)]
    data = json.loads(subprocess.check_output(cmd, text=True, encoding="utf-8"))
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"])


def frames_at(path: Path, indexes: list[int], pixel_format: str) -> tuple[int, int, dict[int, np.ndarray]]:
    """Decode selected display-frame numbers in one pass, avoiding imprecise -ss seeks."""
    width, height = probe(path)
    unique = sorted(set(indexes))
    expression = "+".join(f"eq(n\\,{n})" for n in unique)
    channels = 4 if pixel_format == "rgba" else 3
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"select='{expression}'",
           "-vsync", "0", "-pix_fmt", pixel_format, "-f", "rawvideo", "-"]
    raw = subprocess.check_output(cmd)
    frame_bytes = width * height * channels
    if len(raw) != frame_bytes * len(unique):
        raise RuntimeError(f"{path.name}: decoded {len(raw) // frame_bytes} of {len(unique)} requested frames")
    arrays = np.frombuffer(raw, dtype=np.uint8).reshape(len(unique), height, width, channels)
    return width, height, {index: arrays[i] for i, index in enumerate(unique)}


def sample_indexes(start: int, end: int) -> list[int]:
    # Interior locations make a clip's first retained frame unable to pass all samples.
    span = end - start
    return [start + round(span * fraction) for fraction in (0.10, 0.30, 0.50, 0.70, 0.90)]


def gray(array: np.ndarray) -> np.ndarray:
    rgb = array[..., :3].astype(np.float32)
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def compare(output: np.ndarray, source: np.ndarray, mask: np.ndarray | None = None) -> dict[str, float]:
    a, b = output[..., :3].astype(np.float32), source[..., :3].astype(np.float32)
    if mask is not None:
        a, b = a[mask], b[mask]
    else:
        a, b = a.reshape(-1, 3), b.reshape(-1, 3)
    mae = float(np.mean(np.abs(a - b)) / 255.0)
    ag, bg = np.mean(a, axis=1), np.mean(b, axis=1)
    denom = float(np.linalg.norm(ag - ag.mean()) * np.linalg.norm(bg - bg.mean()))
    corr = float(np.dot(ag - ag.mean(), bg - bg.mean()) / denom) if denom > 1e-6 else 0.0
    return {"mae": mae, "correlation": corr, "pixels": int(len(a))}


def temporal_motion(frames: list[np.ndarray]) -> list[float]:
    return [float(np.mean(np.abs(a[..., :3].astype(np.float32) - b[..., :3].astype(np.float32))) / 255.0)
            for a, b in zip(frames, frames[1:])]


def live2d_temporal_motion(output_frames: list[np.ndarray], source_frames: list[np.ndarray]) -> tuple[list[float], list[float], list[int]]:
    """Measure only model pixels shared by adjacent source frames.

    The export ROI also contains a moving background and subtitles.  They must
    not be allowed to make a frozen Live2D layer look animated.
    """
    x, y, w, h = MODEL_ROI
    output_values, source_values, coverage = [], [], []
    for out_a, out_b, src_a, src_b in zip(output_frames, output_frames[1:], source_frames, source_frames[1:]):
        mask = (src_a[y:y+h, x:x+w, 3] >= 245) & (src_b[y:y+h, x:x+w, 3] >= 245)
        coverage.append(int(mask.sum()))
        out_a_roi, out_b_roi = out_a[y:y+h, x:x+w, :3], out_b[y:y+h, x:x+w, :3]
        src_a_roi, src_b_roi = src_a[y:y+h, x:x+w, :3], src_b[y:y+h, x:x+w, :3]
        output_values.append(float(np.mean(np.abs(out_a_roi[mask].astype(np.float32) - out_b_roi[mask].astype(np.float32))) / 255.0))
        source_values.append(float(np.mean(np.abs(src_a_roi[mask].astype(np.float32) - src_b_roi[mask].astype(np.float32))) / 255.0))
    return output_values, source_values, coverage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path, help="Filmora-exported MP4 to verify")
    parser.add_argument("--output", type=Path, help="JSON result path (default: motion_checks/<export>.motion_check.json)")
    args = parser.parse_args()
    export = args.export.resolve()
    output_path = args.output or (BASE / "code_edit" / "sample_v1_risa" / "motion_checks" /
                                  f"{export.stem}.motion_check.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_indexes = [index for _, start, end, _, _ in SEGMENTS for index in sample_indexes(start, end)]
    out_w, out_h, exported = frames_at(export, output_indexes, "rgb24")
    if (out_w, out_h) != (1920, 1080):
        raise RuntimeError(f"expected 1920x1080 export, got {out_w}x{out_h}")

    report_segments = []
    for name, start, end, source_path, kind in SEGMENTS:
        timeline_indexes = sample_indexes(start, end)
        local_indexes = [frame - start for frame in timeline_indexes]
        source_format = "rgba" if kind == "live2d" else "rgb24"
        src_w, src_h, source = frames_at(source_path, local_indexes, source_format)
        output_frames = [exported[index] for index in timeline_indexes]
        source_frames = [source[index] for index in local_indexes]
        samples = []
        if kind == "cut":
            if (src_w, src_h) != (out_w, out_h):
                raise RuntimeError(f"{name}: source is {src_w}x{src_h}, expected export size")
            for timeline_frame, local_frame, out_frame, src_frame in zip(timeline_indexes, local_indexes, output_frames, source_frames):
                metrics = compare(out_frame, src_frame)
                samples.append({"timeline_frame": timeline_frame, "source_frame": local_frame, **metrics})
            source_passes = [s["correlation"] >= 0.94 and s["mae"] <= 0.08 for s in samples]
            source_requirement = "at least 4/5 samples: correlation >= 0.94 and MAE <= 0.08"
        else:
            x, y, w, h = MODEL_ROI
            if (src_w, src_h) != (out_w, out_h):
                raise RuntimeError(f"{name}: Live2D source is {src_w}x{src_h}, expected {out_w}x{out_h}")
            for timeline_frame, local_frame, out_frame, src_frame in zip(timeline_indexes, local_indexes, output_frames, source_frames):
                # Compare only nearly opaque model pixels; transparent pixels contain the background video.
                source_roi = src_frame[y:y+h, x:x+w]
                mask = source_roi[..., 3] >= 245
                metrics = compare(out_frame[y:y+h, x:x+w], source_roi, mask)
                samples.append({"timeline_frame": timeline_frame, "source_frame": local_frame,
                                "opaque_pixels": int(mask.sum()), **metrics})
            source_passes = [s["pixels"] >= 500 and s["correlation"] >= 0.75 and s["mae"] <= 0.15 for s in samples]
            source_requirement = "at least 4/5 samples: opaque pixels >= 500, correlation >= 0.75 and MAE <= 0.15"

        if kind == "live2d":
            output_motion, source_motion, temporal_coverage = live2d_temporal_motion(output_frames, source_frames)
        else:
            output_motion, source_motion = temporal_motion(output_frames), temporal_motion(source_frames)
            temporal_coverage = []
        # A still clip has near-zero differences at all widely separated sample points.
        moving_pairs = sum(value >= 0.004 for value in output_motion)
        source_moving_pairs = sum(value >= 0.004 for value in source_motion)
        if kind == "live2d":
            # Facial movement is much subtler than a full-screen source cut.  Its
            # absolute signal is small, so compare it to the sampled Live2D source
            # signal; a held first frame is typically under 2% of that signal.
            output_motion_mean = float(np.mean(output_motion))
            source_motion_mean = float(np.mean(source_motion))
            source_has_motion = source_motion_mean >= 0.00005
            motion_pass = source_has_motion and output_motion_mean >= source_motion_mean * 0.30
            motion_requirement = "opaque-model ROI mean temporal MAE >= 30% of sampled Live2D source, whose mean must be >= 0.00005; otherwise inconclusive/fail"
        else:
            motion_pass = moving_pairs >= max(2, min(3, source_moving_pairs))
            motion_requirement = "enough pairs with temporal MAE >= 0.004 to reflect source motion"
        source_pass = sum(source_passes) >= 4
        report_segments.append({
            "segment": name, "timeline_frames": [start, end], "source": str(source_path),
            "samples": samples, "output_temporal_mae": output_motion,
            "source_temporal_mae": source_motion, "temporal_opaque_pixels": temporal_coverage,
            "motion_requirement": motion_requirement,
            "source_requirement": source_requirement, "motion_pass": motion_pass,
            "source_match_pass": source_pass, "passed": motion_pass and source_pass,
        })

    report = {
        "export": str(export), "fps_assumption": FPS, "export_size": [out_w, out_h],
        "method": "five interior frame samples per timeline segment; temporal change plus corresponding source-frame comparison",
        "limitations": [
            "This detects frozen or wrongly mapped source frames at sampled locations; it is not a full visual review.",
            "The Live2D comparison uses only opaque model pixels in ROI [1275,99,384,420]; it does not validate the background layer.",
            "Thresholds permit normal H.264 recompression but may need adjustment if a future export applies intentional color grading or transforms.",
        ],
        "segments": report_segments,
        "passed": all(segment["passed"] for segment in report_segments),
    }
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result": str(output_path), "passed": report["passed"],
                      "failed_segments": [s["segment"] for s in report_segments if not s["passed"]]}, ensure_ascii=False))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
