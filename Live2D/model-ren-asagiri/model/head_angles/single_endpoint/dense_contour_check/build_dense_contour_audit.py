"""Audit and densify the visible source jaw contour without changing art or Cubism files."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).resolve().parent
SINGLE_ENDPOINT = OUT.parent
SOURCE = Path(r"C:\Python\REX_AI\Youtube_Project\Live2D\model-ren-asagiri\art\Looking_down\Looking_down (2).png")
EXISTING_GUIDE = SINGLE_ENDPOINT / "guide" / "looking_down_2_source_landmark_guide.json"
JSON_OUT = OUT / "dense_visible_contour_target.json"
PNG_OUT = OUT / "dense_visible_contour_source_audit.png"
SCALE = 1.2904500571168767
OFFSET = [1404.826424299698, 161.11685212010656]

# Direct pixel inspection of the source.  These controls follow the visible
# lower facial edge: on the right, the thin brown face/neck line begins only
# at (545,626); points above it are hair-occluded and are intentionally absent.
VISIBLE_CONTROLS = [
    (545, 626), (540, 632), (535, 638), (530, 644), (525, 649), (520, 654),
    (515, 659), (510, 664), (505, 669), (500, 674), (495, 678), (490, 683),
    (485, 687), (480, 691), (475, 696), (470, 700), (465, 704), (460, 708),
    (455, 712), (450, 715), (445, 719), (440, 722), (435, 726), (430, 728),
    (424, 729), (420, 729), (415, 727), (410, 724), (405, 721), (400, 718),
    (395, 715), (390, 712), (385, 709), (380, 706), (375, 703), (370, 700),
    (365, 697), (360, 694), (355, 691), (350, 687), (345, 684), (340, 681),
    (335, 679), (330, 674), (325, 671), (320, 667), (315, 663), (310, 660),
    (305, 657), (300, 652), (295, 647), (290, 642), (285, 637), (280, 631),
    (275, 624), (270, 617), (265, 610), (260, 606), (255, 604), (251, 602),
]
INFERRED_RIGHT = [(622, 542), (615, 557), (606, 575), (595, 594), (582, 608), (565, 618), (545, 626)]
INFERRED_LEFT = [(251, 602), (248, 601), (246, 584), (245, 568)]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resample(points: list[tuple[float, float]], spacing: float) -> list[tuple[float, float]]:
    xy = np.asarray(points, dtype=float)
    lengths = np.linalg.norm(xy[1:] - xy[:-1], axis=1)
    cumulative = np.r_[0.0, np.cumsum(lengths)]
    locations = list(np.arange(0, cumulative[-1], spacing)) + [cumulative[-1]]
    answer = []
    for location in locations:
        segment = min(np.searchsorted(cumulative, location, side="right") - 1, len(lengths) - 1)
        amount = (location - cumulative[segment]) / max(lengths[segment], 1e-9)
        point = xy[segment] * (1 - amount) + xy[segment + 1] * amount
        answer.append((round(float(point[0]), 3), round(float(point[1]), 3)))
    return answer


def nearest_distance(point: tuple[float, float], dense: np.ndarray) -> float:
    return float(np.sqrt(np.sum((dense - np.asarray(point, dtype=float)) ** 2, axis=1)).min())


def heading_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    return round(float(np.degrees(np.arctan2(b[1] - a[1], b[0] - a[0]))), 3)


def stats(values: list[float]) -> dict:
    sample = np.asarray(values, dtype=float)
    return {"count": int(len(sample)), "min": round(float(sample.min()), 3), "median": round(float(np.median(sample)), 3), "max": round(float(sample.max()), 3), "mean": round(float(sample.mean()), 3)}


def draw_polyline(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], box: tuple[int, int, int, int], scale: float, color: tuple[int, int, int], width: int, dashed: bool = False) -> None:
    converted = [((x - box[0]) * scale, (y - box[1]) * scale) for x, y in points]
    if dashed:
        for a, b in zip(converted, converted[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            distance = max(float(np.hypot(dx, dy)), 1.0)
            for start in range(0, int(distance), 18):
                end = min(start + 10, distance)
                draw.line((a[0] + dx * start / distance, a[1] + dy * start / distance, a[0] + dx * end / distance, a[1] + dy * end / distance), fill=color, width=width)
    else:
        draw.line(converted, fill=color, width=width, joint="curve")


def build_marked_crop(existing_observed: list[tuple[float, float]]) -> None:
    box, scale = (220, 530, 660, 760), 3
    source = Image.open(SOURCE).convert("RGBA")
    crop = source.crop(box).resize(((box[2] - box[0]) * scale, (box[3] - box[1]) * scale), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(crop)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    for x in range(250, 651, 25):
        px = (x - box[0]) * scale
        draw.line((px, 0, px, crop.height), fill=(0, 240, 245, 130), width=1)
        draw.text((px + 2, 2), str(x), font=font, fill=(0, 240, 245), stroke_width=1, stroke_fill=(0, 0, 0))
    for y in range(550, 751, 25):
        py = (y - box[1]) * scale
        draw.line((0, py, crop.width, py), fill=(0, 240, 245, 130), width=1)
        draw.text((2, py + 2), str(y), font=font, fill=(0, 240, 245), stroke_width=1, stroke_fill=(0, 0, 0))
    draw_polyline(draw, INFERRED_RIGHT, box, scale, (255, 183, 45), 5, dashed=True)
    draw_polyline(draw, INFERRED_LEFT, box, scale, (255, 183, 45), 5, dashed=True)
    draw_polyline(draw, VISIBLE_CONTROLS, box, scale, (0, 232, 255), 5)
    draw_polyline(draw, existing_observed, box, scale, (255, 74, 208), 3, dashed=True)
    for x, y in existing_observed:
        if box[0] <= x <= box[2] and box[1] <= y <= box[3]:
            px, py = (x - box[0]) * scale, (y - box[1]) * scale
            draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill=(255, 74, 208), outline=(15, 15, 15))
    footer = Image.new("RGB", (crop.width, 70), (31, 36, 46))
    fd = ImageDraw.Draw(footer)
    fd.text((12, 8), "cyan: re-traced visible face/neck edge  |  amber: inferred behind hair (excluded)  |  magenta: existing observed guide", font=font, fill=(244, 246, 250))
    result = Image.new("RGB", (crop.width, crop.height + footer.height))
    result.paste(crop.convert("RGB"), (0, 0))
    result.paste(footer, (0, crop.height))
    result.save(PNG_OUT)


def main() -> None:
    guide = json.loads(EXISTING_GUIDE.read_text(encoding="utf-8"))
    old_observed_records = [p for p in guide["visible_facial_skin_outer_contour"]["points"] if p["reliability"] == "observed"]
    old_observed = [tuple(p["source_px"]) for p in old_observed_records]
    evaluation_samples = resample(VISIBLE_CONTROLS, 2.0)
    dense_for_nearest = np.asarray(resample(VISIBLE_CONTROLS, 0.25), dtype=float)
    old_deviations = []
    for p in old_observed_records:
        point = tuple(p["source_px"])
        old_deviations.append({"id": p["id"], "source_px": list(point), "distance_to_retraced_visible_contour_source_px": round(nearest_distance(point, dense_for_nearest), 3)})
    right_old = old_deviations[:10]
    left_old = old_deviations[10:]
    # A control every roughly 10 source pixels is a practical outer mesh ring;
    # 2px samples are evaluation-only and should not be copied into Cubism.
    mesh_controls = resample(VISIBLE_CONTROLS, 10.0)
    headings = [heading_deg(a, b) for a, b in zip(mesh_controls, mesh_controls[1:])]
    payload = {
        "purpose": "Dense audit target for the single left-screen oblique-nod endpoint. This is source observation, not a full-runtime acceptance result.",
        "source": {"path": str(SOURCE), "sha256": sha256(SOURCE), "dimensions_px": [958, 1004], "orientation": "as supplied; no rotation"},
        "fixed_reference_transform": {"full_canvas_scale": SCALE, "full_canvas_offset": OFFSET, "operation": "uniform scale and translation only; retain original tilt"},
        "classification": {
            "visible_observed": "Cyan controls trace the visible outer skin edge / thin brown face-to-neck line.",
            "inferred_hair_occluded": "Amber sections connect toward ears under hair. They are intentionally excluded from numerical contour evaluation and are not precision art targets.",
        },
        "visible_controls_source_px": [list(p) for p in VISIBLE_CONTROLS],
        "mesh_outer_ring_candidates_source_px": [list(p) for p in mesh_controls],
        "evaluation_samples_source_px": [list(p) for p in evaluation_samples],
        "inferred_hair_occluded_source_px": {"right": [list(p) for p in INFERRED_RIGHT], "left": [list(p) for p in INFERRED_LEFT]},
        "existing_guide_audit": {
            "existing_guide": str(EXISTING_GUIDE),
            "finding": "The existing left jaw controls remain close after the prior correction. On the image-right cheek/jaw, several points labelled observed are on an upper hair/occluded path rather than the visible face-to-neck boundary.",
            "right_observed_deviation_source_px": {"summary": stats([p["distance_to_retraced_visible_contour_source_px"] for p in right_old]), "points": right_old},
            "left_observed_deviation_source_px": {"summary": stats([p["distance_to_retraced_visible_contour_source_px"] for p in left_old]), "points": left_old},
        },
        "curvature_guard": {
            "outer_ring_spacing_source_px": 10,
            "outer_ring_headings_degrees": headings,
            "implementation": "Place an outer ring only at the practical controls, then place one inner support ring roughly 10-15 source px toward the face interior. The inner ring is an implementation support, not an observed source contour.",
            "evaluation": "For each 2px cyan sample, measure nearest model alpha edge distance; report p50, p90 and max separately for five equal arc-length bins (right cheek, right jaw, chin, left jaw, left cheek). Also inspect the red alpha edge/cyan target overlay at 4x. A low 25-point median alone is insufficient if a bin maximum or a chord midpoint bows away from cyan.",
        },
        "limitations": [
            "The upper right cheek and both ear junctions are hair-occluded; no precise outer skin contour is asserted there.",
            "This source path guides the bare face underfill but does not require exposed skin through hair layers.",
            "The source illustration and live model are not a pixel-match pair; use this as a shape diagnostic alongside visual review.",
        ],
        "artifacts": {"marked_source_crop": PNG_OUT.name},
    }
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    build_marked_crop(old_observed)
    print(JSON_OUT)
    print(PNG_OUT)
    print(json.dumps(payload["existing_guide_audit"], ensure_ascii=False))


if __name__ == "__main__":
    main()
