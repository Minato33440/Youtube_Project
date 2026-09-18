#!/usr/bin/env python3
"""Build a deterministic 30 fps ParamMouthOpenY curve from a PCM WAV file.

The timestamps are video-frame centres (n / 30), so audio t=0 remains aligned
with video t=0.  Output is intended as an import/reference curve; inspect the
result with the model before accepting it as final lip-sync.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import wave
from pathlib import Path

import numpy as np


FPS = 30.0
WINDOW_SECONDS = 1.0 / 30.0
MAX_OPEN = 0.85
ATTACK_SECONDS = 0.060
RELEASE_SECONDS = 0.080
GATE_ON_FRACTION = 0.10
GATE_OFF_FRACTION = 0.055
MIN_ACTIVE_AMPLITUDE = 0.018
# N01.wav matched to this clip at approximately +0.0007 s (correlation .976).
# Its duration is 15.600884 s. A separate short transient at 15.8667 s is
# outside the narration and must not reopen the mouth. Audio is not altered.
NARRATION_END_SECONDS = 15.602


def load_mono_pcm16(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as source:
        if source.getsampwidth() != 2:
            raise ValueError("Expected PCM16 WAV")
        rate, channels, count = source.getframerate(), source.getnchannels(), source.getnframes()
        raw = np.frombuffer(source.readframes(count), dtype="<i2").astype(np.float64) / 32768.0
    if channels > 1:
        raw = raw.reshape(-1, channels).mean(axis=1)
    return raw, rate


def run_ranges(values: np.ndarray, predicate, minimum_frames: int) -> list[dict[str, float | int]]:
    ranges, start = [], None
    for i, value in enumerate(values):
        if predicate(float(value)) and start is None:
            start = i
        if (not predicate(float(value)) or i == len(values) - 1) and start is not None:
            end = i if predicate(float(value)) and i == len(values) - 1 else i - 1
            if end - start + 1 >= minimum_frames:
                ranges.append({"start_frame": start, "end_frame": end, "start_s": round(start / FPS, 6), "end_s": round(end / FPS, 6)})
            start = None
    return ranges


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("audio_mono_44100_pcm16.wav"))
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    samples, rate = load_mono_pcm16(args.input)
    duration = len(samples) / rate
    frame_count = round(duration * FPS)
    times = np.arange(frame_count, dtype=np.float64) / FPS
    half_window = round(WINDOW_SECONDS * rate / 2)
    rms = np.empty(frame_count)
    for frame, time in enumerate(times):
        centre = round(time * rate)
        start, end = max(0, centre - half_window), min(len(samples), centre + half_window)
        rms[frame] = math.sqrt(float(np.mean(np.square(samples[start:end])))) if end > start else 0.0

    floor = float(np.percentile(rms, 15))
    ceiling = float(np.percentile(rms, 95))
    span = max(ceiling - floor, 1e-9)
    normalized = np.clip((rms - floor) / span, 0.0, 1.0)
    # A square-root response exposes soft syllables without making peaks exceed MAX_OPEN.
    shaped = np.sqrt(normalized)
    gate_on, gate_off = GATE_ON_FRACTION, GATE_OFF_FRACTION
    gated = np.zeros(frame_count)
    is_open = False
    for i, value in enumerate(shaped):
        if is_open:
            is_open = value >= gate_off
        else:
            is_open = value >= gate_on
        gated[i] = value if is_open else 0.0

    gated[times >= NARRATION_END_SECONDS] = 0.0

    attack_alpha = 1.0 - math.exp(-(1.0 / FPS) / ATTACK_SECONDS)
    release_alpha = 1.0 - math.exp(-(1.0 / FPS) / RELEASE_SECONDS)
    envelope = np.zeros(frame_count)
    for i, target in enumerate(gated):
        previous = envelope[i - 1] if i else 0.0
        alpha = attack_alpha if target > previous else release_alpha
        envelope[i] = previous + alpha * (target - previous)
    envelope[envelope < MIN_ACTIVE_AMPLITUDE] = 0.0
    values = np.round(np.clip(envelope * MAX_OPEN, 0.0, MAX_OPEN), 6)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = [{"frame": int(i), "time_s": round(float(t), 6), "rms": round(float(r), 8), "mouth_open_y": float(v)} for i, (t, r, v) in enumerate(zip(times, rms, values))]
    with (args.output_dir / "mouth_curve.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader(); writer.writerows(rows)

    timeline_duration = frame_count / FPS
    meta = {
        "source": {"wav": str(args.input.resolve()), "sample_rate_hz": rate, "duration_s": round(duration, 6), "video_fps": FPS, "frame_count": frame_count, "timeline_duration_s": round(timeline_duration, 6)},
        "parameter": "ParamMouthOpenY",
        "method": {"rms_window_s": WINDOW_SECONDS, "rms_window_alignment": "centred at n / 30 seconds", "noise_floor_percentile": 15, "ceiling_percentile": 95, "max_open": MAX_OPEN, "attack_s": ATTACK_SECONDS, "release_s": RELEASE_SECONDS, "gate_on_fraction": gate_on, "gate_off_fraction": gate_off, "min_active_amplitude": MIN_ACTIVE_AMPLITUDE},
        "statistics": {"rms_min": round(float(rms.min()), 8), "rms_max": round(float(rms.max()), 8), "rms_floor_p15": round(floor, 8), "rms_ceiling_p95": round(ceiling, 8), "mouth_max": float(values.max()), "active_frames": int(np.count_nonzero(values)), "active_seconds": round(float(np.count_nonzero(values) / FPS), 6), "onsets": run_ranges(values, lambda v: v >= 0.05, 3), "silences": run_ranges(values, lambda v: v < 0.018, 5)},
        "frames": rows,
    }
    meta['method']['narration_end_s'] = NARRATION_END_SECONDS
    meta['method']['excluded_tail_reason'] = 'Short transient after matched N01 narration; original audio retained unchanged.'
    (args.output_dir / "mouth_curve.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Cubism Motion3 linear segments: first point then type=0/end point pairs.
    segments = [0.0, float(values[0])]
    for time, value in zip(times[1:], values[1:]):
        segments.extend([0, round(float(time), 6), float(value)])
    motion = {"Version": 3, "Meta": {"Duration": round(timeline_duration, 6), "Fps": FPS, "Loop": False, "CurveCount": 1, "TotalSegmentCount": frame_count - 1, "TotalPointCount": frame_count, "AreBeziersRestricted": True}, "Curves": [{"Target": "Parameter", "Id": "ParamMouthOpenY", "Segments": segments}], "UserData": []}
    (args.output_dir / "voice_sync.motion3.json").write_text(json.dumps(motion, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
