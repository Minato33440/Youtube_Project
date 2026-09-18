#!/usr/bin/env python3
"""Independent PSD structure and rendered-output verification with psd-tools."""
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS / "pylib"))
import numpy as np
from PIL import Image
from psd_tools import PSDImage


def rendered_difference(actual, expected, background):
    actual = actual.astype(np.float64)
    expected = expected.astype(np.float64)
    bg = np.array(background, dtype=np.float64)
    actual_rgb = actual[:, :, :3] * actual[:, :, 3:] / 255 + bg * (1 - actual[:, :, 3:] / 255)
    expected_rgb = expected[:, :, :3] * expected[:, :, 3:] / 255 + bg * (1 - expected[:, :, 3:] / 255)
    delta = np.abs(actual_rgb - expected_rgb)
    visible = (actual[:, :, 3] > 0) | (expected[:, :, 3] > 0)
    visible_delta = delta[visible]
    over2 = np.any(delta > 2, axis=2) & visible
    ys, xs = np.where(over2)
    return {
        "visiblePixels": int(visible.sum()),
        "maxVisiblePerChannelDifference": float(visible_delta.max()) if visible_delta.size else 0.0,
        "meanVisiblePerChannelDifference": float(visible_delta.mean()) if visible_delta.size else 0.0,
        "pixelsWithAnyChannelDifferenceOver2": int(over2.sum()),
        "over2Bounds": None if not len(xs) else {"left": int(xs.min()), "top": int(ys.min()), "right": int(xs.max()) + 1, "bottom": int(ys.max()) + 1},
    }


def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: verify_with_psd_tools.py <manifest.json> <parts.psd> <flattened.png>")
    manifest_file, psd_file, flattened_file = map(Path, sys.argv[1:])
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    expected_names = [layer["name"] for layer in manifest["layers"]]
    psd = PSDImage.open(psd_file)
    actual_layers = list(psd)
    actual_names = [layer.name for layer in actual_layers]
    if actual_names != expected_names:
        raise RuntimeError("psd-tools record order does not match manifest bottom-to-top order")
    for index, spec in enumerate(manifest["layers"]):
        if "clipTo" not in spec:
            continue
        if index == 0 or expected_names[index - 1] != spec["clipTo"]:
            raise RuntimeError(f"Invalid manifest clipping target for {spec['name']}")
        if not actual_layers[index].clipping:
            raise RuntimeError(f"psd-tools did not read clipping on {spec['name']}")
    # force=True prevents using the stored merged-preview and renders the PSD's layers.
    rendered = np.asarray(psd.composite(force=True).convert("RGBA"))
    flattened = np.asarray(Image.open(flattened_file).convert("RGBA"))
    if rendered.shape != flattened.shape:
        raise RuntimeError("psd-tools rendered dimensions do not match flattened PNG")
    raw_delta = np.abs(rendered.astype(np.int16) - flattened.astype(np.int16))
    result = {
        "status": "pass",
        "reader": "psd-tools 1.12.1",
        "layerRecordOrder": "bottom-to-top",
        "firstLayer": actual_names[0],
        "lastLayer": actual_names[-1],
        "layerCount": len(actual_names),
        "clippingLayers": [layer.name for layer in actual_layers if layer.clipping],
        "forceRenderedVsFlattenedRaw": {
            "differentPixels": int(np.any(raw_delta, axis=2).sum()),
            "maxChannelDelta": int(raw_delta.max()),
            "alphaDifferentPixels": int((raw_delta[:, :, 3] > 0).sum()),
        },
        "forceRenderedVsFlattenedDisplay": {
            "#F7F5F0": rendered_difference(rendered, flattened, (247, 245, 240)),
            "#808080": rendered_difference(rendered, flattened, (128, 128, 128)),
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
