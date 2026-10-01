"""Render the exported face-underfill endpoint and compare it with the fixed source guide.

Read-only inspection: this script does not modify the cmo3, model3 JSON, source
illustration, textures, or Cubism project.  It deliberately loads only
single_endpoint/face_runtime, not the full runtime.
"""
from __future__ import annotations

import json
import os
import hashlib
from pathlib import Path

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import numpy as np
import pygame
from PIL import Image, ImageDraw, ImageFont
import live2d.v3 as live2d
from OpenGL.GL import GL_RGBA, GL_UNSIGNED_BYTE, glFinish, glReadPixels


ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "face_runtime" / "Ren_face_endpoint.model3.json"
GUIDE = ROOT / "guide" / "looking_down_2_source_landmark_guide.json"
SOURCE = Path(r"C:\Python\REX_AI\Youtube_Project\Live2D\model-ren-asagiri\art\Looking_down\Looking_down (2).png")
OUT = ROOT / "contour_check"
SIZE = (2000, 3000)  # One-half of the 4000 x 6000 guide canvas.
FULL_CANVAS_SCALE = 1.2904500571168767
FULL_CANVAS_OFFSET = np.array([1404.826424299698, 161.11685212010656])
RENDER_SCALE = 0.5
PARAMETERS = {"ParamAngleX": -30.0, "ParamAngleY": -30.0}
BACKGROUND = (235, 232, 226)


def unpremultiply(raw: np.ndarray) -> np.ndarray:
    result = raw.copy()
    alpha = raw[:, :, 3:4].astype(np.float32)
    result[:, :, :3] = np.clip(
        np.rint(raw[:, :, :3].astype(np.float32) * 255 / np.maximum(alpha, 1)), 0, 255
    )
    return result


def composite(raw: np.ndarray) -> Image.Image:
    alpha = raw[:, :, 3:4].astype(np.float32) / 255
    rgb = np.clip(
        np.rint(raw[:, :, :3].astype(np.float32) + np.asarray(BACKGROUND, dtype=np.float32) * (1 - alpha)),
        0,
        255,
    ).astype(np.uint8)
    return Image.fromarray(rgb, "RGB")


def source_to_render(point: list[float] | tuple[float, float]) -> tuple[float, float]:
    return tuple((FULL_CANVAS_OFFSET + np.asarray(point, dtype=float) * FULL_CANVAS_SCALE) * RENDER_SCALE)


def resample_polyline(points: list[dict], count: int) -> list[dict]:
    xy = np.asarray([p["source_px"] for p in points], dtype=float)
    lengths = np.linalg.norm(xy[1:] - xy[:-1], axis=1)
    cumulative = np.r_[0.0, np.cumsum(lengths)]
    result = []
    for i, distance in enumerate(np.linspace(0, cumulative[-1], count), start=1):
        segment = min(np.searchsorted(cumulative, distance, side="right") - 1, len(lengths) - 1)
        fraction = (distance - cumulative[segment]) / max(lengths[segment], 1e-9)
        point = xy[segment] * (1 - fraction) + xy[segment + 1] * fraction
        result.append({"sample": i, "source_px": [round(float(point[0]), 3), round(float(point[1]), 3)]})
    return result


def alpha_outer_boundary(raw: np.ndarray) -> np.ndarray:
    """Return visible alpha outer-edge pixels. Interior holes are retained if present."""
    mask = raw[:, :, 3] >= 16
    padded = np.pad(mask, 1, constant_values=False)
    neighbours_all_opaque = (
        padded[:-2, 1:-1]
        & padded[2:, 1:-1]
        & padded[1:-1, :-2]
        & padded[1:-1, 2:]
    )
    return mask & ~neighbours_all_opaque


