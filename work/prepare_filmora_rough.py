"""Prepare seven local review clips from four selected public source videos."""
import csv
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yt_dlp

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "Politics_Economics" / "2026-09-09_fiscal_policy"
MEDIA = PROJECT / "media"
SOURCES = MEDIA / "sources"
CLIPS = MEDIA / "rough_v1_clips"
for folder in (SOURCES, CLIPS, PROJECT / "filmora", PROJECT / "exports"):
    folder.mkdir(parents=True, exist_ok=True)
rows = list(csv.DictReader((PROJECT / "cuts.csv").open(encoding="utf-8-sig", newline="")))

def seconds(value):
    h, m, s = map(int, value.split(":"))
    return h * 3600 + m * 60 + s

def fetch(vid):
    target = SOURCES / f"{vid}.mp4"
    if target.is_file() and target.stat().st_size > 10000:
        print(f"SOURCE EXISTS {vid}", flush=True)
        return target
    print(f"DOWNLOAD START {vid}", flush=True)
    opts = {
        "format": "bv[height<=1080][vcodec^=avc1]+ba[ext=m4a]/b[height<=1080][ext=mp4]",
        "outtmpl": str(SOURCES / "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "js_runtimes": {"node": {}},
        "quiet": True,
        "noprogress": True,
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 2,
        "fragment_retries": 2,
        "overwrites": False,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([f"https://www.youtube.com/watch?v={vid}"])
    if not target.is_file():
        raise RuntimeError(f"Expected MP4 missing: {vid}")
    print(f"DOWNLOAD DONE {vid} {target.stat().st_size // 1048576} MiB", flush=True)
    return target

ids = list(dict.fromkeys(r["video_id"] for r in rows))
with ThreadPoolExecutor(max_workers=2) as pool:
    futures = {pool.submit(fetch, vid): vid for vid in ids}
    for future in as_completed(futures):
        future.result()

manifest = []
cursor = 0
for row in rows:
    vid = row["video_id"]
    duration = seconds(row["source_out"]) - seconds(row["source_in"])
    output = CLIPS / f"{row['cut_id']}_{vid}.mp4"
    print(f"CUT START {row['cut_id']} {duration}s", flush=True)
    if not output.exists():
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
                   "-ss", row["source_in"], "-i", str(SOURCES / f"{vid}.mp4"), "-t", str(duration),
                   "-map", "0:v:0", "-map", "0:a:0", "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1",
                   "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(output)]
        subprocess.run(command, check=True)
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate", "-of", "json", str(output)], check=True, capture_output=True, text=True, encoding="utf-8")
    info = json.loads(result.stdout)
    actual = float(info["format"]["duration"])
    if abs(actual - duration) > 0.12:
        raise RuntimeError(f"Duration mismatch {row['cut_id']}: {actual} / {duration}")
    manifest.append({"cut_id": row["cut_id"], "video_id": vid, "source_in": row["source_in"], "source_out": row["source_out"],
                     "timeline_in_seconds": cursor, "timeline_out_seconds": cursor + duration,
                     "path": str(output), "duration_seconds": actual, "streams": info["streams"]})
    cursor += duration
    print(f"CUT DONE {row['cut_id']} {actual:.3f}s", flush=True)
(PROJECT / "rough_v1_manifest.json").write_text(json.dumps({"version": "rough_v1", "narration_included": False, "planned_duration_seconds": cursor, "clips": manifest}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"READY {len(manifest)} clips {cursor // 60}:{cursor % 60:02}", flush=True)
