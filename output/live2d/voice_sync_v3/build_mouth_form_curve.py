"""Build an editorial ParamMouthForm curve from the locked v2 alignment.

The v2 ParamMouthOpenY values are copied verbatim.  Mouth form is a Japanese
performance-design approximation (width/roundness), not measured lip tracking.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
V2 = ROOT.parent / "voice_sync_v2"
FPS = 30
FRAME_COUNT = 478
VOWEL_FORM = {"a": 0.0, "e": 0.35, "i": 0.9, "u": -0.72, "o": -1.0}
SILENCE = {"sil", "silb", "sile", "sp", "pau"}
CLOSURES = {"m", "b", "p", "cl"}
SMOOTH_SIGMA_S = 0.040
NEUTRAL_WINDOW_S = 0.090


def phone_name(phone: dict) -> str:
    return str(phone["phoneme"]).lower().rstrip(":")


def gaussian_smooth(values: np.ndarray, sigma_s: float, sample_rate: int) -> np.ndarray:
    radius = max(1, round(sigma_s * sample_rate * 3))
    x = np.arange(-radius, radius + 1) / sample_rate
    kernel = np.exp(-0.5 * (x / sigma_s) ** 2)
    return np.convolve(values, kernel / kernel.sum(), mode="same")


def smoothstep(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def main() -> None:
    v2_rows = list(csv.DictReader((V2 / "mouth_curve.csv").open(encoding="utf-8-sig", newline="")))
    if len(v2_rows) != FRAME_COUNT:
        raise ValueError(f"Expected {FRAME_COUNT} v2 frames, got {len(v2_rows)}")
    alignment = json.loads((V2 / "alignment" / "phonemes.json").read_text(encoding="utf-8-sig"))
    phones = alignment["phonemes"] if isinstance(alignment, dict) else alignment
    if not phones:
        raise ValueError("No aligned phonemes")

    # A 1 ms working curve lets form pass naturally through ordinary consonants.
    duration_s = FRAME_COUNT / FPS
    sample_rate = 1000
    timeline = np.arange(0.0, duration_s, 1.0 / sample_rate)
    vowel_centers = [
        ((float(p["start_s"]) + float(p["end_s"])) / 2.0, VOWEL_FORM[phone_name(p)])
        for p in phones
        if phone_name(p) in VOWEL_FORM
    ]
    centers_t = np.array([t for t, _ in vowel_centers])
    centers_v = np.array([v for _, v in vowel_centers])
    raw = np.interp(timeline, centers_t, centers_v, left=0.0, right=0.0)

    # Do not make every consonant its own form.  The interpolation above carries
    # the surrounding vowel shape across ordinary consonants; only real closure
    # and silence pull deliberately and gradually toward ParamMouthForm=0.
    neutral_mask = np.zeros_like(raw, dtype=bool)
    neutral_intervals = []
    for p in phones:
        kind = phone_name(p)
        if kind not in SILENCE | CLOSURES:
            continue
        start, end = float(p["start_s"]), float(p["end_s"])
        neutral_mask |= (timeline >= start) & (timeline < end)
        neutral_intervals.append(
            {
                "start_s": round(start, 6),
                "end_s": round(end, 6),
                "phoneme": p["phoneme"],
                "reason": "silence" if kind in SILENCE else "lip_closure",
            }
        )

    form = gaussian_smooth(raw, SMOOTH_SIGMA_S, sample_rate)
    # The envelope reaches neutral inside m/b/p and silence, then eases over
    # 90 ms at each boundary so a closed mouth does not display form chatter.
    if neutral_mask.any():
        distance = np.full(len(timeline), np.inf)
        neutral_idx = np.flatnonzero(neutral_mask)
        for i in range(len(timeline)):
            distance[i] = np.min(np.abs(i - neutral_idx)) / sample_rate
        envelope = smoothstep(distance / NEUTRAL_WINDOW_S)
        form *= envelope

    frame_times = np.arange(FRAME_COUNT) / FPS
    frame_form = np.interp(frame_times, timeline, form)
    frame_form[np.abs(frame_form) < 0.004] = 0.0
    frame_form = np.clip(np.round(frame_form, 6), -1.0, 1.0)

    rows = []
    for original, value in zip(v2_rows, frame_form):
        row = dict(original)  # mouth_open_y and every v2 column remain untouched.
        row["mouth_form"] = float(value)
        rows.append(row)
    with (ROOT / "mouth_curve.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    def linear_segments(values: list[float]) -> list[float]:
        segments: list[float] = [0.0, values[0]]
        for frame, value in enumerate(values[1:], start=1):
            segments.extend([0, round(frame / FPS, 6), value])
        return segments

    open_values = [float(row["mouth_open_y"]) for row in v2_rows]
    form_values = [float(value) for value in frame_form]
    motion = {
        "Version": 3,
        "Meta": {
            "Duration": FRAME_COUNT / FPS,
            "Fps": FPS,
            "Loop": False,
            "CurveCount": 2,
            "TotalSegmentCount": (FRAME_COUNT - 1) * 2,
            "TotalPointCount": FRAME_COUNT * 2,
            "AreBeziersRestricted": True,
        },
        "Curves": [
            {"Target": "Parameter", "Id": "ParamMouthOpenY", "Segments": linear_segments(open_values)},
            {"Target": "Parameter", "Id": "ParamMouthForm", "Segments": linear_segments(form_values)},
        ],
        "UserData": [],
    }
    (ROOT / "voice_sync.motion3.json").write_text(json.dumps(motion, ensure_ascii=False), encoding="utf-8")

    profile = {
        "parameter": "ParamMouthForm",
        "semantics": {"-1": "narrower, rounder", "0": "current neutral shape", "+1": "wider shape"},
        "vowel_targets": VOWEL_FORM,
        "editorial_basis": "Japanese mouth-shape performance design; this is not measured lip tracking.",
        "japanese_u_note": "u is restrained at -0.72 and is not treated as an English-style strong oo rounding.",
        "coarticulation": "Ordinary consonants bridge adjacent vowel forms; m/b/p and silence ease to neutral.",
        "neutralization": {"sigma_seconds": SMOOTH_SIGMA_S, "boundary_ease_seconds": NEUTRAL_WINDOW_S},
        "alignment_source": "../voice_sync_v2/alignment/phonemes.json",
        "alignment_method": alignment.get("method") if isinstance(alignment, dict) else None,
        "frame_count": FRAME_COUNT,
        "fps": FPS,
        "duration_seconds": FRAME_COUNT / FPS,
        "neutral_intervals": neutral_intervals,
        "visual_status": "Pending: Cubism warp-deformer implementation and real render review are owned by the GUI workflow.",
    }
    (ROOT / "mouth_form_profile.json").write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    curve_meta = {
        "method": "Locked v2 aperture plus aligned-Japanese-vowel editorial mouth form",
        "source_v2": "../voice_sync_v2/mouth_curve.csv",
        "mouth_open_y": "Copied verbatim from v2; no aperture redesign.",
        "mouth_form_profile": "mouth_form_profile.json",
        "frame_count": FRAME_COUNT,
        "fps": FPS,
        "frames": rows,
    }
    (ROOT / "mouth_curve.json").write_text(json.dumps(curve_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    same_open = all(a["mouth_open_y"] == b["mouth_open_y"] for a, b in zip(v2_rows, rows))
    print(json.dumps({
        "frames": len(rows), "open_curve_verbatim": same_open,
        "form_range": [float(frame_form.min()), float(frame_form.max())],
        "last_12_form": form_values[-12:], "neutral_intervals": len(neutral_intervals),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
