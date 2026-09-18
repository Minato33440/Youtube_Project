# Filmora layered trial — 2026-09-15

> Superseded after Boss's playback review: all timeline video clips in this original trial were frozen. The earlier decode/audio checks did not test temporal motion. Use `Risa_Layered_Trial_20260915_MotionFixed.wfp` and its matching MP4. See `filmora_motion_fix_report.md` for the correction and new verification; the historical observations below are not a motion-quality approval.

Boss requested a prototype only. Delivered the first 00:02:38:05 (4745 frames), with one narration segment, without extending this Filmora project to the full video.

## Deliverables

- Native project: `../../filmora/Risa_Layered_Trial_20260915.wfp`
- Native Filmora export: `../../exports/Risa_Layered_Trial_20260915.mp4`
- Source assets: `../../media/sample_v1_risa/`
- Automated evidence: `filmora_trial_verification.json`
- Inspected representative frames: `filmora_trial_contact_sheet.jpg`

The native GUI contains Video 1 (five cut clips with linked audio), Video 2 (N01 background), Video 3 (N01 transparent Live2D MOV), and Audio 1 (N01 narration WAV). N01 occupies 00:00:21:13–00:00:37:12. Background and model can be repositioned independently; narration volume/timing can be edited separately. The model is rendered transparent video, not a Cubism rig inside Filmora. Background text is baked into its video and is not an editable Filmora title.

## Verified

- Filmora 15.6.4.20299 opened the prepared project and displayed the transparent model over its separate background.
- Native Save As produced a new project identity at 19:22 JST. Reopening the saved final WFP succeeded and retained all layers and media.
- Native local MP4 export succeeded at 19:27 JST; the exported file was copied unchanged from Filmora Output into project exports.
- 1920×1080, 30 fps, 4745 frames, H.264/AAC stereo 48 kHz, 158.166 seconds, 39,237,251 bytes.
- Full FFmpeg decode completed without errors. All eight referenced source assets exist.
- Six segment audio comparisons against their own source assets detected 0 ms peak correlation offset at 16 kHz analysis resolution. Correlations ranged from 0.9924 to 0.9999; narration was 0.9939. AAC re-encoding means audio is not byte-identical to source.
- Six representative frames inspected: cut video, narration start/middle/end, first following cut, and later cut. Model alpha, placement, background and text displayed correctly.

Boss's full viewing/listening judgment of this Filmora export remains pending. Earlier approval of the code-generated motion sample is distinct from approval of this new native export.

## Reproduction and limitations

The minimal WFP written by `work/build_risa_filmora.py` was rejected at Filmora's initial project validation. Repacking the original native WFP succeeded, so ZIP compression alone was not the cause. Preserving the original native `project_info.json` and ZIP entries while replacing timeline/media data, then performing native Save As, succeeded. The exact rejecting metadata field is not established; do not treat arbitrary WFP generation as generally supported.

`work/prepare_filmora_trial.py` records this preparation route. Use native Save As to a new file, reopen, export and verify every prepared project. The delivered WFP is the natively saved version; the diagnostic WFP files are not deliverables.

## Execution record

- Coordinator: Astra; current reasoning strength not independently observed. One existing child agent (prior Terra/Medium assignment) performed bounded read-only container comparison; parent alone operated Filmora. Follow-up reused the existing child task context, with no new full-history fork.
- Native export took approximately 20 seconds. Overall preparation required metadata compatibility retries and an audio media-type correction; exact total work time was not measured.
- Audio registration corrected from image type 16 to audio type 4, WAV stream metadata corrected, and narration placed on standalone Audio 1.
- The automated verifier initially encountered missing SciPy and was changed to NumPy FFT correlation; no package installation was needed.
- No full-length Filmora extension, publication, or change to the original/completed full MP4 was performed.
