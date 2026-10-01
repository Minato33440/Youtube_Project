# Whole-head outline guide and actual runtime comparison

## Result

The import-ready 4000x6000 PSD passed ag-psd RGBA readback and independent psd-tools canvas/layer-order checks.  The Rough image is an exact visible-RGBA crop of the original at original offset `(57, 1)` with scale `1.0`; therefore the outline-to-canvas transform is uniform scale `1.2904500571168767` and translation `(1478.38207755536, 162.40730217722344)`.  No rotation or un-tilting is applied.

- `whole_head_reference_4000x6000.psd`: five separate import layers for observed face edge, inferred scalp, ear outer reference, Boss outline, and Rough.
- `whole_head_outline_guide_4000x6000.png`: transparent 4000x6000 whole-head overlay.
- `whole_head_outline_source_audit.png`: cyan is the observed face-underfill edge; amber dashed is the inferred hair-hidden scalp; magenta ears are separate and excluded from the face target.
- `whole_head_runtime_guide_4up.png`: real direct-SDK face-runtime comparison at X=-30/Y=-30.

## Before and after measurement

The archived baseline and newly exported moc3 hashes differ and both hashes match files on disk. The observed face path has p50 `4.457 -> 2.635` px, p90 `14.333 -> 7.279` px, max `23.622 -> 9.92` px over `344` samples. The inferred scalp path has p50 `32.775 -> 6.76` px, p90 `92.52 -> 14.276` px, max `98.555 -> 16.856` px over `275` samples. These are 4000x6000 canvas distances, using the same fixed registration for both models.

## Preservation and remaining work

The 15 face-only frontal angle/mouth cases and eight full-model frontal/mouth cases have zero displayed-image difference from this task's backup. The three other endpoint poses have zero alpha-boundary difference. Thirty-two face-only pose/mouth cases were checked and the comparison sheets visually inspected.

This does not pass a perfect-edge acceptance gate. Small cheek kinks remain. At alpha>=16, endpoint rows show up to seven tiny edge splits; at alpha>=64, X=-15/Y=-30 has a one-row split in each mouth state. These are recorded rather than removed from the report. The public wrapper has no vertex/index buffer access for a numerical triangle inversion audit. No new continuous-motion or physics acceptance is claimed.

The renderer loads the exported model3/moc3 directly, disables blink/breath, does not call physics, and does not warp a model render. Ear outer contours are not included in face-underfill distance metrics. The hidden scalp remains an authorized approximation. Boss visual review of the face contour is pending; other facial parts have not been adjusted.
