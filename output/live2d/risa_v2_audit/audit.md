# Risa v2 asset audit

1. Compared current `parts/` PNG bytes and decoded RGBA pixels to the 23 PNGs in `Risa_Live2D_Parts_v1_bundle.zip`; 13 are byte-identical, 10 changed, 3 are new, and no v1 PNG is missing.
2. All 26 current files decode as RGBA and every file has at least one transparent pixel. This audit found no fully opaque PNG that would by itself indicate an opaque rectangular background.
3. Nine revised existing files changed dimensions: both brows, both ears, both upper lids, and the three mouth-outline files. `Head_Skin_Nose.png` changed pixels without a dimension change.
4. The three new, unreferenced files are `Hair_Front_Left_Pin.png.png`, `Hair_Front_Right_Pin.png`, and `Head_Skin_Nose_Ears_Neck.png`. The first name has a double `.png` suffix.
5. `manifest.json` still references 23 existing files and none of those three new files. Its dimensions and placements therefore do not describe the new split-hair assets.
6. The v1 PSD was written at 13:56, before the revised PNG writes from 14:34 through 17:50. It is stale relative to the changed parts; this audit did not rebuild it.
7. `Risa_Live2D_Parts_v2.cmo3` is a later file (17:58, SHA-256 `2199FCD2AD30877E98590EFA35755ECAB1CDC4D94CE2152A8E14D9B79E4BA517`). PNG comparison alone cannot establish which assets or parameters it contains.
8. The v1 bundle SHA-256 is `AA8A632581EA010EE1E20E9E17A26D8F15B7815F14C10A377C341C03668A2206`; the current manifest SHA-256 is `3450BB839EA059D0AA6E0AAF3E37D30C39BC8CC08F07850109750A8E63CB2124`.

See [audit.json](audit.json) for changed/new file hashes and old/new dimensions. No assets, manifests, PSDs, CMO3 files, or Cubism UI state were modified.
