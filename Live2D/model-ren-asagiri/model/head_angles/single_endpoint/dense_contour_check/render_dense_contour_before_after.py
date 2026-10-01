"""Direct-SDK before/after audit of face-underfill against the dense visible contour.

Loads the supplied model3 JSON files directly.  No temporary model fixture,
physics update, model/image warp, GUI operation, or asset modification occurs.
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
BEFORE = SINGLE / "archive" / "before_mesh_refinement_20260926" / "face_runtime" / "Ren_face_endpoint.model3.json"
DENSE = OUT / "dense_visible_contour_target.json"
SOURCE = Path(r"C:\Python\REX_AI\Youtube_Project\Live2D\model-ren-asagiri\art\Looking_down\Looking_down (2).png")
SIZE = (2000, 3000)
RENDER_SCALE = 0.5
BACKGROUND = (235, 232, 226)
PARAMETERS = {"ParamAngleX": -30.0, "ParamAngleY": -30.0}
REPORT = OUT / "dense_contour_before_after_measurement.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def moc_path(model_path: Path) -> Path:
    return model_path.parent / json.loads(model_path.read_text(encoding="utf-8"))["FileReferences"]["Moc"]


def unpremultiply(raw: np.ndarray) -> np.ndarray:
    result = raw.copy()
    alpha = raw[:, :, 3:4].astype(np.float32)
    result[:, :, :3] = np.clip(np.rint(raw[:, :, :3].astype(np.float32) * 255 / np.maximum(alpha, 1)), 0, 255)
    return result


def composite(raw: np.ndarray, background=BACKGROUND) -> Image.Image:
    alpha = raw[:, :, 3:4].astype(np.float32) / 255
    rgb = np.clip(np.rint(raw[:, :, :3].astype(np.float32) + np.asarray(background, dtype=np.float32) * (1 - alpha)), 0, 255).astype(np.uint8)
    return Image.fromarray(rgb, "RGB")


def alpha_edge(raw: np.ndarray) -> np.ndarray:
    mask = raw[:, :, 3] >= 16
    padded = np.pad(mask, 1, constant_values=False)
    all_neighbours = padded[:-2, 1:-1] & padded[2:, 1:-1] & padded[1:-1, :-2] & padded[1:-1, 2:]
    return mask & ~all_neighbours


def stats(values: list[float]) -> dict:
    array = np.asarray(values, dtype=float)
    return {"count": int(len(array)), "min": round(float(array.min()), 3), "p50": round(float(np.percentile(array, 50)), 3), "p90": round(float(np.percentile(array, 90)), 3), "max": round(float(array.max()), 3), "mean": round(float(array.mean()), 3)}


def measure(edge: np.ndarray, targets: list[list[float]], transform) -> tuple[list[dict], dict]:
    ys, xs = np.nonzero(edge)
    if not len(xs):
        raise RuntimeError("No alpha outer edge in SDK face-only render.")
    edge_xy = np.column_stack([xs, ys]).astype(float)
    rows = []
    for index, source_px in enumerate(targets):
        target = np.asarray(transform(source_px), dtype=float)
        distances2 = np.sum((edge_xy - target) ** 2, axis=1)
        closest_index = int(np.argmin(distances2))
        distance = float(np.sqrt(distances2[closest_index]))
        nearest = edge_xy[closest_index]
        rows.append({"sample": index + 1, "source_px": source_px, "target_render_px": [round(float(target[0]), 3), round(float(target[1]), 3)], "nearest_alpha_edge_render_px": [int(nearest[0]), int(nearest[1])], "distance_render_px": round(distance, 3), "distance_full_canvas_px": round(distance / RENDER_SCALE, 3)})
    return rows, {"render_px": stats([x["distance_render_px"] for x in rows]), "full_canvas_px": stats([x["distance_full_canvas_px"] for x in rows])}


def render_direct(model_path: Path, parameters: dict[str, float]) -> np.ndarray:
    model = live2d.LAppModel()
    model.LoadModelJson(str(model_path))  # Original model3 JSON: no temporary rewritten references.
    model.Resize(*SIZE)
    model.SetAutoBlinkEnable(False)
    model.SetAutoBreathEnable(False)
    try:
        for param, value in parameters.items():
            model.SetParameterValue(param, value)
        # Direct Core update applies parameter deformation.  It does not call the
        # LApp physics update path, matching the working face-underfill checker.
        model._model.Update(1 / 30)
        live2d.clearBuffer(0, 0, 0, 0)
        model.Draw()
        glFinish()
        return np.frombuffer(glReadPixels(0, 0, *SIZE, GL_RGBA, GL_UNSIGNED_BYTE), np.uint8).reshape(SIZE[1], SIZE[0], 4).copy()[::-1].copy()
    finally:
        model.DestroyRenderer()


def source_reference(transform) -> Image.Image:
    source = Image.open(SOURCE).convert("RGBA")
    # Source uses the fixed uniform scale/translation; model renders are not resampled.
    dense = json.loads(DENSE.read_text(encoding="utf-8"))
    scale = dense["fixed_reference_transform"]["full_canvas_scale"] * RENDER_SCALE
    offset = np.asarray(dense["fixed_reference_transform"]["full_canvas_offset"], dtype=float) * RENDER_SCALE
    scaled = source.resize((round(source.width * scale), round(source.height * scale)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", SIZE, BACKGROUND + (255,))
    canvas.alpha_composite(scaled, (round(offset[0]), round(offset[1])))
    return canvas.convert("RGB")


def image_delta_summary(before: np.ndarray, after: np.ndarray) -> dict:
    def summarize(delta: np.ndarray, threshold: int) -> dict:
        channel = delta.max(axis=2)
        return {"max_channel_difference": int(delta.max()), "pixels_over_threshold": int(np.count_nonzero(channel > threshold))}
    return {
        "raw_rgba": summarize(np.abs(after.astype(np.int16) - before.astype(np.int16)), 8),
        "white_composite": summarize(np.abs(np.asarray(composite(after, (255, 255, 255))).astype(np.int16) - np.asarray(composite(before, (255, 255, 255))).astype(np.int16)), 2),
        "review_gray_composite": summarize(np.abs(np.asarray(composite(after)).astype(np.int16) - np.asarray(composite(before)).astype(np.int16)), 2),
    }


def labelled(image: Image.Image, label: str, crop: tuple[int, int, int, int], font: ImageFont.FreeTypeFont) -> Image.Image:
    piece = image.crop(crop)
    result = Image.new("RGB", (piece.width, piece.height + 42), (248, 247, 243))
    result.paste(piece, (0, 42))
    ImageDraw.Draw(result).text((10, 10), label, fill=(28, 33, 42), font=font)
    return result


def main() -> None:
    for path in (CURRENT, BEFORE, DENSE, SOURCE):
        if not path.exists():
            raise FileNotFoundError(path)
    dense = json.loads(DENSE.read_text(encoding="utf-8"))
    if sha256(SOURCE) != dense["source"]["sha256"]:
        raise RuntimeError("Fixed source hash differs from dense target; refusing comparison.")
    scale = dense["fixed_reference_transform"]["full_canvas_scale"]
    offset = np.asarray(dense["fixed_reference_transform"]["full_canvas_offset"], dtype=float)
    transform = lambda point: tuple((offset + np.asarray(point, dtype=float) * scale) * RENDER_SCALE)
    targets = dense["evaluation_samples_source_px"]  # 2px dense visible contour; inferred regions excluded by construction.

    pygame.display.init()
    live2d.init()
    try:
        pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)
        pygame.display.set_mode(SIZE, pygame.OPENGL | pygame.DOUBLEBUF | pygame.HIDDEN)
        live2d.glInit()
        before_raw = render_direct(BEFORE, PARAMETERS)
        current_raw = render_direct(CURRENT, PARAMETERS)
        before_front_raw = render_direct(BEFORE, {"ParamAngleX": 0.0, "ParamAngleY": 0.0})
        current_front_raw = render_direct(CURRENT, {"ParamAngleX": 0.0, "ParamAngleY": 0.0})
    finally:
        live2d.dispose()
        pygame.quit()

    before_review, current_review = composite(before_raw), composite(current_raw)
    source_review = source_reference(transform)
    before_review.save(OUT / "dense_before_bareface_2000x3000.png")
    current_review.save(OUT / "dense_after_bareface_2000x3000.png")
    source_review.save(OUT / "dense_source_fixed_2000x3000.png")
    Image.fromarray(unpremultiply(before_raw), "RGBA").save(OUT / "dense_before_bareface_2000x3000_rgba.png")
    Image.fromarray(unpremultiply(current_raw), "RGBA").save(OUT / "dense_after_bareface_2000x3000_rgba.png")

    before_edge, current_edge = alpha_edge(before_raw), alpha_edge(current_raw)
    before_rows, before_summary = measure(before_edge, targets, transform)
    current_rows, current_summary = measure(current_edge, targets, transform)
    # Five contiguous equal-length bins make local bowing visible even when the
    # all-path median is small.  They are practical review bins, not anatomy claims.
    bin_names = ["right_cheek", "right_jaw", "chin", "left_jaw", "left_cheek"]
    bins = {}
    for index, name in enumerate(bin_names):
        lo = round(index * len(targets) / 5)
        hi = round((index + 1) * len(targets) / 5)
        bins[name] = {"sample_range_1_based": [lo + 1, hi], "before_full_canvas_px": stats([x["distance_full_canvas_px"] for x in before_rows[lo:hi]]), "after_full_canvas_px": stats([x["distance_full_canvas_px"] for x in current_rows[lo:hi]])}

    overlay = current_review.copy()
    overlay_draw = ImageDraw.Draw(overlay)
    before_y, before_x = np.nonzero(before_edge)
    current_y, current_x = np.nonzero(current_edge)
    overlay_draw.point(list(zip(before_x.tolist(), before_y.tolist())), fill=(237, 69, 68))
    overlay_draw.point(list(zip(current_x.tolist(), current_y.tolist())), fill=(72, 238, 126))
    contour = [transform(point) for point in targets]
    overlay_draw.line(contour, fill=(0, 226, 255), width=2, joint="curve")
    for x, y in contour[::5]:
        overlay_draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(0, 226, 255), outline=(20, 20, 20))
    overlay.save(OUT / "dense_before_after_thin_contour_overlay_2000x3000.png")
    crop = (720, 300, 1250, 760)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
    panels = [
        labelled(source_review, "Source art — fixed placement", crop, font),
        labelled(before_review, "Before bareface — SDK render", crop, font),
        labelled(current_review, "After bareface — SDK render", crop, font),
        labelled(overlay, "Cyan target / red before / green after", crop, font),
    ]
    sheet = Image.new("RGB", (panels[0].width * 4, panels[0].height), (248, 247, 243))
    for index, panel in enumerate(panels):
        sheet.paste(panel, (index * panel.width, 0))
    sheet.save(OUT / "dense_contour_before_after_4up.png")

    report = {
        "status": "measurement_complete",
        "scope": "Face-runtime-only direct-SDK render at ParamAngleX=-30, ParamAngleY=-30. This excludes inferred hair-covered contour segments, full runtime, hair, eyes, mouth, and visual acceptance.",
        "direct_model_loading": {"before_model3_json": str(BEFORE), "after_model3_json": str(CURRENT), "temporary_fixture": False, "physics_update_called": False},
        "fixed_source": {"path": str(SOURCE), "sha256": sha256(SOURCE), "dense_target": str(DENSE), "full_canvas_scale": scale, "full_canvas_offset": offset.tolist(), "render_scale": RENDER_SCALE},
        "models": {"before_moc3_sha256": sha256(moc_path(BEFORE)), "after_moc3_sha256": sha256(moc_path(CURRENT)), "before_moc3_bytes": moc_path(BEFORE).stat().st_size, "after_moc3_bytes": moc_path(CURRENT).stat().st_size},
        "overall_distance": {"before": before_summary, "after": current_summary},
        "per_arc_distance_full_canvas_px": bins,
        "front_x0_y0_before_after": {
            "meaning": "Current versus pre-refinement face-runtime render at the front pose. This is preservation relative to the archived face export, not a direct source-art pixel match.",
            "display_delta": image_delta_summary(before_front_raw, current_front_raw),
        },
        "sample_count": len(targets),
        "artifacts": {"four_up": "dense_contour_before_after_4up.png", "thin_overlay": "dense_before_after_thin_contour_overlay_2000x3000.png", "source": "dense_source_fixed_2000x3000.png", "before": "dense_before_bareface_2000x3000.png", "after": "dense_after_bareface_2000x3000.png"},
        "interpretation_limit": "Nearest alpha-edge distances describe placement against the visible source path. They cannot prove triangle topology, prevent overlaps hidden by draw order, or establish visual acceptance; inspect the 4-up overlay and Cubism mesh view.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"before": before_summary["full_canvas_px"], "after": current_summary["full_canvas_px"], "per_arc": bins}, ensure_ascii=False))


if __name__ == "__main__":
    main()
