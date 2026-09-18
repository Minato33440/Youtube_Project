import json
import sys
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")
root = Path(__file__).resolve().parent / "source_checks"

def stamp(ms):
    s = ms // 1000
    return f"{s // 3600:02}:{s // 60 % 60:02}:{s % 60:02}.{ms % 1000:03}"

for video_id in sys.argv[1:]:
    try:
        data = json.loads((root / f"{video_id}.json").read_text(encoding="utf-8"))
        captions = data["automatic_captions"].get("ja-orig") or data["automatic_captions"].get("ja")
        source = next(row for row in captions if row["ext"] == "json3")
        r = requests.get(source["url"], timeout=30)
        r.raise_for_status()
        payload = r.json()
        (root / f"{video_id}.ja.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        lines = []
        for e in payload.get("events", []):
            text = "".join(s.get("utf8", "") for s in e.get("segs", [])).strip()
            if text:
                start = int(e["tStartMs"])
                end = start + int(e.get("dDurationMs", 0))
                lines.append(f"{stamp(start)} --> {stamp(end)}  {text}")
        (root / f"{video_id}.ja.txt").write_text("\n".join(lines), encoding="utf-8")
        print(video_id, len(lines), "caption lines")
    except Exception as exc:
        print(video_id, type(exc).__name__, str(exc).split(" for url:")[0])