def nearest_boundary_samples(boundary: np.ndarray, samples: list[dict]) -> tuple[list[dict], dict]:
    ys, xs = np.nonzero(boundary)
    if not len(xs):
        raise RuntimeError("No visible alpha boundary was found in the exported face-underfill render.")
    edge_xy = np.column_stack([xs, ys]).astype(float)
    records = []
    for sample in samples:
        target = np.asarray(source_to_render(sample["source_px"]), dtype=float)
        squared = np.sum((edge_xy - target) ** 2, axis=1)
        index = int(np.argmin(squared))
        distance = float(np.sqrt(squared[index]))
        nearest = edge_xy[index]
        records.append({
            **sample,
            "target_render_px": [round(float(target[0]), 3), round(float(target[1]), 3)],
            "nearest_model_alpha_edge_render_px": [int(nearest[0]), int(nearest[1])],
            "min_distance_render_px": round(distance, 3),
            "min_distance_full_canvas_px": round(distance / RENDER_SCALE, 3),
        })
    distances = np.asarray([r["min_distance_render_px"] for r in records], dtype=float)
    return records, {
        "count": int(len(records)),
        "render_px": {"min": round(float(distances.min()), 3), "median": round(float(np.median(distances)), 3), "max": round(float(distances.max()), 3), "mean": round(float(distances.mean()), 3)},
        "full_canvas_px": {"min": round(float(distances.min() / RENDER_SCALE), 3), "median": round(float(np.median(distances) / RENDER_SCALE), 3), "max": round(float(distances.max() / RENDER_SCALE), 3), "mean": round(float(distances.mean() / RENDER_SCALE), 3)},
    }


def line_and_points(draw: ImageDraw.ImageDraw, samples: list[dict], color: tuple[int, int, int], width: int = 3) -> None:
    coords = [source_to_render(s["source_px"]) for s in samples]
    draw.line(coords, fill=color, width=width, joint="curve")
    for x, y in coords:
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=color, outline=(20, 20, 20))


def labeled_crop(image: Image.Image, label: str, box: tuple[int, int, int, int], font: ImageFont.FreeTypeFont) -> Image.Image:
    crop = image.crop(box)
    result = Image.new("RGB", (crop.width, crop.height + 44), (248, 247, 243))
    result.paste(crop, (0, 44))
    ImageDraw.Draw(result).text((12, 11), label, fill=(31, 36, 45), font=font)
    return result


