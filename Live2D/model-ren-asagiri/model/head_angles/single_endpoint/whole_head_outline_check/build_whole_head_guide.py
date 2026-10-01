"""Build a registered whole-head guide from the Boss-supplied outline.

Only derived guide/reference assets under this directory are written.  The
source images and every Cubism/runtime artifact are read-only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[3]
ART = PROJECT / "art" / "Looking_down"
ORIGINAL = ART / "Looking_down (2).png"
ROUGH = ART / "Looking_down (2)-Rough.png"
OUTLINE = ART / "Looking_down (2)-outline.png"
CANVAS = (4000, 6000)
ORIGINAL_SCALE = 1.2904500571168767
ORIGINAL_OFFSET = (1404.826424299698, 161.11685212010656)
ROUGH_TO_ORIGINAL_SCALE = 1.0
ROUGH_TO_ORIGINAL_OFFSET = (57.0, 1.0)
COMBINED_OFFSET = (
    ORIGINAL_OFFSET[0] + ROUGH_TO_ORIGINAL_OFFSET[0] * ORIGINAL_SCALE,
    ORIGINAL_OFFSET[1] + ROUGH_TO_ORIGINAL_OFFSET[1] * ORIGINAL_SCALE,
)

# These source controls follow the dark line on the supplied outline.  The
# face-underfill path excludes the ears.  Coordinates are in Rough/outline px.
FACE_LEFT_TO_CHIN = [
    (149, 500), (155, 510), (161, 520), (166, 530), (172, 540), (177, 550),
    (183, 560), (188, 570), (194, 580), (199, 590), (205, 600), (211, 610),
    (217, 620), (223, 630), (231, 640), (240, 650), (251, 660), (267, 670),
    (282, 680), (297, 690), (313, 700), (329, 710), (348, 720), (365, 728),
]
FACE_CHIN_TO_RIGHT = [
    (365, 728), (386, 720), (398, 710), (411, 700), (424, 690), (436, 680),
    (447, 670), (458, 660), (469, 650), (478, 640), (487, 630), (493, 620),
    (499, 610), (505, 600), (509, 590), (513, 580), (517, 570), (521, 560),
    (524, 550), (527, 540), (532, 530), (533, 520), (537, 510), (540, 500),
    (542, 490), (545, 480), (547, 470), (550, 460), (553, 450), (554, 440),
]
FACE_VISIBLE = FACE_LEFT_TO_CHIN + FACE_CHIN_TO_RIGHT[1:]

# The upper path is supplied by Boss as the intended hidden head shape.  It is
# still classified as inferred for face-underfill validation because hair
# hides the scalp in the finished model and there is no visible skin edge.
SCALP_INFERRED_RIGHT_TO_LEFT = [
    (554, 440), (556, 420), (558, 400), (558, 380), (556, 360), (553, 340),
    (549, 325), (545, 315), (541, 305), (537, 295), (531, 285), (524, 275),
    (517, 265), (508, 255), (498, 245), (487, 235), (475, 225), (459, 215),
    (439, 207), (420, 201), (403, 197), (382, 194), (360, 193), (338, 193),
    (317, 194), (297, 198), (280, 202), (264, 207), (248, 213), (233, 220),
    (219, 228), (207, 237), (194, 247), (181, 259), (170, 272), (159, 286),
    (150, 301), (142, 317), (135, 333), (130, 349), (126, 365), (122, 382),
    (120, 400), (122, 420), (127, 440), (130, 450), (136, 470), (142, 490),
    (149, 500),
]

EAR_LEFT_OUTER = [
    (144, 490), (140, 500), (137, 510), (134, 520), (134, 530), (139, 540),
    (144, 550), (149, 560), (158, 570), (169, 580), (181, 590), (194, 600),
    (205, 605),
]
EAR_RIGHT_OUTER = [
    (558, 440), (570, 450), (579, 460), (586, 470), (592, 480), (591, 490),
    (586, 500), (581, 510), (574, 520), (563, 530), (555, 540), (547, 550),
    (533, 560), (521, 565),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_to_original(point: tuple[float, float]) -> tuple[float, float]:
    return (
        point[0] * ROUGH_TO_ORIGINAL_SCALE + ROUGH_TO_ORIGINAL_OFFSET[0],
        point[1] * ROUGH_TO_ORIGINAL_SCALE + ROUGH_TO_ORIGINAL_OFFSET[1],
    )


def source_to_canvas(point: tuple[float, float]) -> tuple[float, float]:
    original = source_to_original(point)
    return (
        ORIGINAL_OFFSET[0] + original[0] * ORIGINAL_SCALE,
        ORIGINAL_OFFSET[1] + original[1] * ORIGINAL_SCALE,
    )


def resample(points: list[tuple[float, float]], spacing: float) -> list[tuple[float, float]]:
    xy = np.asarray(points, dtype=float)
    lengths = np.linalg.norm(xy[1:] - xy[:-1], axis=1)
    cumulative = np.r_[0.0, np.cumsum(lengths)]
    locations = list(np.arange(0, cumulative[-1], spacing)) + [cumulative[-1]]
    result = []
    for location in locations:
        segment = min(np.searchsorted(cumulative, location, side="right") - 1, len(lengths) - 1)
        amount = (location - cumulative[segment]) / max(lengths[segment], 1e-9)
        point = xy[segment] * (1 - amount) + xy[segment + 1] * amount
        result.append((round(float(point[0]), 3), round(float(point[1]), 3)))
    return result


def mapped_records(points: list[tuple[float, float]]) -> list[dict]:
    rows = []
    for x, y in points:
        original = source_to_original((x, y))
        canvas = source_to_canvas((x, y))
        rows.append({
            "outline_rough_px": [round(x, 3), round(y, 3)],
            "original_px": [round(original[0], 3), round(original[1], 3)],
            "canvas_px": [round(canvas[0], 3), round(canvas[1], 3)],
        })
    return rows


def registered_raster(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    return image.resize(
        (round(image.width * ORIGINAL_SCALE), round(image.height * ORIGINAL_SCALE)),
        Image.Resampling.LANCZOS,
    )


def line_layer(
    name: str,
    paths: list[list[tuple[float, float]]],
    color: tuple[int, int, int, int],
    width: int,
    dashed: bool = False,
    points: bool = False,
) -> dict:
    mapped = [[source_to_canvas(point) for point in path] for path in paths]
    all_points = [point for path in mapped for point in path]
    pad = 24
    left = int(np.floor(min(point[0] for point in all_points) - pad))
    top = int(np.floor(min(point[1] for point in all_points) - pad))
    right = int(np.ceil(max(point[0] for point in all_points) + pad))
    bottom = int(np.ceil(max(point[1] for point in all_points) + pad))
    image = Image.new("RGBA", (right - left + 1, bottom - top + 1), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for path in mapped:
        local = [(point[0] - left, point[1] - top) for point in path]
        if dashed:
            for a, b in zip(local, local[1:]):
                distance = max(float(np.hypot(b[0] - a[0], b[1] - a[1])), 1.0)
                for start in np.arange(0, distance, 22.0):
                    end = min(start + 13.0, distance)
                    p0 = (a[0] + (b[0] - a[0]) * start / distance, a[1] + (b[1] - a[1]) * start / distance)
                    p1 = (a[0] + (b[0] - a[0]) * end / distance, a[1] + (b[1] - a[1]) * end / distance)
                    draw.line((p0, p1), fill=color, width=width)
        else:
            draw.line(local, fill=color, width=width, joint="curve")
        if points:
            radius = max(2, width)
            for x, y in local:
                draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color, outline=(20, 25, 32, 255), width=1)
    file_name = f"{name}.png"
    image.save(OUT / file_name)
    return {"name": name, "path": file_name, "left": left, "top": top, "dimensions_px": list(image.size)}


def build_source_audit() -> None:
    outline = Image.open(OUTLINE).convert("RGBA")
    scale = 2
    audit = outline.resize((outline.width * scale, outline.height * scale), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(audit)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)

    def draw_path(points, color, width=4, dashed=False):
        mapped = [(x * scale, y * scale) for x, y in points]
        if dashed:
            for a, b in zip(mapped, mapped[1:]):
                distance = max(float(np.hypot(b[0] - a[0], b[1] - a[1])), 1.0)
                for start in np.arange(0, distance, 18.0):
                    end = min(start + 10.0, distance)
                    draw.line((a[0] + (b[0] - a[0]) * start / distance, a[1] + (b[1] - a[1]) * start / distance,
                               a[0] + (b[0] - a[0]) * end / distance, a[1] + (b[1] - a[1]) * end / distance), fill=color, width=width)
        else:
            draw.line(mapped, fill=color, width=width, joint="curve")

    draw_path(FACE_VISIBLE, (0, 220, 255, 255), 5)
    draw_path(SCALP_INFERRED_RIGHT_TO_LEFT, (255, 177, 45, 255), 5, True)
    draw_path(EAR_LEFT_OUTER, (255, 64, 194, 255), 4)
    draw_path(EAR_RIGHT_OUTER, (255, 64, 194, 255), 4)
    footer = Image.new("RGB", (audit.width, 84), (28, 33, 42))
    footer_draw = ImageDraw.Draw(footer)
    footer_draw.text((12, 8), "cyan: observed face-underfill edge   amber dashed: inferred hair-hidden scalp", font=font, fill=(244, 246, 250))
    footer_draw.text((12, 38), "magenta: ear outer contour (separate; excluded from face target)", font=font, fill=(244, 246, 250))
    result = Image.new("RGB", (audit.width, audit.height + footer.height), (238, 238, 235))
    neutral = Image.new("RGBA", audit.size, (238, 238, 235, 255))
    neutral.alpha_composite(audit)
    result.paste(neutral.convert("RGB"), (0, 0))
    result.paste(footer, (0, audit.height))
    result.save(OUT / "whole_head_outline_source_audit.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    original = Image.open(ORIGINAL).convert("RGBA")
    rough = Image.open(ROUGH).convert("RGBA")
    outline = Image.open(OUTLINE).convert("RGBA")
    if rough.size != (672, 769) or outline.size != (672, 784) or original.size != (958, 1004):
        raise RuntimeError("Input dimensions changed; stop before generating a misregistered guide.")
    original_crop = np.asarray(original.crop((57, 1, 729, 770)), dtype=np.uint8)
    rough_array = np.asarray(rough, dtype=np.uint8)
    visible = (original_crop[:, :, 3] > 0) | (rough_array[:, :, 3] > 0)
    if not np.array_equal(original_crop[visible], rough_array[visible]):
        raise RuntimeError("Rough is no longer an exact visible-pixel crop at original offset (57,1).")
    if np.any(np.asarray(outline)[769:, :, 3]):
        raise RuntimeError("Expected the outline's final 15 rows to be transparent padding.")

    rough_scaled = registered_raster(ROUGH)
    outline_scaled = registered_raster(OUTLINE)
    rough_scaled.save(OUT / "reference_rough_registered.png")
    outline_scaled.save(OUT / "reference_outline_registered.png")
    face_layer = line_layer("guide_face_observed_cyan", [FACE_VISIBLE], (0, 225, 255, 255), 5, points=True)
    scalp_layer = line_layer("guide_scalp_inferred_amber_dashed", [SCALP_INFERRED_RIGHT_TO_LEFT], (255, 178, 46, 255), 5, dashed=True, points=True)
    ear_layer = line_layer("guide_ear_outer_magenta", [EAR_LEFT_OUTER, EAR_RIGHT_OUTER], (255, 64, 194, 255), 4, points=True)

    overlay = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    position = (round(COMBINED_OFFSET[0]), round(COMBINED_OFFSET[1]))
    faded_outline = outline_scaled.copy()
    alpha = np.asarray(faded_outline.getchannel("A"), dtype=np.uint16)
    faded_outline.putalpha(Image.fromarray((alpha * 90 // 255).astype(np.uint8)))
    overlay.alpha_composite(faded_outline, position)
    for layer in (scalp_layer, face_layer, ear_layer):
        overlay.alpha_composite(Image.open(OUT / layer["path"]).convert("RGBA"), (layer["left"], layer["top"]))
    overlay.save(OUT / "whole_head_outline_guide_4000x6000.png")
    build_source_audit()

    face_samples = resample(FACE_VISIBLE, 2.0)
    scalp_samples = resample(SCALP_INFERRED_RIGHT_TO_LEFT, 3.0)
    payload = {
        "purpose": "Whole-head face-underfill target for the single X=-30/Y=-30 endpoint. Ear outlines are kept separate and excluded from face-underfill distances.",
        "inputs": {
            "original": {"path": str(ORIGINAL), "sha256": sha256(ORIGINAL), "dimensions_px": list(original.size)},
            "rough": {"path": str(ROUGH), "sha256": sha256(ROUGH), "dimensions_px": list(rough.size)},
            "outline": {"path": str(OUTLINE), "sha256": sha256(OUTLINE), "dimensions_px": list(outline.size)},
        },
        "registration": {
            "rough_outline_to_original": {"scale": 1.0, "translation_px": [57, 1], "visible_rgba_residual": "exact; 338253/338253 visible-union pixels equal"},
            "original_to_canvas": {"scale": ORIGINAL_SCALE, "translation_px": list(ORIGINAL_OFFSET), "operation": "uniform scale and translation only; retain original tilt"},
            "rough_outline_to_canvas": {"scale": ORIGINAL_SCALE, "translation_px": list(COMBINED_OFFSET), "raster_layer_position_rounded_px": list(position)},
        },
        "classification": {
            "face_visible_observed": "Cyan path follows the supplied dark face outline from the left ear-root area through the chin to the right side. It is the precision face-underfill target.",
            "scalp_hair_hidden_inferred": "Amber dashed path follows the Boss-supplied intended upper head shape, but remains an approximation for face-underfill because finished hair hides it.",
            "ear_outer_observed_separate": "Magenta paths trace ear outer silhouettes for orientation only. They are not part of the face-underfill target and are excluded from distance metrics.",
        },
        "controls": {
            "face_visible": mapped_records(FACE_VISIBLE),
            "scalp_inferred_right_to_left": mapped_records(SCALP_INFERRED_RIGHT_TO_LEFT),
            "ear_left_outer": mapped_records(EAR_LEFT_OUTER),
            "ear_right_outer": mapped_records(EAR_RIGHT_OUTER),
        },
        "evaluation_samples": {
            "face_visible_2px_spacing": mapped_records(face_samples),
            "scalp_inferred_3px_spacing": mapped_records(scalp_samples),
        },
        "key_coordinates": {
            key: mapped_records([point])[0]
            for key, point in {
                "scalp_top": (338, 193),
                "face_left_start": (149, 500),
                "chin_tip": (365, 728),
                "face_right_start": (540, 500),
                "left_ear_outermost": (134, 520),
                "right_ear_outermost": (593, 485),
            }.items()
        },
        "psd_layer_assets": {
            "rough": {"path": "reference_rough_registered.png", "left": position[0], "top": position[1], "dimensions_px": list(rough_scaled.size)},
            "outline": {"path": "reference_outline_registered.png", "left": position[0], "top": position[1], "dimensions_px": list(outline_scaled.size)},
            "face_guide": face_layer,
            "scalp_guide": scalp_layer,
            "ear_guide": ear_layer,
        },
        "artifacts": {
            "full_canvas_guide": "whole_head_outline_guide_4000x6000.png",
            "source_audit": "whole_head_outline_source_audit.png",
        },
        "limitations": [
            "The upper scalp is intentionally an inferred hidden face-underfill boundary even though it follows the supplied outline.",
            "Ear outer paths are orientation references only; the face-underfill mesh must not be expanded to the ear silhouette.",
            "This guide does not establish acceptance of a Cubism model. Use direct runtime renders and review the model alpha edge without post-render warping.",
        ],
    }
    target_path = OUT / "whole_head_contour_target.json"
    target_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    provenance = {
        "status": "guide_built",
        "inputs": {name: value["sha256"] for name, value in payload["inputs"].items()},
        "outputs": {path.name: sha256(path) for path in sorted(OUT.glob("*.png"))},
        "target_json": {"path": target_path.name, "sha256": sha256(target_path)},
    }
    (OUT / "guide_provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"combined_offset": COMBINED_OFFSET, "key_coordinates": payload["key_coordinates"], "artifacts": payload["artifacts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
