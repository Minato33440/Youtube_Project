"""Read-only SDK/raster audit of a face-runtime mesh refinement.

This cannot mutate Cubism projects, textures, source PNGs, or runtime files.
The installed Python wrapper exposes Drawable IDs, but not Cubism Core's vertex,
index, or UV-buffer APIs; the report records that limitation explicitly.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import numpy as np
import pygame
import live2d.v3 as live2d
from OpenGL.GL import GL_RGBA, GL_UNSIGNED_BYTE, glFinish, glReadPixels


OUT = Path(__file__).resolve().parent
SINGLE = OUT.parent
CURRENT = SINGLE / "face_runtime" / "Ren_face_endpoint.model3.json"
BEFORE = SINGLE / "archive" / "before_mesh_refinement_20260926" / "face_runtime" / "Ren_face_endpoint.model3.json"
REPORT = OUT / "mesh_refinement_sdk_audit.json"
SIZE = (2000, 3000)
POSES = {"front_x0_y0": {"ParamAngleX": 0.0, "ParamAngleY": 0.0}, "left_oblique_x-30_y-30": {"ParamAngleX": -30.0, "ParamAngleY": -30.0}}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_paths(path: Path) -> dict:
    model_json = json.loads(path.read_text(encoding="utf-8"))
    moc = path.parent / model_json["FileReferences"]["Moc"]
    return {"model3_json": str(path), "model3_json_sha256": sha256(path), "moc3": str(moc), "moc3_sha256": sha256(moc), "moc3_bytes": moc.stat().st_size}


def composite(raw: np.ndarray, background: tuple[int, int, int]) -> np.ndarray:
    alpha = raw[:, :, 3:4].astype(np.float32) / 255
    return np.clip(np.rint(raw[:, :, :3].astype(np.float32) + np.asarray(background, dtype=np.float32) * (1 - alpha)), 0, 255).astype(np.uint8)


def mask_extent(mask: np.ndarray) -> dict:
    """Fast raster symptom extent; topology still requires a geometry-capable API."""
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return {"pixels": 0, "bbox_render_px": None, "bbox_dimensions": None, "fill_ratio": None}
    width, height = int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)
    return {"pixels": int(len(xs)), "bbox_render_px": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], "bbox_dimensions": [width, height], "fill_ratio": round(float(len(xs)) / (width * height), 4)}


def compare(current: np.ndarray, before: np.ndarray) -> dict:
    alpha_current, alpha_before = current[:, :, 3], before[:, :, 3]
    raw_delta = np.abs(current.astype(np.int16) - before.astype(np.int16))
    white_delta = np.abs(composite(current, (255, 255, 255)).astype(np.int16) - composite(before, (255, 255, 255)).astype(np.int16))
    review_delta = np.abs(composite(current, (235, 232, 226)).astype(np.int16) - composite(before, (235, 232, 226)).astype(np.int16))
    alpha_mask = np.abs(alpha_current.astype(np.int16) - alpha_before.astype(np.int16)) > 8
    visible_mask = white_delta.max(axis=2) > 12
    def summary(delta: np.ndarray, threshold: int) -> dict:
        channel = delta.max(axis=2)
        return {"max_channel_difference": int(delta.max()), "pixels_over_threshold": int(np.count_nonzero(channel > threshold))}
    return {
        "raw_rgba": summary(raw_delta, 8),
        "white_composite": summary(white_delta, 2),
        "review_gray_composite": summary(review_delta, 2),
        "alpha": {"pixels_changed_over_8": int(np.count_nonzero(alpha_mask)), "current_visible_pixels_alpha_ge_16": int(np.count_nonzero(alpha_current >= 16)), "before_visible_pixels_alpha_ge_16": int(np.count_nonzero(alpha_before >= 16))},
        "high_visual_delta_extent_over_12": mask_extent(visible_mask),
    }


def main() -> None:
    for path in (CURRENT, BEFORE):
        if not path.exists():
            raise FileNotFoundError(path)
    pygame.display.init()
    live2d.init()
    models = []
    try:
        pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)
        pygame.display.set_mode(SIZE, pygame.OPENGL | pygame.DOUBLEBUF | pygame.HIDDEN)
        live2d.glInit()

        def load_without_physics(path: Path):
            model = live2d.LAppModel()
            # Keep the original relative file references.  The direct Core
            # update below bypasses physics without rewriting a model fixture.
            model.LoadModelJson(str(path))
            model.Resize(*SIZE)
            model.SetAutoBlinkEnable(False)
            model.SetAutoBreathEnable(False)
            models.append(model)
            return model

        current_model, before_model = load_without_physics(CURRENT), load_without_physics(BEFORE)

        def render(model, values):
            pygame.event.pump()
            for name, value in values.items():
                model.SetParameterValue(name, value)
            model._model.Update(1 / 30)
            live2d.clearBuffer(0, 0, 0, 0)
            model.Draw()
            glFinish()
            raw = np.frombuffer(glReadPixels(0, 0, *SIZE, GL_RGBA, GL_UNSIGNED_BYTE), np.uint8).reshape(SIZE[1], SIZE[0], 4).copy()
            return raw[::-1].copy()

        cases = {}
        for name, values in POSES.items():
            current_raw, before_raw = render(current_model, values), render(before_model, values)
            cases[name] = compare(current_raw, before_raw)

        current_ids, before_ids = current_model.GetDrawableIds(), before_model.GetDrawableIds()
        model_method_names = [name for name in dir(current_model._model) if any(token in name.lower() for token in ("drawable", "vertex", "index", "uv"))]
        report = {
            "status": "completed_with_sdk_geometry_limit",
            "scope": "Read-only comparison of current face_runtime versus archive/before_mesh_refinement_20260926/face_runtime. Original model3 files loaded directly; Core update bypasses physics.",
            "current": model_paths(CURRENT),
            "before": model_paths(BEFORE),
            "sdk_observable_structure": {"current_drawable_count": len(current_ids), "before_drawable_count": len(before_ids), "drawable_ids_equal": current_ids == before_ids, "current_drawable_ids": current_ids, "before_drawable_ids": before_ids},
            "required_mesh_topology_readout": {
                "vertex_count": "unavailable",
                "triangle_index_count": "unavailable",
                "uv_triangle_overlap": "unavailable",
                "negative_triangle_area": "unavailable",
                "x-30_y-30_vertex_inversion_or_self_intersection": "unavailable",
                "reason": "Installed live2d.v3 Python wrapper exposes only drawable IDs and hit testing. It has no public csmGetDrawableVertexCounts, csmGetDrawableVertexPositions, csmGetDrawableVertexUvs, csmGetDrawableIndices, or index-count binding.",
                "actual_underlying_model_methods": model_method_names,
                "interpretation": "The raster checks below can locate a visible symptom but cannot distinguish an under-positioned exterior vertex from duplicate/overlapping automatic triangulation. That distinction needs Cubism's mesh/inspector view or a Core API binding that exposes the drawable buffers.",
            },
            "static_render_comparisons": cases,
            "front_pose_interpretation": "front_x0_y0 compares the new export with the pre-refinement export; it verifies preservation relative to that export, not a direct pixel comparison to the source illustration.",
            "gui_follow_up": [
                "At X=-30/Y=-30, select face_underfill and inspect the narrow residual with mesh display enabled. If two triangles occupy the same region or an old internal edge remains after moving the new border point, delete/reconnect the redundant interior edge rather than moving the exterior outline farther out.",
                "If the mesh has one continuous outer ring and the residual changes position with the boundary vertex, add one inner support point/ring about 10-15 source px inward and reconnect locally; avoid a long thin triangle from the new cheek point to a distant old vertex.",
                "After each local change, re-export face_runtime and re-run this script. Keep front_x0_y0 white/review-gray differences at zero or explain any localized delta before treating endpoint improvement as accepted.",
            ],
        }
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"current_moc3_sha256": report["current"]["moc3_sha256"], "before_moc3_sha256": report["before"]["moc3_sha256"], "front": cases["front_x0_y0"]["white_composite"], "endpoint": cases["left_oblique_x-30_y-30"]["white_composite"]}, ensure_ascii=False))
    finally:
        for model in models:
            model.DestroyRenderer()
        live2d.dispose()
        pygame.quit()


if __name__ == "__main__":
    main()