def make_reference_full() -> Image.Image:
    source = Image.open(SOURCE).convert("RGBA")
    scaled = source.resize((round(source.width * FULL_CANVAS_SCALE * RENDER_SCALE), round(source.height * FULL_CANVAS_SCALE * RENDER_SCALE)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", SIZE, BACKGROUND + (255,))
    canvas.alpha_composite(scaled, (round(FULL_CANVAS_OFFSET[0] * RENDER_SCALE), round(FULL_CANVAS_OFFSET[1] * RENDER_SCALE)))
    return canvas.convert("RGB")


def main() -> None:
    if not MODEL.exists():
        raise FileNotFoundError(f"Missing {MODEL}; wait for the Cubism face_runtime export to finish.")
    if not GUIDE.exists():
        raise FileNotFoundError(GUIDE)
    OUT.mkdir(exist_ok=True)
    guide = json.loads(GUIDE.read_text(encoding="utf-8"))
    observed = [p for p in guide["visible_facial_skin_outer_contour"]["points"] if p["reliability"] == "observed"]
    target_samples = resample_polyline(observed, 25)

    pygame.display.init()
    live2d.init()
    models = []
    try:
        pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)
        pygame.display.set_mode(SIZE, pygame.OPENGL | pygame.DOUBLEBUF | pygame.HIDDEN)
        live2d.glInit()
        model = live2d.LAppModel()
        model.LoadModelJson(str(MODEL))
        model.Resize(*SIZE)
        model.SetAutoBlinkEnable(False)
        model.SetAutoBreathEnable(False)
        models.append(model)
        ids = set(model.GetParamIds())
        for param, value in PARAMETERS.items():
            if param not in ids:
                raise RuntimeError(f"Exported face runtime lacks {param}.")
            model.SetParameterValue(param, value)
        model._model.Update(1 / 30)
        live2d.clearBuffer(0, 0, 0, 0)
        model.Draw()
        glFinish()
        raw = np.frombuffer(glReadPixels(0, 0, *SIZE, GL_RGBA, GL_UNSIGNED_BYTE), np.uint8).reshape(SIZE[1], SIZE[0], 4).copy()[::-1].copy()
    finally:
        for item in models:
            item.DestroyRenderer()
        live2d.dispose()
        pygame.quit()

    Image.fromarray(unpremultiply(raw), "RGBA").save(OUT / "face_underfill_render_2000x3000_rgba.png")
    face_composite = composite(raw)
    face_composite.save(OUT / "face_underfill_render_2000x3000_review.png")
    reference = make_reference_full()
    reference.save(OUT / "source_reference_2000x3000_review.png")
    boundary = alpha_outer_boundary(raw)
    samples, summary = nearest_boundary_samples(boundary, target_samples)

    overlay = face_composite.copy()
    overlay_draw = ImageDraw.Draw(overlay)
    edge_y, edge_x = np.nonzero(boundary)
    overlay_draw.point(list(zip(edge_x.tolist(), edge_y.tolist())), fill=(235, 75, 68))
    line_and_points(overlay_draw, samples, (0, 226, 255), width=3)
    landmarks = {x["id"]: x["source_px"] for x in guide["anatomical_landmarks"]}
    for landmark_id, color in (("nose_tip", (255, 73, 205)), ("chin_tip", (255, 73, 205))):
        x, y = source_to_render(landmarks[landmark_id])
        overlay_draw.line((x - 10, y, x + 10, y), fill=color, width=2)
        overlay_draw.line((x, y - 10, x, y + 10), fill=color, width=2)
    overlay.save(OUT / "face_underfill_alpha_target_overlay_2000x3000.png")

    # Crop around the placed face, while preserving the shared 2000x3000 space
    # in the three full-size source artifacts above.
    crop_box = (720, 300, 1250, 760)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 22)
    comparison = Image.new("RGB", ((crop_box[2] - crop_box[0]) * 3, (crop_box[3] - crop_box[1]) + 44), (248, 247, 243))
    comparison.paste(labeled_crop(reference, "Source art — fixed placement", crop_box, font), (0, 0))
    comparison.paste(labeled_crop(face_composite, "Exported face_underfill only", crop_box, font), (crop_box[2] - crop_box[0], 0))
    comparison.paste(labeled_crop(overlay, "Cyan target / red model alpha edge", crop_box, font), ((crop_box[2] - crop_box[0]) * 2, 0))
    comparison.save(OUT / "face_underfill_contour_comparison_3up.png")

    chin_sample = min(samples, key=lambda x: np.linalg.norm(np.asarray(x["source_px"]) - np.asarray(landmarks["chin_tip"])))
    report = {
        "status": "measurement_complete",
        "scope": "The render is the exported face_underfill-only face_runtime at ParamAngleX=-30, ParamAngleY=-30. It is not a full-runtime, hair, eye, or mouth validation.",
        "source": {"guide": str(GUIDE), "art": str(SOURCE), "guide_transform": {"full_canvas_scale": FULL_CANVAS_SCALE, "full_canvas_offset": FULL_CANVAS_OFFSET.tolist(), "render_scale": RENDER_SCALE}},
        "model": {
            "path": str(MODEL),
            "moc3_path": str(MODEL.parent / json.loads(MODEL.read_text(encoding="utf-8"))["FileReferences"]["Moc"]),
            "moc3_sha256": hashlib.sha256((MODEL.parent / json.loads(MODEL.read_text(encoding="utf-8"))["FileReferences"]["Moc"]).read_bytes()).hexdigest(),
            "render_size": list(SIZE), "parameters": PARAMETERS, "alpha_outer_edge_pixel_count": int(np.count_nonzero(boundary)),
        },
        "target_definition": "25 equally spaced samples of the guide's observed (cyan) source-space contour. Amber inferred hair-occluded sections are excluded.",
        "observed_contour_distance": {"summary": summary, "samples": samples},
        "landmarks": {
            "nose": {"source_px": landmarks["nose_tip"], "render_px": [round(x, 3) for x in source_to_render(landmarks["nose_tip"])], "model_measurement": "not applicable: face_underfill contains no independent nose drawable; shown only as a fixed guide crosshair"},
            "chin": {"source_px": landmarks["chin_tip"], "render_px": [round(x, 3) for x in source_to_render(landmarks["chin_tip"])], "nearest_observed_contour_sample": chin_sample},
        },
        "artifacts": {
            "raw_rgba": "face_underfill_render_2000x3000_rgba.png",
            "review_render": "face_underfill_render_2000x3000_review.png",
            "reference": "source_reference_2000x3000_review.png",
            "overlay": "face_underfill_alpha_target_overlay_2000x3000.png",
            "three_up": "face_underfill_contour_comparison_3up.png",
        },
        "interpretation_limit": "This is a contour-distance diagnostic against the fixed guide. It does not establish a visual-quality pass, and nearest alpha edge is not a substitute for review where the face edge meets the neck or hair.",
    }
    (OUT / "face_underfill_contour_measurement.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["observed_contour_distance"]["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
