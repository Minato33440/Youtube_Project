# Live2D PSD packaging helper

`build_psd.js` packages existing RGBA PNG parts into an RGB, 8-bit PSD. It does not alter artwork or resize images. Manifest layers are declared **bottom-to-top** and are written in that order, so Cubism displays the final manifest layer as the topmost layer and the first manifest layer as the bottommost layer.

```powershell
& 'C:/Users/Setona/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' `
  output/live2d/risa_parts_v1/tools/build_psd.js path/to/manifest.json
```

Use `--out-dir path/to/output` to place all emitted files in a separate directory. Relative PNG and output paths in a manifest resolve from the manifest's directory (unless `--out-dir` is supplied for output paths).

```json
{
  "canvas": { "width": 2048, "height": 2048 },
  "layers": [
    { "name": "body", "path": "parts/body.png", "left": 300, "top": 120, "visible": true },
    { "name": "eye_white_L", "path": "parts/eye_white_L.png", "left": 520, "top": 200 },
    { "name": "iris_L", "path": "parts/iris_L_full_circle.png", "left": 520, "top": 200, "clipTo": "eye_white_L" }
  ],
  "output": {
    "psd": "risa_parts_v1.psd",
    "flattenedPng": "risa_parts_v1_flattened.png",
    "previewPng": "risa_parts_v1_preview.png",
    "verificationJson": "risa_parts_v1_verification.json",
    "previewBackground": "#808080"
  }
}
```

`clipTo` is optional and limited to the immediately preceding layer in the manifest's bottom-to-top order. It stores Photoshop's clipping flag on the upper layer while preserving that layer's original, full PNG pixels. The flattened PNG clips its per-pixel alpha against the target layer's alpha at the same canvas coordinate. The emitted verification JSON records each source layer's file bounds and alpha bounds, and confirms a real `ag-psd` read-back of names, count, position, visibility, clipping, and exact RGBA data. `ag-psd` is installed locally in this tools directory (`ag-psd` 28.3.0); no global runtime files are changed.

To inspect the PSD's embedded merged preview after alpha compositing, without rebuilding any assets, run:

```powershell
& 'C:/Users/Setona/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe' `
  output/live2d/risa_parts_v1/tools/diagnose_merged_preview.js `
  output/live2d/risa_parts_v1/Risa_Live2D_Parts_v1.psd `
  output/live2d/risa_parts_v1/Risa_Live2D_Parts_v1.png
```

It reports the maximum and mean visible RGB differences plus the number of visible pixels exceeding a difference of 2, over `#F7F5F0` and `#808080`.

`pylib` contains a tools-local `psd-tools` installation for an independent layer-record and forced-layer-render check:

```powershell
& 'C:/Users/Setona/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' `
  output/live2d/risa_parts_v1/tools/verify_with_psd_tools.py `
  output/live2d/risa_parts_v1/manifest.json `
  output/live2d/risa_parts_v1/Risa_Live2D_Parts_v1.psd `
  output/live2d/risa_parts_v1/Risa_Live2D_Parts_v1.png
```
