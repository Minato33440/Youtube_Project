"""Create Japanese phoneme boundaries with the bundled Julius segmentation kit.

This intentionally uses the per-mora phoneme labels from the source VoiceVox
JSON, rather than its zero-valued duration fields.  It builds a linear Julius
DFA whose words are individual phonemes, then parses Julius forced-alignment
frames.  Source utterances are aligned separately before mapping to the
concatenated Live2D clip timeline.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
SOURCE_DIR = ROOT / "Politics_Economics" / "2026-09-09_fiscal_policy" / "speech" / "sample_v1"
KIT = Path(__file__).resolve().parent / "segmentation-kit"
OUT = ROOT / "output" / "live2d" / "voice_sync_v2" / "alignment"
JULIUS = KIT / "bin" / "julius-4.3.1.exe"
HMM = KIT / "models" / "hmmdefs_ptm_gid.binhmm"
HLIST = KIT / "models" / "logicalTri"

# Determined by sample-accurate comparison with the N01 source concatenation.
CLIP_OFFSET_SECONDS = 0.000726


def duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def frames(path: Path) -> int:
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes()


def active_tail_start(path: Path, after_s: float, threshold: float = 80.0) -> float | None:
    """Return the first 10-ms RMS-active bin after `after_s`, if any."""
    with wave.open(str(path), "rb") as wav:
        rate = wav.getframerate()
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float32)
    frame = max(1, round(rate * 0.01))
    first_bin = int(after_s * rate) // frame
    for i in range(first_bin, len(samples) // frame):
        chunk = samples[i * frame:(i + 1) * frame]
        if float(np.sqrt(np.mean(chunk * chunk))) >= threshold:
            return round(i * frame / rate, 7)
    return None


def longest_low_energy_run(path: Path, start_s: float, end_s: float, threshold: float = 80.0) -> dict | None:
    """Find a >=40-ms low-energy run inside one source-time phoneme span."""
    with wave.open(str(path), "rb") as wav:
        rate = wav.getframerate()
        samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float32)
    width = max(1, round(rate * 0.01))
    begin = max(0, int(start_s * rate) // width)
    finish = min(len(samples) // width, (int(end_s * rate) + width - 1) // width)
    best_start = best_len = current_start = current_len = 0
    for index in range(begin, finish):
        chunk = samples[index * width:(index + 1) * width]
        low = float(np.sqrt(np.mean(chunk * chunk))) < threshold
        if low:
            if not current_len:
                current_start = index
            current_len += 1
            if current_len > best_len:
                best_start, best_len = current_start, current_len
        else:
            current_len = 0
    if best_len < 4:
        return None
    return {"low_energy_start_s_source": round(best_start * width / rate, 7), "low_energy_end_s_source": round((best_start + best_len) * width / rate, 7), "low_energy_duration_s": round(best_len * width / rate, 7)}


def replace_exact_zero_with_dither(source: Path, destination: Path) -> int:
    """Avoid a Julius 4.3.1 zero-energy failure without changing sample count/time.

    With `-nostrip`, this bundled build rejects a leading all-zero PCM region
    before forced alignment.  Replacing only exact zeros by integer PCM value
    1 retains every sample and the waveform timebase while avoiding that
    implementation failure.  This is an alignment-only copy; original audio
    remains untouched.
    """
    with wave.open(str(source), "rb") as wav:
        params = wav.getparams()
        values = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").copy()
    zero_count = int(np.count_nonzero(values == 0))
    values[values == 0] = 1
    with wave.open(str(destination), "wb") as wav:
        wav.setparams(params)
        wav.writeframes(values.astype("<i2").tobytes())
    return zero_count


def load_sentence(name: str) -> tuple[str, str, list[tuple[str, str]]]:
    data = json.loads((SOURCE_DIR / f"{name}.json").read_text(encoding="utf-8-sig"))
    tokens: list[tuple[str, str]] = []
    for phrase in data["query"]["accent_phrases"]:
        for mora in phrase["moras"]:
            mora_text = mora["text"]
            vowel = mora["vowel"]
            consonant = mora["consonant"]
            if vowel == "pau":
                tokens.append(("sp", mora_text))
            else:
                if consonant:
                    tokens.append((consonant, mora_text))
                tokens.append((vowel, mora_text))
    return data["text"], data.get("spoken_text", data["text"]), tokens


def insert_observed_pauses(name: str, tokens: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Add only a manually evidenced pause absent from the VoiceVox mora JSON."""
    if name != "N01_02":
        return tokens
    # In the source waveform, a >= 0.40-s zero-energy run follows the first
    # /s a N w a/ (spoken "san wa") and precedes /k e i/.  No `pau` mora is
    # present there, so retain an explicit provenance label in output.
    pattern = ["s", "a", "N", "w", "a", "k", "e", "i"]
    phonemes = [phoneme for phoneme, _ in tokens]
    at = next(i for i in range(len(phonemes)) if phonemes[i:i + len(pattern)] == pattern)
    return tokens[:at + 5] + [("sp", "[observed_pause: N01_02 san-wa]")] + tokens[at + 5:]


