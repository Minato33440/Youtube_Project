"""Build a non-destructive, unrotated overlay guide for the oblique-nod mesh pass."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SOURCE = ROOT / "art" / "Looking_down" / "Looking_down (2).png"
CASE = OUT.parent / "preview" / "case_01.png"
CANVAS = (4000, 6000)
MODEL_CROP = (390, 0, 420, 570)
MODEL_SCALE = 0.3
SOURCE_PUPILS = np.array([[295.9, 527.3], [487.3, 507.3]], dtype=float)
CURRENT_PUPILS = np.array([[145.8, 248.8], [220.3, 248.4]], dtype=float)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def landmark(x: float, y: float, display_scale: float, display_offset: np.ndarray) -> dict:
    display = np.array([x, y]) * display_scale + display_offset
    full = (display + np.array(MODEL_CROP[:2])) / MODEL_SCALE
    return {
        "source_px": [round(x, 2), round(y, 2)],
        "aligned_display_px": [round(float(display[0]), 2), round(float(display[1]), 2)],
        "full_canvas_px": [round(float(full[0]), 2), round(float(full[1]), 2)],
    }


def main() -> None:
    source = Image.open(SOURCE).convert("RGBA")
    source_distance = float(np.linalg.norm(SOURCE_PUPILS[1] - SOURCE_PUPILS[0]))
    current_distance = float(np.linalg.norm(CURRENT_PUPILS[1] - CURRENT_PUPILS[0]))
    display_scale = current_distance / source_distance
    display_offset = CURRENT_PUPILS.mean(axis=0) - display_scale * SOURCE_PUPILS.mean(axis=0)
    full_scale = display_scale / MODEL_SCALE
    full_offset = (display_offset + np.array(MODEL_CROP[:2])) / MODEL_SCALE

    scaled_size = tuple(round(v * full_scale) for v in source.size)
    scaled = source.resize(scaled_size, Image.Resampling.LANCZOS)
    left = tuple(round(v) for v in full_offset)
    right = (CANVAS[0] - left[0] - scaled.width, left[1])
    scaled.save(OUT / "reference_left_scaled.png")
    scaled.transpose(Image.Transpose.FLIP_LEFT_RIGHT).save(OUT / "reference_right_mirrored_geometry_guide_scaled.png")

    for name, image, position in (
        ("reference_left_fullcanvas.png", scaled, left),
        ("reference_right_mirrored_geometry_guide_fullcanvas.png", scaled.transpose(Image.Transpose.FLIP_LEFT_RIGHT), right),
    ):
        full = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
        full.alpha_composite(image, position)
        full.save(OUT / name)

    display = source.resize(tuple(round(v * display_scale) for v in source.size), Image.Resampling.LANCZOS)
    reference_crop = Image.new("RGBA", (420, 570), (0, 0, 0, 0))
    reference_crop.alpha_composite(display, tuple(round(v) for v in display_offset))
    reference_crop.save(OUT / "reference_left_case_01_crop.png")
    current = Image.open(CASE).convert("RGBA")
    comparison = Image.new("RGBA", (840, 570), (239, 236, 231, 255))
    comparison.alpha_composite(current, (0, 0))
    comparison.alpha_composite(reference_crop, (420, 0))
    comparison.save(OUT / "case_01_reference_crop_comparison.png")

    # Re-measured directly on the unrotated source illustration. These are guide
    # points for mesh placement; only the two pupil centres define the transform.
    raw_landmarks = {
        "pupil_left": (295.9, 527.3),
        "pupil_right": (487.3, 507.3),
        "nose_tip": (385.0, 589.0),
        "mouth_center": (413.0, 657.0),
        "chin_tip": (424.0, 728.0),
        "ear_left_visible": (144.0, 500.0),
        "ear_right_visible": (646.0, 507.0),
        "cheek_left_silhouette": (251.0, 618.0),
        "cheek_right_silhouette": (574.0, 613.0),
    }
    annotated = source.copy()
    draw = ImageDraw.Draw(annotated)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    for number, (name, (x, y)) in enumerate(raw_landmarks.items(), start=1):
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#ff2d2d", outline="white", width=2)
        draw.text((x + 8, y - 23), f"{number} {name}", font=font, fill="white", stroke_width=2, stroke_fill="#111111")
    annotated.save(OUT / "source_landmarks_numbered.png")
    manifest = {
        "purpose": "Non-destructive PSD reference overlay for oblique-nod mesh adjustment. Hide before export/import as non-export reference.",
        "source": {
            "path": str(SOURCE),
            "sha256": sha256(SOURCE),
            "dimensions": list(source.size),
            "operation": "uniform scale and translation only; no rotation, shear, warp, repaint, or source modification",
        },
        "canvas": {"dimensions": list(CANVAS), "model_crop": {"left": 390, "top": 0, "width": 420, "height": 570}, "model_scale": MODEL_SCALE},
        "alignment": {
            "method": "match pupil distance and midpoint while retaining the original source roll/slope",
            "source_pupil_centres": SOURCE_PUPILS.tolist(),
            "current_case_01_pupil_centres": CURRENT_PUPILS.tolist(),
            "source_pupil_distance": source_distance,
            "current_pupil_distance": current_distance,
            "display_scale": display_scale,
            "display_offset": display_offset.tolist(),
            "full_canvas_scale": full_scale,
            "full_canvas_offset": full_offset.tolist(),
            "raster_layer_position": {"reference_left": list(left), "reference_right_mirrored_about_x_2000": list(right)},
            "raster_layer_dimensions": list(scaled.size),
            "slope_note": "The source pupils remain approximately 7.74 display px lower on the left after alignment; this is intentional and preserves the original tilted reference.",
        },
        "layers": [
            {"name": "reference_left", "path": "reference_left_scaled.png", "left": left[0], "top": left[1], "opacity": 0.45, "role": "unrotated original-colored reference; hide/non-export"},
            {"name": "reference_right__MIRRORED_GEOMETRY_GUIDE_NOT_FINAL_ART", "path": "reference_right_mirrored_geometry_guide_scaled.png", "left": right[0], "top": right[1], "opacity": 0.45, "role": "mirror across full-canvas x=2000 for geometry only; not final colored artwork; hide/non-export"},
        ],
        "landmarks": {name: landmark(x, y, display_scale, display_offset) for name, (x, y) in raw_landmarks.items()},
        "limitations": [
            "Landmarks other than the supplied pupil centres are visual approximations for mesh guidance.",
            "The model preview and the supplied illustration differ in proportions and art construction; this guide is not a pixel-match target.",
            "The mirrored layer is a geometry aid only and must not be used as final colored art.",
        ],
    }
    (OUT / "reference_overlay_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
