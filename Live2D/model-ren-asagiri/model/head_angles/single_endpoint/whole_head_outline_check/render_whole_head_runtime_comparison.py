"""Direct-SDK whole-head face-underfill comparison against the new guide.

The renderer loads the real exported model3 JSON directly.  It does not make
temporary model fixtures, call physics, warp a rendered model, or modify any
Cubism/runtime artifact.  When baseline and current hashes match it reports a
before-only/current-baseline diagnostic rather than claiming an after result.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import numpy as np
import pygame
from PIL import Image, ImageDraw, ImageFont
import live2d.v3 as live2d
from OpenGL.GL import GL_RGBA, GL_UNSIGNED_BYTE, glFinish, glReadPixels


OUT = Path(__file__).resolve().parent
SINGLE = OUT.parent
CURRENT = SINGLE / "face_runtime" / "Ren_face_endpoint.model3.json"
BASELINE = SINGLE / "archive" / "before_whole_head_outline_20260926" / "face_runtime" / "Ren_face_endpoint.model3.json"
TARGET = OUT / "whole_head_contour_target.json"
SIZE = (2000, 3000)
RENDER_SCALE = 0.5
PARAMETERS = {"ParamAngleX": -30.0, "ParamAngleY": -30.0}
BACKGROUND = (235, 232, 226)
REPORT = OUT / "whole_head_runtime_measurement.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def moc_path(model_path: Path) -> Path:
    model = json.loads(model_path.read_text(encoding="utf-8"))
    return model_path.parent / model["FileReferences"]["Moc"]


def render_direct(model_path: Path) -> np.ndarray:
    model = live2d.LAppModel()
    model.LoadModelJson(str(model_path))
    model.Resize(*SIZE)
    model.SetAutoBlinkEnable(False)
    model.SetAutoBreathEnable(False)
    try:
        for parameter, value in PARAMETERS.items():
            model.SetParameterValue(parameter, value)
        model._model.Update(1 / 30)
        live2d.clearBuffer(0, 0, 0, 0)
        model.Draw()
        glFinish()
        return np.frombuffer(
            glReadPixels(0, 0, *SIZE, GL_RGBA, GL_UNSIGNED_BYTE), np.uint8
        ).reshape(SIZE[1], SIZE[0], 4).copy()[::-1].copy()
    finally:
        model.DestroyRenderer()


def unpremultiply(raw: np.ndarray) -> np.ndarray:
    result = raw.copy()
    alpha = raw[:, :, 3:4].astype(np.float32)
    result[:, :, :3] = np.clip(
        np.rint(raw[:, :, :3].astype(np.float32) * 255 / np.maximum(alpha, 1)), 0, 255
    )
    return result


def composite(raw: np.ndarray, background=BACKGROUND) -> Image.Image:
    alpha = raw[:, :, 3:4].astype(np.float32) / 255
    rgb = np.clip(
        np.rint(raw[:, :, :3].astype(np.float32) + np.asarray(background, dtype=np.float32) * (1 - alpha)),
        0,
        255,
    ).astype(np.uint8)
    return Image.fromarray(rgb, "RGB")


def alpha_edge(raw: np.ndarray, threshold: int = 16) -> np.ndarray:
    mask = raw[:, :, 3] >= threshold
    padded = np.pad(mask, 1, constant_values=False)
    interior = (
        padded[:-2, 1:-1]
        & padded[2:, 1:-1]
        & padded[1:-1, :-2]
        & padded[1:-1, 2:]
    )
    return mask & ~interior


def stats(values: list[float]) -> dict:
    array = np.asarray(values, dtype=float)
    return {
        "count": int(len(array)),
        "min": round(float(array.min()), 3),
        "p50": round(float(np.percentile(array, 50)), 3),
        "p90": round(float(np.percentile(array, 90)), 3),
        "max": round(float(array.max()), 3),
        "mean": round(float(array.mean()), 3),
    }


def target_render_points(records: list[dict]) -> list[tuple[float, float]]:
    return [(row["canvas_px"][0] * RENDER_SCALE, row["canvas_px"][1] * RENDER_SCALE) for row in records]


def measure(edge: np.ndarray, records: list[dict]) -> tuple[list[dict], dict]:
    ys, xs = np.nonzero(edge)
    if not len(xs):
        raise RuntimeError("No alpha edge in direct SDK face-only render.")
    edge_xy = np.column_stack([xs, ys]).astype(float)
    rows = []
    for index, record in enumerate(records):
        target = np.asarray(record["canvas_px"], dtype=float) * RENDER_SCALE
        distances2 = np.sum((edge_xy - target) ** 2, axis=1)
        closest = int(np.argmin(distances2))
        distance = float(np.sqrt(distances2[closest]))
        rows.append({
            "sample": index + 1,
            "outline_rough_px": record["outline_rough_px"],
            "target_canvas_px": record["canvas_px"],
            "target_render_px": [round(float(target[0]), 3), round(float(target[1]), 3)],
            "nearest_alpha_edge_render_px": [int(edge_xy[closest, 0]), int(edge_xy[closest, 1])],
            "distance_render_px": round(distance, 3),
            "distance_canvas_px": round(distance / RENDER_SCALE, 3),
        })
    return rows, stats([row["distance_canvas_px"] for row in rows])


def equal_arc_bins(rows: list[dict], names: list[str]) -> dict:
    answer = {}
    for index, name in enumerate(names):
        lo = round(index * len(rows) / len(names))
        hi = round((index + 1) * len(rows) / len(names))
        answer[name] = {
            "sample_range_1_based": [lo + 1, hi],
            "distance_canvas_px": stats([row["distance_canvas_px"] for row in rows[lo:hi]]),
        }
    return answer


def draw_dashed(draw: ImageDraw.ImageDraw, points, fill, width=2, dash=12, gap=8) -> None:
    for a, b in zip(points, points[1:]):
        distance = max(float(np.hypot(b[0] - a[0], b[1] - a[1])), 1.0)
        for start in np.arange(0, distance, dash + gap):
            end = min(start + dash, distance)
            draw.line((
                a[0] + (b[0] - a[0]) * start / distance,
                a[1] + (b[1] - a[1]) * start / distance,
                a[0] + (b[0] - a[0]) * end / distance,
                a[1] + (b[1] - a[1]) * end / distance,
            ), fill=fill, width=width)


def guide_reference(target: dict) -> Image.Image:
    guide = Image.open(OUT / target["artifacts"]["full_canvas_guide"]).convert("RGBA")
    guide = guide.resize(SIZE, Image.Resampling.LANCZOS)
    neutral = Image.new("RGBA", SIZE, BACKGROUND + (255,))
    neutral.alpha_composite(guide)
    return neutral.convert("RGB")


def labelled_crop(image: Image.Image, label: str, crop, font) -> Image.Image:
    piece = image.crop(crop).resize(((crop[2] - crop[0]) * 2, (crop[3] - crop[1]) * 2), Image.Resampling.NEAREST)
    result = Image.new("RGB", (piece.width, piece.height + 44), (248, 247, 243))
    result.paste(piece, (0, 44))
    ImageDraw.Draw(result).text((10, 10), label, fill=(28, 33, 42), font=font)
    return result


def image_delta(before: np.ndarray, current: np.ndarray) -> dict:
    delta = np.abs(current.astype(np.int16) - before.astype(np.int16))
    return {
        "max_channel_difference": int(delta.max()),
        "pixels_with_any_rgba_difference": int(np.count_nonzero(np.max(delta, axis=2))),
    }


def main() -> None:
    for path in (CURRENT, BASELINE, TARGET):
        if not path.exists():
            raise FileNotFoundError(path)
    target = json.loads(TARGET.read_text(encoding="utf-8"))
    face_records = target["evaluation_samples"]["face_visible_2px_spacing"]
    scalp_records = target["evaluation_samples"]["scalp_inferred_3px_spacing"]
    current_hash = sha256(moc_path(CURRENT))
    baseline_hash = sha256(moc_path(BASELINE))

    pygame.display.init()
    live2d.init()
    try:
        pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)
        pygame.display.set_mode(SIZE, pygame.OPENGL | pygame.DOUBLEBUF | pygame.HIDDEN)
        live2d.glInit()
        baseline_raw = render_direct(BASELINE)
        current_raw = baseline_raw.copy() if current_hash == baseline_hash else render_direct(CURRENT)
    finally:
        live2d.dispose()
        pygame.quit()

    baseline_edge = alpha_edge(baseline_raw)
    current_edge = alpha_edge(current_raw)
    baseline_face_rows, baseline_face_summary = measure(baseline_edge, face_records)
    baseline_scalp_rows, baseline_scalp_summary = measure(baseline_edge, scalp_records)
    current_face_rows, current_face_summary = measure(current_edge, face_records)
    current_scalp_rows, current_scalp_summary = measure(current_edge, scalp_records)

    baseline_review = composite(baseline_raw)
    current_review = composite(current_raw)
    guide_review = guide_reference(target)
    baseline_review.save(OUT / "baseline_bareface_2000x3000.png")
    current_review.save(OUT / "current_bareface_2000x3000.png")
    Image.fromarray(unpremultiply(current_raw), "RGBA").save(OUT / "current_bareface_2000x3000_rgba.png")

    overlay = current_review.copy()
    draw = ImageDraw.Draw(overlay)
    ys, xs = np.nonzero(current_edge)
    draw.point(list(zip(xs.tolist(), ys.tolist())), fill=(237, 69, 68))
    face_points = target_render_points(face_records)
    scalp_points = target_render_points(scalp_records)
    draw.line(face_points, fill=(0, 225, 255), width=2, joint="curve")
    draw_dashed(draw, scalp_points, fill=(255, 178, 46), width=2)
    for x, y in face_points[::8]:
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(0, 225, 255))
    for x, y in scalp_points[::8]:
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 178, 46))
    overlay.save(OUT / "current_vs_whole_head_guide_overlay_2000x3000.png")

    crop = (770, 170, 1170, 590)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
    panels = [
        labelled_crop(guide_review, "New guide: cyan face / amber inferred scalp", crop, font),
        labelled_crop(baseline_review, "Archived before bare face — direct SDK", crop, font),
        labelled_crop(current_review, "Current bare face — direct SDK", crop, font),
        labelled_crop(overlay, "Red current alpha / cyan face / amber scalp", crop, font),
    ]
    sheet = Image.new("RGB", (panels[0].width * len(panels), panels[0].height), (248, 247, 243))
    for index, panel in enumerate(panels):
        sheet.paste(panel, (index * panel.width, 0))
    sheet.save(OUT / "whole_head_runtime_guide_4up.png")

    hashes_equal = baseline_hash == current_hash
    report = {
        "status": "baseline_only_current_runtime_unchanged" if hashes_equal else "before_after_measurement_complete",
        "scope": "Face-runtime-only direct-SDK render at ParamAngleX=-30, ParamAngleY=-30. No hair, eyes, ears, mouth, physics update, temporary model fixture, or post-render model warp.",
        "acceptance": "diagnostic_only; Boss visual acceptance remains required",
        "direct_model_loading": {
            "baseline_model3_json": str(BASELINE),
            "current_model3_json": str(CURRENT),
            "temporary_fixture": False,
            "physics_update_called": False,
            "render_warp_applied": False,
        },
        "models": {
            "baseline_moc3_sha256": baseline_hash,
            "current_moc3_sha256": current_hash,
            "hashes_equal": hashes_equal,
            "render_delta": image_delta(baseline_raw, current_raw),
        },
        "target": {
            "path": str(TARGET),
            "sha256": sha256(TARGET),
            "outline_sha256": target["inputs"]["outline"]["sha256"],
            "classification": target["classification"],
        },
        "distance_canvas_px": {
            "baseline": {
                "face_visible_observed": baseline_face_summary,
                "scalp_hair_hidden_inferred": baseline_scalp_summary,
                "face_equal_arc_bins": equal_arc_bins(baseline_face_rows, ["left_cheek", "left_jaw", "chin", "right_jaw", "right_cheek"]),
                "scalp_equal_arc_bins": equal_arc_bins(baseline_scalp_rows, ["right_side", "upper_right", "upper_left", "left_side"]),
            },
            "current": {
                "face_visible_observed": current_face_summary,
                "scalp_hair_hidden_inferred": current_scalp_summary,
                "face_equal_arc_bins": equal_arc_bins(current_face_rows, ["left_cheek", "left_jaw", "chin", "right_jaw", "right_cheek"]),
                "scalp_equal_arc_bins": equal_arc_bins(current_scalp_rows, ["right_side", "upper_right", "upper_left", "left_side"]),
            },
        },
        "sample_counts": {"face_visible_observed": len(face_records), "scalp_hair_hidden_inferred": len(scalp_records)},
        "artifacts": {
            "four_up": "whole_head_runtime_guide_4up.png",
            "overlay": "current_vs_whole_head_guide_overlay_2000x3000.png",
            "baseline": "baseline_bareface_2000x3000.png",
            "current": "current_bareface_2000x3000.png",
            "current_rgba": "current_bareface_2000x3000_rgba.png",
        },
        "interpretation_limits": [
            "The scalp target is intentionally inferred under hair and must be reviewed as a shape/coverage guide rather than a visible-pixel truth.",
            "Ear outer contours are excluded from face-underfill distance metrics.",
            "Nearest alpha-edge distances cannot prove mesh topology, triangle orientation, or continuous-motion quality.",
            "When baseline and current moc3 hashes are equal, this is a before-only diagnostic and no after improvement is claimed.",
        ],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "hashes_equal": hashes_equal, "baseline": report["distance_canvas_px"]["baseline"], "current": report["distance_canvas_px"]["current"], "artifacts": report["artifacts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