def make_dfa_dict(tokens: list[tuple[str, str]], prefix: Path) -> None:
    # Julius treats the physical `sp` model as an optional transparent short
    # pause and therefore omits it from palign output.  Use its ordinary
    # silence HMM internally for comma/full-stop morae, while retaining `sp`
    # as the reported phoneme label below.
    words = ["silB", *["silB" if phoneme == "sp" else phoneme for phoneme, _ in tokens], "silE"]
    # Same linear grammar layout as the official segment_julius.pl.
    lines = []
    final_word = len(words) - 1
    for i in range(len(words)):
        lines.append(f"{i} {final_word - i} {i + 1} 0 {1 if i == 0 else 0}")
    lines.append(f"{len(words)} -1 -1 1 0")
    prefix.with_suffix(".dfa").write_text("\n".join(lines) + "\n", encoding="ascii")
    prefix.with_suffix(".dict").write_text(
        "\n".join(f"{i} [w_{i}] {word}" for i, word in enumerate(words)) + "\n",
        encoding="ascii",
    )


ALIGN_RE = re.compile(r"^\[\s*(\d+)\s+(\d+)\]\s+[0-9.\-]+\s+(.*)$")


def parse_alignment(log_path: Path, tokens: list[tuple[str, str]], sentence: str) -> list[dict]:
    result: list[dict] = []
    in_alignment = False
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "begin forced alignment" in line:
            in_alignment = True
            continue
        if "end forced alignment" in line:
            in_alignment = False
        if not in_alignment:
            continue
        match = ALIGN_RE.match(line)
        if not match:
            continue
        begin_frame, end_frame, unit = match.groups()
        result.append((int(begin_frame), int(end_frame)))
    # The kit injects silB/silE around every utterance.  The middle rows map
    # positionally to our constrained phoneme grammar, including pause morae.
    if len(result) >= 2:
        result = result[1:-1]
    rows: list[dict] = []
    for (bf, ef), (phoneme, mora) in zip(result, tokens):
        # Official kit's 25-ms window convention: start is frame*10ms plus
        # 12.5ms except at frame zero, end is (frame+1)*10ms plus 12.5ms.
        start = bf * 0.01 + (0.0125 if bf else 0.0)
        end = (ef + 1) * 0.01 + 0.0125
        rows.append({
            "start_s_source": round(start, 7), "end_s_source": round(end, 7),
            "phoneme": phoneme, "sentence": sentence, "mora": mora,
            "begin_frame": bf, "end_frame": ef,
        })
    if len(rows) != len(tokens):
        raise RuntimeError(f"{sentence}: Julius returned {len(rows)} phonemes; expected {len(tokens)}")
    return rows


