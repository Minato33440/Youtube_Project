"""One-off reproducible PTM-vs-monophone check for the suspected N01_02 pause."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import run_julius_forced_alignment as base


OUT = base.OUT / "ptm_comparison"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    work = base.OUT / "julius_work"
    name = "N01_02"
    _, _, tokens = base.load_sentence(name)
    log_path = OUT / f"{name}.ptm.log"
    result = subprocess.run(
        [str(base.JULIUS), "-h", str(base.KIT / "models" / "hmmdefs_ptm_gid.binhmm"),
         "-hlist", str(base.KIT / "models" / "logicalTri"),
         "-dfa", str(work / f"{name}.dfa"), "-v", str(work / f"{name}.dict"),
         "-palign", "-input", "file", "-nostrip"],
        input=str(work / f"{name}_nostrip_input.wav") + "\n",
        text=True, capture_output=True, cwd=str(base.KIT), check=False,
    )
    log_path.write_text(result.stdout + "\n--- STDERR ---\n" + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"PTM Julius failed: {log_path}")
    rows = base.parse_alignment(log_path, tokens, name)
    focus = [row for row in rows if 2.0 <= row["start_s_source"] <= 3.2]
    payload = {"status": "success", "model": "hmmdefs_ptm_gid.binhmm + logicalTri", "sentence": name, "aligned_phonemes": len(rows), "focus_source_2_0_to_3_2_s": focus}
    (OUT / f"{name}.ptm.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
