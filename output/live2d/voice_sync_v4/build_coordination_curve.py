"""Build reusable, editorially-timed eye/breath/neck curves for the approved v3 mouth.

This stage deliberately does not infer physiology from audio.  Phoneme alignment
anchors pauses, while blink and emphasis choices are a restrained performance
design that must be reviewed on the Cubism model.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
V3 = ROOT.parent / "voice_sync_v3"
V2_ALIGNMENT = ROOT.parent / "voice_sync_v2" / "alignment" / "phonemes.json"
PROFILE_PATH = ROOT / "performance_profile.json"
FPS, FRAME_COUNT = 30, 478
DURATION = FRAME_COUNT / FPS


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def add_pulse(values: list[float], center_s: float, width_s: float, amplitude: float) -> None:
    """Add a raised-cosine pulse, zero at each edge and peak at center."""
    for frame in range(FRAME_COUNT):
        distance = abs(frame / FPS - center_s)
        if distance <= width_s:
            values[frame] += amplitude * 0.5 * (1.0 + math.cos(math.pi * distance / width_s))


def add_blink(values: list[float], start_s: float, profile: list[float]) -> None:
    start = round(start_s * FPS)
    for offset, value in enumerate(profile):
        frame = start + offset
        if 0 <= frame < FRAME_COUNT:
            values[frame] = min(values[frame], value)


def linear_segments(values: list[float]) -> list[float]:
    segments: list[float] = [0.0, values[0]]
    for frame, value in enumerate(values[1:], start=1):
        segments.extend([0, round(frame / FPS, 6), value])
    return segments


def main() -> None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    rows = list(csv.DictReader((V3 / "mouth_curve.csv").open(encoding="utf-8-sig", newline="")))
    if len(rows) != FRAME_COUNT:
        raise ValueError(f"Expected {FRAME_COUNT} v3 frames, got {len(rows)}")
    if not {"mouth_open_y", "mouth_form"}.issubset(rows[0]):
        raise ValueError("v3 mouth columns are missing")

    alignment = json.loads(V2_ALIGNMENT.read_text(encoding="utf-8-sig"))
    pauses = []
    for phone in alignment["phonemes"]:
        if str(phone["phoneme"]).lower() not in {"sp", "sil", "pau"}:
            continue
        start, end = float(phone["start_s"]), float(phone["end_s"])
        if end - start >= float(profile["breath"]["long_pause_threshold_seconds"]):
            pauses.append({"start_s": round(start, 6), "end_s": round(end, 6), "duration_s": round(end - start, 6)})

    # Both eyes share the same curve so every blink includes an actual bilateral
    # closed frame.  The profile keeps one closed-frame hold and reopens slowly.
    blink_starts = [float(value) for value in profile["blink_starts_s"]]
    blink_profile = [float(value) for value in profile["blink_profile"]]
    min_blink_spacing = float(profile["minimum_blink_spacing_seconds"])
    if blink_profile != [1.0, 0.45, 0.0, 0.0, 0.25, 0.6, 0.84, 1.0]:
        raise ValueError("Blink profile must preserve the approved eight samples")
    if any(b - a < min_blink_spacing for a, b in zip(blink_starts, blink_starts[1:])):
        raise ValueError("Blink spacing violates the 2.2 s minimum")
    left_eye, right_eye = [1.0] * FRAME_COUNT, [1.0] * FRAME_COUNT
    for start in blink_starts:
        add_blink(left_eye, start, blink_profile)
        add_blink(right_eye, start, blink_profile)

    breath_profile = profile["breath"]
    # A gentle periodic baseline.  Wide pause pulses avoid a fast body jump,
    # and start/end fades make this isolated clip begin and finish at zero.
    breath = [float(breath_profile["baseline_center"]) + float(breath_profile["baseline_amplitude"]) * math.sin(2 * math.pi * (frame / FPS + float(breath_profile["phase_seconds"])) / float(breath_profile["period_seconds"])) for frame in range(FRAME_COUNT)]
    for pause in pauses:
        add_pulse(breath, (pause["start_s"] + pause["end_s"]) / 2, max(float(breath_profile["pause_half_width_seconds"]), pause["duration_s"] / 2), float(breath_profile["long_pause_extra_amplitude"]))
    for frame in range(FRAME_COUNT):
        time_s = frame / FPS
        start_gain = min(1.0, time_s / float(breath_profile["start_fade_seconds"]))
        end_gain = min(1.0, max(0.0, (((FRAME_COUNT - 1) / FPS) - time_s) / float(breath_profile["end_fade_seconds"])))
        breath[frame] *= min(start_gain, end_gain)
    breath = [clamp(value, 0.0, 1.0) for value in breath]

    # Small text-supported emphasis pulses.  The signs are staging choices only;
    # each is well inside ParamAngleZ's +/-30 technical range (observed rig
    # mapping: +/-30 is about +/-6 degrees in the rendered pose).
    emphasis = profile["neck"]["emphasis"]
    angle_z = [0.0] * FRAME_COUNT
    for item in emphasis:
        add_pulse(angle_z, float(item["time_s"]), float(profile["neck"]["pulse_half_width_seconds"]), float(item["angle_z"]))
    angle_z = [clamp(value, -6.0, 6.0) for value in angle_z]

    # Eye and neck settle at the end.  Breath is faded to zero above, but any
    # later idle clip still needs its own transition review.
    for frame in range(FRAME_COUNT - 4, FRAME_COUNT):
        left_eye[frame] = right_eye[frame] = 1.0
        angle_z[frame] = 0.0

    for values, low, high, name in [
        (left_eye, 0.0, 1.0, "ParamEyeLOpen"),
        (right_eye, 0.0, 1.0, "ParamEyeROpen"),
        (breath, 0.0, 1.0, "ParamBreath"),
        (angle_z, -6.0, 6.0, "ParamAngleZ"),
    ]:
        if not all(math.isfinite(value) and low <= value <= high for value in values):
            raise ValueError(f"Invalid values in {name}")

    fields = list(rows[0]) + ["eye_l_open", "eye_r_open", "breath", "angle_z"]
    performance_rows = []
    for frame, row in enumerate(rows):
        # Keep mouth source strings unparsed and unmodified in the emitted CSV.
        performance_rows.append({
            **row,
            "eye_l_open": f"{left_eye[frame]:.6f}",
            "eye_r_open": f"{right_eye[frame]:.6f}",
            "breath": f"{breath[frame]:.6f}",
            "angle_z": f"{angle_z[frame]:.6f}",
        })
    with (ROOT / "performance_curve.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(performance_rows)

    curves = [
        ("ParamMouthOpenY", [float(row["mouth_open_y"]) for row in rows]),
        ("ParamMouthForm", [float(row["mouth_form"]) for row in rows]),
        ("ParamEyeLOpen", left_eye), ("ParamEyeROpen", right_eye),
        ("ParamBreath", breath), ("ParamAngleZ", angle_z),
    ]
    motion = {"Version": 3, "Meta": {"Duration": DURATION, "Fps": FPS, "Loop": False,
              "CurveCount": len(curves), "TotalSegmentCount": (FRAME_COUNT - 1) * len(curves),
              "TotalPointCount": FRAME_COUNT * len(curves), "AreBeziersRestricted": True},
              "Curves": [{"Target": "Parameter", "Id": name, "Segments": linear_segments([round(value, 6) for value in values])} for name, values in curves],
              "UserData": []}
    (ROOT / "performance.motion3.json").write_text(json.dumps(motion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rules = {"stage": "2: coordinated eye, breath, and neck performance", "source": {"mouth_curve": "../voice_sync_v3/mouth_curve.csv", "phoneme_alignment": "../voice_sync_v2/alignment/phonemes.json", "alignment_method": alignment.get("method")},
             "frame_count": FRAME_COUNT, "fps": FPS, "duration_seconds": DURATION,
             "mouth_contract": "mouth_open_y and mouth_form are copied verbatim from v3; this stage does not redesign lips.",
             "performance_profile": "performance_profile.json", "eye": {"parameters": ["ParamEyeLOpen", "ParamEyeROpen"], "minimum_blink_spacing_seconds": min_blink_spacing, "blink_duration_seconds": (len(blink_profile) - 1) / FPS, "profile_samples": blink_profile, "left_right_timing": "same frames; both eyes close fully together"},
             "breath": {"parameter": "ParamBreath", "baseline": breath_profile, "range": [0.0, 1.0], "long_pause_threshold_seconds": breath_profile["long_pause_threshold_seconds"], "long_pause_extra_amplitude": breath_profile["long_pause_extra_amplitude"], "pause_half_width_seconds": breath_profile["pause_half_width_seconds"], "clip_fades_to_zero": {"start_seconds": breath_profile["start_fade_seconds"], "end_seconds": breath_profile["end_fade_seconds"]}},
             "neck": {"parameter": "ParamAngleZ", "used_range": [-6.0, 6.0], "observed_rig_context": "ParamAngleZ +/-30 corresponds to roughly +/-6 degrees in the current rig; values here are intentionally restrained parameter units.", "pulse_half_width_seconds": profile["neck"]["pulse_half_width_seconds"]},
             "end_state": {"eyes": 1.0, "angle_z": 0.0, "breath": "fades to zero; transition into any idle motion requires visual review"},
             "editorial_status": "Timing and emphasis are editorial performance design, not physiologically measured motion or face tracking."}
    def neck_evidence(item: dict) -> dict:
        start, end = float(item["time_s"]) - float(profile["neck"]["pulse_half_width_seconds"]), float(item["time_s"]) + float(profile["neck"]["pulse_half_width_seconds"])
        phones = [{"phoneme": phone["phoneme"], "mora": phone["mora"], "start_s": round(float(phone["start_s"]), 6), "end_s": round(float(phone["end_s"]), 6), "sentence": phone["sentence"]} for phone in alignment["phonemes"] if float(phone["end_s"]) >= start and float(phone["start_s"]) <= end]
        mora_rows = [row["mora"] for row in rows if start <= float(row["time_s"]) <= end and row["mora"]]
        return {**item, "manual_editorial_time": True, "source_window_s": [round(start, 6), round(end, 6)], "alignment_phonemes": phones, "v3_moras_in_window": list(dict.fromkeys(mora_rows))}
    events = {"long_pauses_from_alignment": pauses, "blinks": [{"start_s": start, "start_frame": round(start * FPS), "samples": blink_profile, "eyes": "same timing"} for start in blink_starts], "neck_emphasis": [neck_evidence(item) for item in emphasis],
              "note": "Blink and neck placements are manual editorial choices. Pause intervals and neck evidence are checked against forced phoneme alignment and v3 CSV mora rows; they are not motion capture."}
    performance = {"method": "Approved v3 mouth plus staged editorial coordination", "frame_count": FRAME_COUNT, "fps": FPS, "duration_seconds": DURATION, "frames": performance_rows,
                   "editorial_status": rules["editorial_status"]}
    (ROOT / "coordination_rules.json").write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "events.json").write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "performance_curve.json").write_text(json.dumps(performance, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"frames": len(performance_rows), "blink_count": len(blink_starts), "long_pause_count": len(pauses), "breath_range": [round(min(breath), 6), round(max(breath), 6)], "angle_z_range": [round(min(angle_z), 6), round(max(angle_z), 6)]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