def align_one(name: str, work: Path) -> tuple[list[dict], dict]:
    text, spoken_text, tokens = load_sentence(name)
    tokens = insert_observed_pauses(name, tokens)
    source_wav = SOURCE_DIR / f"{name}.wav"
    work_wav = work / f"{name}.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(source_wav), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(work_wav)], check=True)
    julius_wav = work / f"{name}_nostrip_input.wav"
    dithered_zero_samples = replace_exact_zero_with_dither(work_wav, julius_wav)
    prefix = work / name
    make_dfa_dict(tokens, prefix)
    completed = subprocess.run(
        [str(JULIUS), "-h", str(HMM), "-hlist", str(HLIST), "-dfa", str(prefix.with_suffix('.dfa')), "-v", str(prefix.with_suffix('.dict')), "-palign", "-input", "file", "-nostrip"],
        input=str(julius_wav) + "\n", text=True, capture_output=True, cwd=str(KIT), check=False,
    )
    log = completed.stdout + "\n--- STDERR ---\n" + completed.stderr
    (work / f"{name}.log").write_text(log, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"Julius failed for {name}; see {work / (name + '.log')}")
    processed = re.findall(r"^STAT:\s+(\d+) samples \(", log, flags=re.MULTILINE)
    expected = frames(julius_wav)
    if len(processed) != 1 or int(processed[0]) != expected:
        raise RuntimeError(f"{name}: processed samples {processed!r}; expected unstripped {expected}; see {work / (name + '.log')}")
    rows = parse_alignment(work / f"{name}.log", tokens, name)
    metadata = {"sentence": name, "text": text, "spoken_text": spoken_text, "source_duration_s": duration(source_wav), "expected_phonemes": len(tokens), "aligned_phonemes": len(rows), "converted_16khz_samples": expected, "julius_processed_samples": int(processed[0]), "zero_stripping": "disabled (-nostrip); sample counts match", "exact_zero_samples_replaced_with_pcm_1_in_alignment_copy": dithered_zero_samples, "inferred_pause_insertions": 1 if name == "N01_02" else 0}
    return rows, metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", action="store_true", help="Remove only this alignment working directory before rerun.")
    args = parser.parse_args()
    work = OUT / "julius_work"
    if args.clean and work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    sentence_meta: list[dict] = []
    concat_offset = 0.0
    for name in ("N01_01", "N01_02", "N01_03", "N01_04"):
        rows, metadata = align_one(name, work)
        for row in rows:
            row["start_s_concat"] = round(row["start_s_source"] + concat_offset, 7)
            row["end_s_concat"] = round(row["end_s_source"] + concat_offset, 7)
            row["start_s"] = round(row["start_s_concat"] + CLIP_OFFSET_SECONDS, 7)
            row["end_s"] = round(row["end_s_concat"] + CLIP_OFFSET_SECONDS, 7)
            all_rows.append(row)
        metadata["concat_start_s"] = round(concat_offset, 7)
        metadata["concat_end_s"] = round(concat_offset + metadata["source_duration_s"], 7)
        sentence_meta.append(metadata)
        concat_offset += metadata["source_duration_s"]
    with (OUT / "phonemes.json").open("w", encoding="utf-8") as f:
        json.dump({"method": "Julius 4.3.1 forced Viterbi alignment", "time_resolution_s": 0.01, "clip_offset_s": CLIP_OFFSET_SECONDS, "sentences": sentence_meta, "phonemes": all_rows}, f, ensure_ascii=False, indent=2)
    fields = ["start_s", "end_s", "phoneme", "sentence", "mora", "start_s_source", "end_s_source", "start_s_concat", "end_s_concat", "begin_frame", "end_frame"]
    with (OUT / "phonemes.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_rows)
    short = []
    long_vowels = []
    for row in all_rows:
        item = {key: row[key] for key in ("sentence", "start_s", "end_s", "phoneme", "mora")}
        item["duration_s"] = round(row["end_s"] - row["start_s"], 7)
        if item["duration_s"] < 0.015:
            short.append(item)
        if row["phoneme"] in {"a", "i", "u", "e", "o"} and item["duration_s"] > 0.3:
            long_vowels.append(item)
    long_non_pause = []
    low_energy_absorbed = []
    for row in all_rows:
        item = {key: row[key] for key in ("sentence", "start_s", "end_s", "phoneme", "mora", "start_s_source", "end_s_source")}
        item["duration_s"] = round(row["end_s"] - row["start_s"], 7)
        if row["phoneme"] != "sp" and item["duration_s"] > 0.3:
            long_non_pause.append(item)
        if row["phoneme"] != "sp":
            low_run = longest_low_energy_run(SOURCE_DIR / f"{row['sentence']}.wav", row["start_s_source"], row["end_s_source"])
            if low_run:
                low_energy_absorbed.append(item | low_run)
    target = ROOT / "output" / "live2d" / "voice_sync_v1" / "audio_mono_44100_pcm16.wav"
    source_end_on_clip = concat_offset + CLIP_OFFSET_SECONDS
    tail_start = active_tail_start(target, source_end_on_clip)
    report = {
        "status": "success",
        "source_concat_duration_s": round(concat_offset, 7),
        "target_clip_duration_s": duration(target),
        "clip_offset_s": CLIP_OFFSET_SECONDS,
        "phoneme_count": len(all_rows),
        "unaligned_target_region_start_s": round(source_end_on_clip, 7),
        "first_rms_active_tail_bin_s": tail_start,
        "anomalies": {"phoneme_shorter_than_15ms": short, "vowel_longer_than_300ms": long_vowels, "non_pause_phoneme_longer_than_300ms": long_non_pause, "low_energy_40ms_or_more_inside_non_pause_phoneme": low_energy_absorbed},
        "caveats": ["Julius feature frames are 10 ms; boundaries are not sub-frame precision.", "silB/silE are omitted from phonemes outputs.", "One `sp` is an explicitly marked observation-based insertion: N01_02 san-wa pause; it was absent from the JSON mora list.", "The target clip has non-source material after the source-concatenation region; no phoneme is asserted for it."],
    }
    (OUT / "quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "execution.log").write_text(
        "Julius 4.3.1 forced alignment completed successfully.\n"
        f"Acoustic model: {HMM}\n"
        "Input was each original N01_01..N01_04 WAV, converted locally to 16-kHz PCM.\n"
        f"Output phonemes: {len(all_rows)}\n"
        f"Source concat duration: {concat_offset:.7f}s\n"
        f"Target mapping offset: {CLIP_OFFSET_SECONDS:.7f}s\n"
        f"Unaligned target region starts: {source_end_on_clip:.7f}s\n"
        f"First RMS-active 10ms tail bin: {tail_start}\n"
        f"Shorter than 15ms: {len(short)}; vowels longer than 300ms: {len(long_vowels)}; non-pause phonemes longer than 300ms: {len(long_non_pause)}; low-energy absorption flags: {len(low_energy_absorbed)}\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
