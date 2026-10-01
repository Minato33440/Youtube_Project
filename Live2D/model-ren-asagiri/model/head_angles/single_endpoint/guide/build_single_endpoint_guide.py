"""Build a non-destructive source-space guide for the left-screen oblique nod endpoint."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


GUIDE_DIR = Path(__file__).resolve().parent
SOURCE = Path(
    r"C:\Python\REX_AI\Youtube_Project\Live2D\model-ren-asagiri\art\Looking_down\Looking_down (2).png"
)
PNG_OUT = GUIDE_DIR / "looking_down_2_source_landmark_guide.png"
JSON_OUT = GUIDE_DIR / "looking_down_2_source_landmark_guide.json"

# Path order is deliberately image-right cheek -> chin -> image-left cheek.
# The first/last short sections disappear under hair, so their positions are
# mesh-continuity estimates rather than claimed visible skin edges.
CONTOUR = [
    ("r_ear_face_junction", 622, 542, "inferred_occluded"),
    ("r_occlusion_1", 615, 557, "inferred_occluded"),
    ("r_occlusion_2", 606, 575, "inferred_occluded"),
    ("r_occlusion_exit", 595, 594, "inferred_occluded"),
    ("r_cheek_start", 574, 613, "observed"),
    ("r_cheek_1", 567, 626, "observed"),
    ("r_cheek_2", 557, 642, "observed"),
    ("r_jaw_1", 544, 657, "observed"),
    ("r_jaw_2", 529, 672, "observed"),
    ("r_jaw_3", 513, 686, "observed"),
    ("r_jaw_4", 496, 699, "observed"),
    ("r_jaw_5", 478, 710, "observed"),
    ("r_chin_slope", 459, 719, "observed"),
    ("chin_right", 441, 726, "observed"),
    ("chin_tip", 424, 729, "observed"),
    ("chin_left", 410, 724, "observed"),
    ("l_chin_slope", 390, 712, "observed"),
    ("l_jaw_1", 370, 700, "observed"),
    ("l_jaw_2", 355, 691, "observed"),
    ("l_jaw_3", 340, 682, "observed"),
    ("l_jaw_4", 320, 667, "observed"),
    ("l_jaw_5", 305, 657, "observed"),
    ("l_jaw_6", 290, 642, "observed"),
    ("l_cheek_1", 270, 617, "observed"),
    ("l_cheek_last_reliable", 251, 602, "observed"),
    ("l_occlusion_1", 248, 601, "inferred_occluded"),
    ("l_occlusion_2", 246, 584, "inferred_occluded"),
    ("l_ear_face_junction", 245, 568, "inferred_occluded"),
]

LANDMARKS = [
    ("pupil_left", 297.14, 529.50, "direct black-pupil component centroid; existing transform anchor remains [295.9, 527.3]"),
    ("pupil_right", 487.55, 507.47, "direct black-pupil component centroid; existing transform anchor remains [487.3, 507.3]"),
    ("eye_left_center", 295.0, 526.0, "visual approximation"),
    ("eye_right_center", 488.0, 510.0, "visual approximation"),
    ("nose_tip", 385.0, 589.0, "visual approximation; inherited manifest"),
    ("mouth_center", 413.0, 657.0, "visual approximation; inherited manifest"),
    ("chin_tip", 424.0, 729.0, "visible lower-face outline"),
    ("ear_left_visible_center", 144.0, 500.0, "manifest visual proxy, not a face junction"),
    ("ear_right_visible_center", 646.0, 507.0, "manifest visual proxy, not a face junction"),
    ("ear_face_junction_left", 245.0, 568.0, "inferred: hidden by hair"),
    ("ear_face_junction_right", 622.0, 542.0, "inferred: hidden by hair/ear overlap"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def guide_data() -> dict:
    return {
        "purpose": "Static mesh-placement guide for one left-screen oblique nod endpoint; no source art changes.",
        "source": {
            "path": str(SOURCE),
            "sha256": sha256(SOURCE),
            "dimensions_px": [958, 1004],
            "orientation": "as supplied; no rotation applied",
            "coordinate_convention": "origin at source top-left; x increases image-right and y increases downward",
        },
        "existing_reference_overlay_transform": {
            "source": "../../reference_overlay/reference_overlay_manifest.json",
            "aligned_display_px": {
                "formula": "x = 31.44792728990933 + source_x * 0.387135017135063; y = 48.33505563603197 + source_y * 0.387135017135063",
                "uniform_scale": 0.387135017135063,
                "offset": [31.44792728990933, 48.33505563603197],
            },
            "full_canvas_px": {
                "formula": "x = 1404.826424299698 + source_x * 1.2904500571168767; y = 161.11685212010656 + source_y * 1.2904500571168767",
                "uniform_scale": 1.2904500571168767,
                "offset": [1404.826424299698, 161.11685212010656],
            },
            "roll_note": "The left source pupil is 20.0 source px lower than the right (about 7.74 display px after alignment). Preserve this slope; do not upright-rotate the guide.",
        },
        "visible_facial_skin_outer_contour": {
            "direction": "image-right ear/cheek -> chin -> image-left cheek",
            "points": [
                {"id": ident, "source_px": [x, y], "reliability": reliability}
                for ident, x, y, reliability in CONTOUR
            ],
            "observed_section": "r_cheek_start through l_cheek_last_reliable",
            "inferred_sections": [
                "r_ear_face_junction through r_occlusion_exit",
                "l_occlusion_1 through l_ear_face_junction",
            ],
            "accuracy": "Observed points trace the visible lower facial outline to approximately 2-4 source px. Occluded junction points are continuity estimates only and should not be treated as visible line art.",
        },
        "anatomical_landmarks": [
            {"id": ident, "source_px": [x, y], "basis": basis}
            for ident, x, y, basis in LANDMARKS
        ],
        "alignment_pitfalls": [
            "Do not rotate the supplied image or force the pupils level; its roll is intentional in the established overlay.",
            "Use the green observed jaw section to remove a bare-face underfill, but keep skin behind the dark hair strands rather than drawing a new exposed skin strip.",
            "The two ear-face junctions and short upper-cheek continuations are hair-occluded. Use amber points only to preserve mesh continuity, not as precision artwork targets.",
            "The supplied illustration and model differ in construction and proportions. Anchor the endpoint first by the measured pupil centers, then use the contour as shape guidance rather than a pixel-match target.",
        ],
        "annotation_legend": {
            "green_solid": "observed visible skin outer contour",
            "amber_dashed": "inferred contour behind hair/ear overlap",
            "cyan": "pupils and central facial landmarks",
            "blue": "visible ear-center proxies",
        },
    }


def font(size: int):
    for candidate in (r"C:\Windows\Fonts\meiryo.ttc", r"C:\Windows\Fonts\arial.ttf"):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def draw_path(draw, point_list, scale, ox, oy, color, width, dashed=False):
    mapped = [(ox + x * scale, oy + y * scale) for _, x, y, _ in point_list]
    if dashed:
        for a, b in zip(mapped, mapped[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = max((dx * dx + dy * dy) ** 0.5, 1)
            for start in range(0, int(length), 20):
                end = min(start + 12, length)
                draw.line((a[0] + dx * start / length, a[1] + dy * start / length,
                           a[0] + dx * end / length, a[1] + dy * end / length), fill=color, width=width)
    else:
        draw.line(mapped, fill=color, width=width, joint="curve")
    for px, py in mapped:
        draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill=color, outline=(20, 20, 20), width=1)


def build_png(data: dict):
    im = Image.open(SOURCE).convert("RGBA")
    panel_w, panel_h = 3040, 1740
    background = Image.new("RGB", (panel_w, panel_h), (28, 32, 42))
    draw = ImageDraw.Draw(background)
    title_font, label_font, small_font = font(34), font(22), font(17)
    draw.text((40, 24), "Looking_down (2) — left-screen oblique nod endpoint", fill=(244, 246, 250), font=title_font)
    draw.text((40, 70), "SOURCE SPACE  |  supplied roll preserved  |  green=observed skin edge, amber=inferred under hair", fill=(186, 199, 216), font=label_font)

    # Left: the whole unrotated source with its contour position in context.
    full_scale, full_x, full_y = 1.48, 42, 130
    full = im.resize((round(im.width * full_scale), round(im.height * full_scale)), Image.Resampling.LANCZOS)
    background.paste(full, (full_x, full_y), full)
    draw.rectangle((full_x - 2, full_y - 2, full_x + full.width + 2, full_y + full.height + 2), outline=(102, 116, 137), width=2)

    right_inferred = CONTOUR[:4]
    observed = CONTOUR[4:25]
    left_inferred = CONTOUR[25:]
    draw_path(draw, right_inferred + [CONTOUR[4]], full_scale, full_x, full_y, (255, 180, 50), 5, dashed=True)
    draw_path(draw, observed, full_scale, full_x, full_y, (60, 245, 126), 5)
    draw_path(draw, [CONTOUR[24]] + left_inferred, full_scale, full_x, full_y, (255, 180, 50), 5, dashed=True)

    for ident, x, y, basis in LANDMARKS:
        px, py = full_x + x * full_scale, full_y + y * full_scale
        color = (65, 210, 250) if "ear_" not in ident else (95, 145, 255)
        draw.ellipse((px - 6, py - 6, px + 6, py + 6), fill=color, outline=(9, 12, 17), width=2)
    for name, x, y, dx, dy in [
        ("R junction (inferred)", 622, 542, 20, -22),
        ("R cheek: first reliable", 574, 613, 20, -2),
        ("chin", 424, 728, 18, 15),
        ("L cheek: last reliable", 251, 618, -215, 10),
        ("L junction (inferred)", 245, 568, -200, -22),
    ]:
        px, py = full_x + x * full_scale, full_y + y * full_scale
        draw.text((px + dx, py + dy), name, fill=(245, 247, 252), font=small_font, stroke_width=2, stroke_fill=(9, 12, 17))

    # Right: face zoom with a source-coordinate grid for implementation tracing.
    box, zoom, zx, zy = (180, 450, 700, 770), 3.7, 1575, 250
    crop = im.crop(box).resize((round((box[2] - box[0]) * zoom), round((box[3] - box[1]) * zoom)), Image.Resampling.LANCZOS)
    background.paste(crop, (zx, zy), crop)
    draw.rectangle((zx - 2, zy - 2, zx + crop.width + 2, zy + crop.height + 2), outline=(102, 116, 137), width=2)
    for x in range(200, 701, 50):
        px = zx + (x - box[0]) * zoom
        draw.line((px, zy, px, zy + crop.height), fill=(75, 220, 245), width=1)
        draw.text((px + 3, zy + 3), str(x), fill=(75, 220, 245), font=small_font, stroke_width=1, stroke_fill=(0, 0, 0))
    for y in range(450, 771, 50):
        py = zy + (y - box[1]) * zoom
        draw.line((zx, py, zx + crop.width, py), fill=(75, 220, 245), width=1)
        draw.text((zx + 3, py + 3), str(y), fill=(75, 220, 245), font=small_font, stroke_width=1, stroke_fill=(0, 0, 0))
    within = [p for p in CONTOUR if box[0] <= p[1] <= box[2] and box[1] <= p[2] <= box[3]]
    draw_path(draw, within[:5], zoom, zx - box[0] * zoom, zy - box[1] * zoom, (255, 180, 50), 8, dashed=True)
    draw_path(draw, within[4:25], zoom, zx - box[0] * zoom, zy - box[1] * zoom, (60, 245, 126), 8)
    draw_path(draw, within[24:], zoom, zx - box[0] * zoom, zy - box[1] * zoom, (255, 180, 50), 8, dashed=True)
    for ident, x, y, basis in LANDMARKS:
        if box[0] <= x <= box[2] and box[1] <= y <= box[3]:
            px, py = zx + (x - box[0]) * zoom, zy + (y - box[1]) * zoom
            color = (65, 210, 250) if "ear_" not in ident else (95, 145, 255)
            draw.ellipse((px - 8, py - 8, px + 8, py + 8), fill=color, outline=(9, 12, 17), width=2)
    draw.text((1575, 1530), "Source-coordinate detail. The amber ends are intentionally not a claimed visible outline.", fill=(214, 223, 235), font=label_font)
    draw.text((1575, 1570), "Direct pupil black-component centers: (297.14, 529.50) and (487.55, 507.47).", fill=(214, 223, 235), font=label_font)
    background.save(PNG_OUT)


if __name__ == "__main__":
    payload = guide_data()
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    build_png(payload)
    print(JSON_OUT)
    print(PNG_OUT)
