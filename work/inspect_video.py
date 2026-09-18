import json
import sys
from pathlib import Path

import yt_dlp

sys.stdout.reconfigure(encoding="utf-8")
root = Path(__file__).resolve().parent / "source_checks"
root.mkdir(parents=True, exist_ok=True)
opts = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "noplaylist": True,
    "js_runtimes": {"node": {}},
    "socket_timeout": 25,
    "retries": 1,
}
for video_id in sys.argv[1:]:
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        data = {key: info.get(key) for key in (
            "id", "title", "duration", "upload_date", "channel", "channel_url",
            "description", "chapters", "license", "availability", "webpage_url"
        )}
        data["subtitles"] = info.get("subtitles", {})
        data["automatic_captions"] = {
            k: v for k, v in info.get("automatic_captions", {}).items()
            if k.startswith("ja")
        }
        (root / f"{video_id}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({k: data.get(k) for k in ("id", "title", "duration", "upload_date", "channel", "chapters", "license")}, ensure_ascii=False))
        print("caption_languages", list(data["subtitles"]), list(data["automatic_captions"]))
    except Exception as exc:
        print(video_id, type(exc).__name__, str(exc))
