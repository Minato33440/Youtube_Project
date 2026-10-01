"""Create reference-only endpoint comparisons after render_preview.py completes."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "preview"
OVERLAY = ROOT / "reference_overlay"
MANIFEST = OVERLAY / "reference_overlay_manifest.json"


def labelled(image: Image.Image, label: str, font: ImageFont.FreeTypeFont) -> Image.Image:
    tile = Image.new("RGB", (420, 608), "#f4f1ec")
    background = Image.new("RGBA", (420, 570), "#eae4da")
    background.alpha_composite(image.convert("RGBA"))
    tile.paste(background.convert("RGB"), (0, 38))
    ImageDraw.Draw(tile).text((10, 10), label, fill="#1e232b", font=font)
    return tile


def source_crop(manifest: dict) -> Image.Image:
    """Use only the recorded uniform scale/translation; never rotate or re-fit."""
    source = Image.open(manifest["source"]["path"]).convert("RGBA")
    alignment = manifest["alignment"]
    scale = float(alignment["display_scale"])
    offset = tuple(round(float(v)) for v in alignment["display_offset"])
    raster = source.resize(tuple(round(v * scale) for v in source.size), Image.Resampling.LANCZOS)
    crop = Image.new("RGBA", (420, 570), (0, 0, 0, 0))
    crop.alpha_composite(raster, offset)
    return crop


def mirrored_geometry_crop(manifest: dict) -> Image.Image:
    """Place the declared right guide at its manifest position, then take case crop."""
    layer = next(item for item in manifest["layers"] if item["name"].startswith("reference_right"))
    guide = Image.open(OVERLAY / layer["path"]).convert("RGBA")
    canvas = Image.new("RGBA", tuple(manifest["canvas"]["dimensions"]), (0, 0, 0, 0))
    canvas.alpha_composite(guide, (int(layer["left"]), int(layer["top"])))
    # The preview is the 0.3 model-scale canvas cropped at (390, 0).
    preview_full = canvas.resize((1200, 1800), Image.Resampling.LANCZOS)
    return preview_full.crop((390, 0, 810, 570))


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    original_reference = source_crop(manifest)
    mirrored_reference = mirrored_geometry_crop(manifest)
    rows = []
    for case_no, direction in ((1, "Left + nod"), (3, "Right + nod")):
        current = Image.open(OUT / f"case_{case_no:02d}.png").convert("RGBA")
        before = Image.open(OUT / f"before_tilted_reference_case_{case_no:02d}.png").convert("RGBA")
        reference = original_reference if case_no == 1 else mirrored_reference
        guide_label = ("Original unrotated source — left endpoint"
                       if case_no == 1 else "Mirrored shape guide (colors ignored)")
        # Apply the requested 50% reference opacity without modifying the source or guide.
        half_reference = reference.copy()
        half_reference.putalpha(half_reference.getchannel("A").point(lambda value: value // 2))
        overlay = current.copy()
        overlay.alpha_composite(half_reference)
        overlay_name = (f"case_{case_no:02d}_unrotated_reference_overlay_50.png" if case_no == 1
                        else f"case_{case_no:02d}_mirrored_geometry_reference_overlay_50.png")
        overlay.save(OUT / overlay_name)
        row = Image.new("RGB", (1680, 608), "#f4f1ec")
        row.paste(labelled(before, f"Before — {direction}", font), (0, 0))
        row.paste(labelled(current, f"Current — {direction}", font), (420, 0))
        row.paste(labelled(reference, guide_label, font), (840, 0))
        row.paste(labelled(overlay, f"Current + 50% reference — {direction}", font), (1260, 0))
        rows.append(row)
    sheet = Image.new("RGB", (1680, 1216), "#f4f1ec")
    for index, row in enumerate(rows):
        sheet.paste(row, (0, index * 608))
    sheet.save(OUT / "tilted_reference_before_current_comparison.jpg", quality=95)
    metadata = {
        "status": "pass",
        "source_transform": {
            "display_scale": manifest["alignment"]["display_scale"],
            "display_offset": manifest["alignment"]["display_offset"],
            "operation": "manifest uniform scale and translation only; no rotation, re-fit, warp, or source modification",
        },
        "inputs": ["before_tilted_reference_case_01.png", "case_01.png", "before_tilted_reference_case_03.png", "case_03.png"],
        "outputs": ["case_01_unrotated_reference_overlay_50.png", "case_03_mirrored_geometry_reference_overlay_50.png", "tilted_reference_before_current_comparison.jpg"],
        "reference_columns": {"case_01": "unrotated original source", "case_03": "reference_right geometry-only mirror placed at manifest coordinates; not final colored art"},
    }
    (OUT / "tilted_reference_comparison.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
