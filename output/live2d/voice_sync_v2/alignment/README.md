# N01 Live2D phoneme alignment

`phonemes.json` and `phonemes.csv` are local Julius 4.3.1 forced-Viterbi
alignment results for the four original source utterances `N01_01.wav` through
`N01_04.wav`.  `start_s` and `end_s` are mapped to
`voice_sync_v1/audio_mono_44100_pcm16.wav`; `start_s_source`/`end_s_source`
remain in the individual source WAV timebase and `start_s_concat`/`end_s_concat`
are the raw four-file concatenation timebase.

## Reproduce

From the project root, use the supplied project runtime:

```powershell
& output/live2d/runtime_venv/Scripts/python.exe output/live2d/alignment_tools/run_julius_forced_alignment.py
```

The script locally converts each source WAV to 16-kHz PCM, reads its VoiceVox
JSON mora/phoneme labels, makes a linear Julius grammar, invokes the bundled
Julius executable, and writes the detailed per-sentence engine logs in
`julius_work/`.  It never uses the JSON duration fields.

`--clean` only replaces the current `julius_work/` scratch directory. It does
not remove `initial_stripped/` or the saved comparison records.

## Limits

Julius uses 10-ms feature shifts, so the boundaries have 10-ms resolution.
`sp` is reported for punctuation morae, but uses Julius's ordinary silence HMM
internally because its native short-pause model is transparent in palign logs.
One additional `sp` is explicitly marked as
`[observed_pause: N01_02 san-wa]`: a roughly 0.4-second zero-energy run in the
source follows that phrase, while the source JSON has no `pau` mora. This
evidence-based insertion prevents the forced grammar from assigning the pause
to its preceding vowel/nasal; it is not presented as a JSON-provided mora.
The source material ends at 15.6016104 s in target time.  The target clip's
separate RMS-active tail begins at approximately 15.86 s and has no claimed
phoneme alignment.
