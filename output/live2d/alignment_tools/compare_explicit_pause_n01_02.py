"""Test one acoustically observed, previously unlabelled N01_02 pause."""
from __future__ import annotations

import json
import subprocess

import run_julius_forced_alignment as base


OUT = base.OUT / "explicit_pause_comparison"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    name = "N01_02"
    _, _, tokens = base.load_sentence(name)
    # The observed 0.45-s zero-energy gap follows the first /s a N w a/
    # sequence (the spoken "san wa") and precedes /k e i/.  JSON contains no
    # pau mora at that location, so this is an experimental grammar only.
    pattern = ["s", "a", "N", "w", "a", "k", "e", "i"]
    phonemes = [p for p, _ in tokens]
    at = next(i for i in range(len(phonemes)) if phonemes[i:i + len(pattern)] == pattern)
    tested = tokens[:at + 5] + [("sp", "[observed_pause]")] + tokens[at + 5:]
    prefix = OUT / f"{name}.explicit_pause"
    base.make_dfa_dict(tested, prefix)
    work = base.OUT / "julius_work"
    result = subprocess.run(
        [str(base.JULIUS), "-h", str(base.HMM), "-dfa", str(prefix.with_suffix(".dfa")),
         "-v", str(prefix.with_suffix(".dict")), "-palign", "-input", "file", "-nostrip"],
        input=str(work / f"{name}_nostrip_input.wav") + "\n",
        text=True, capture_output=True, cwd=str(base.KIT), check=False,
    )
    log = OUT / f"{name}.explicit_pause.log"
    log.write_text(result.stdout + "\n--- STDERR ---\n" + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Julius failed: {log}")
    rows = base.parse_alignment(log, tested, name)
    focus = [row for row in rows if 2.0 <= row["start_s_source"] <= 3.3]
    payload = {"status": "success", "experiment": "one inferred sp after san-wa before kei", "aligned_phonemes": len(rows), "focus_source_2_0_to_3_3_s": focus}
    (OUT / f"{name}.explicit_pause.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
