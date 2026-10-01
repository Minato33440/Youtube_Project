"""Register the Boss-supplied rough head image to the original tilted source.

This is a read-only analysis helper.  It uses only PIL and NumPy and never
changes source art or any Cubism/runtime file.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[3]
ART = PROJECT / "art" / "Looking_down"
ORIGINAL = ART / "Looking_down (2).png"
ROUGH = ART / "Looking_down (2)-Rough.png"
OUTLINE = ART / "Looking_down (2)-outline.png"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(path: Path) -> dict:
    image = Image.open(path).convert("RGBA")
    rgba = np.asarray(image)
    alpha = rgba[:, :, 3]
    return {
        "path": str(path),
        "sha256": sha256(path),
        "mode_after_load": image.mode,
        "dimensions_px": list(image.size),
        "alpha_min_max": [int(alpha.min()), int(alpha.max())],
        "alpha_bbox_gt_0": list(Image.fromarray(alpha).getbbox() or ()),
        "transparent_pixel_count": int(np.count_nonzero(alpha == 0)),
        "opaque_pixel_count": int(np.count_nonzero(alpha == 255)),
        "top_left_rgba": rgba[0, 0].tolist(),
        "bottom_right_rgba": rgba[-1, -1].tolist(),
    }


def feature(image: Image.Image) -> np.ndarray:
    rgba = np.asarray(image.convert("RGBA"), dtype=np.float32) / 255.0
    rgb = rgba[:, :, :3] * rgba[:, :, 3:4]
    gray = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[:, 1:-1] = gray[:, 2:] - gray[:, :-2]
    gy[1:-1, :] = gray[2:, :] - gray[:-2, :]
    edge = np.sqrt(gx * gx + gy * gy)
    edge += 0.35 * np.sqrt(
        np.square(np.pad(rgba[:, 1:, 3] - rgba[:, :-1, 3], ((0, 0), (0, 1))))
        + np.square(np.pad(rgba[1:, :, 3] - rgba[:-1, :, 3], ((0, 1), (0, 0))))
    )
    edge -= edge.mean()
    norm = float(np.linalg.norm(edge))
    return edge / max(norm, 1e-12)


def fft_shift(fixed: np.ndarray, moving: np.ndarray) -> tuple[int, int, float]:
    shape = tuple(1 << (int(a + b - 2).bit_length()) for a, b in zip(fixed.shape, moving.shape))
    correlation = np.fft.irfftn(
        np.fft.rfftn(fixed, shape) * np.conj(np.fft.rfftn(moving, shape)), shape
    )
    peak = np.unravel_index(int(np.argmax(correlation)), correlation.shape)
    shifts = []
    for value, size in zip(peak, shape):
        shifts.append(int(value if value <= size // 2 else value - size))
    # array order is y,x
    return shifts[1], shifts[0], float(correlation[peak])


def pixel_residual(original: Image.Image, rough: Image.Image, tx: int, ty: int) -> dict:
    moving = np.asarray(rough.convert("RGBA"), dtype=np.int16)
    fixed = np.asarray(original.convert("RGBA"), dtype=np.int16)
    x0, y0 = max(tx, 0), max(ty, 0)
    x1, y1 = min(tx + rough.width, original.width), min(ty + rough.height, original.height)
    rx0, ry0 = x0 - tx, y0 - ty
    a = fixed[y0:y1, x0:x1]
    b = moving[ry0 : ry0 + (y1 - y0), rx0 : rx0 + (x1 - x0)]
    # Ignore stored RGB under zero alpha and compare the visible premultiplied signal.
    ap = np.concatenate([a[:, :, :3] * a[:, :, 3:4] // 255, a[:, :, 3:4]], axis=2)
    bp = np.concatenate([b[:, :, :3] * b[:, :, 3:4] // 255, b[:, :, 3:4]], axis=2)
    delta = np.abs(ap - bp)
    visible = (a[:, :, 3] > 0) | (b[:, :, 3] > 0)
    visible_delta = delta[visible]
    return {
        "translation_px": [tx, ty],
        "overlap_dimensions_px": [x1 - x0, y1 - y0],
        "visible_union_pixel_count": int(np.count_nonzero(visible)),
        "premultiplied_rgba_mean_abs_difference": round(float(visible_delta.mean()), 6),
        "premultiplied_rgba_p95_abs_difference": round(float(np.percentile(visible_delta, 95)), 6),
        "premultiplied_rgba_max_abs_difference": int(visible_delta.max()),
        "exact_visible_rgba_pixel_fraction": round(float(np.mean(np.max(visible_delta.reshape(-1, 4), axis=1) == 0)), 6),
    }


def main() -> None:
    original_image = Image.open(ORIGINAL).convert("RGBA")
    rough_image = Image.open(ROUGH).convert("RGBA")
    fixed = feature(original_image)
    candidates = []
    # Coarse-to-fine uniform-scale search. No rotation is considered or applied.
    scales = np.arange(0.96, 1.0401, 0.002)
    for scale in scales:
        size = (round(rough_image.width * scale), round(rough_image.height * scale))
        moving = feature(rough_image.resize(size, Image.Resampling.LANCZOS))
        tx, ty, score = fft_shift(fixed, moving)
        candidates.append({"scale": round(float(scale), 6), "translation_px": [tx, ty], "fft_edge_score": score})
    candidates.sort(key=lambda item: item["fft_edge_score"], reverse=True)
    best_coarse = candidates[0]
    center = best_coarse["scale"]
    fine = []
    for scale in np.arange(center - 0.003, center + 0.00301, 0.0001):
        size = (round(rough_image.width * scale), round(rough_image.height * scale))
        moving = feature(rough_image.resize(size, Image.Resampling.LANCZOS))
        tx, ty, score = fft_shift(fixed, moving)
        fine.append({"scale": round(float(scale), 7), "translation_px": [tx, ty], "fft_edge_score": score, "resized_dimensions_px": list(size)})
    fine.sort(key=lambda item: item["fft_edge_score"], reverse=True)
    local_residuals = [
        pixel_residual(original_image, rough_image, tx, ty)
        for ty in range(-1, 4)
        for tx in range(54, 61)
    ]
    local_residuals.sort(key=lambda item: item["premultiplied_rgba_mean_abs_difference"])
    report = {
        "purpose": "Read-only source registration from Rough coordinates to original Looking_down (2) coordinates.",
        "inputs": {"original": describe(ORIGINAL), "rough": describe(ROUGH), "outline": describe(OUTLINE)},
        "model": "original_xy = rough_xy * uniform_scale + translation_xy; no rotation or shear",
        "best_fft_edge_registration": fine[0],
        "selected_exact_crop_registration": {
            "scale": 1.0,
            "translation_px": [57, 1],
            "model": "original_xy = rough_xy + (57, 1)",
            "reason": "The FFT peak is stable at this integer translation throughout the no-resize scale plateau, and it is the best local visible-pixel residual. The supplied Rough and outline share the same top-left coordinate system; the outline's last 15 rows are transparent padding.",
            "pixel_residual": pixel_residual(original_image, rough_image, 57, 1),
        },
        "local_integer_translation_residuals_top_10": local_residuals[:10],
        "coarse_top_10": candidates[:10],
        "fine_top_20": fine[:20],
        "note": "FFT edge correlation is an estimator. Final guide generation should record a pixel-domain residual and selected transform explicitly.",
    }
    path = OUT / "source_registration_exploration.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["best_fft_edge_registration"], ensure_ascii=False))
    print(path)


if __name__ == "__main__":
    main()
