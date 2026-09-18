"""Build a review candidate from the original interview; retain source and cut map."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "Politics_Economics/2026-09-09_fiscal_policy"
SOURCE = PROJECT / "media/sources/FjHO1E_QLVo.mp4"
OUT = PROJECT / "media/net_demand_candidate_v1"
OUT.mkdir(parents=True, exist_ok=True)
META = PROJECT / "code_edit/net_demand_candidate_v1.json"
META.parent.mkdir(parents=True, exist_ok=True)
REVIEW = PROJECT / "exports/net_demand_candidate_v1.mp4"
REVIEW.parent.mkdir(parents=True, exist_ok=True)
parts = [
    ("ND01", 1508.24, 1595.48, "指標の定義と、ネットゼロだった時期の説明"),
    ("ND02", 1701.00, 1767.50, "家計支援・成長投資とマイナス5の目安、過大拡張は別"),
    ("ND03", 1794.28, 1813.44, "インフレにはネット資金需要と輸入物価が影響するという説明"),
    ("ND04", 1832.40, 1894.50, "輸入物価上昇ゼロという条件、賃金上昇は可能性、過大拡張のインフレ"),
]


def run(args):
    return subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def probe(path):
    return json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                           "-of", "json", str(path)]).stdout)


manifest = {
    "version": "net_demand_candidate_v1", "created": "2026-09-10",
    "source_url": "https://www.youtube.com/watch?v=FjHO1E_QLVo",
    "reference_url": "https://www.youtube.com/watch?v=hDWfHRL5pbQ&t=877s",
    "source_channel": "ニュースの争点 公式チャンネル",
    "source_upload_date": "2025-11-05", "recording_date": None,
    "time_unit": "seconds", "source_out_is_exclusive": True,
    "status": "review_candidate_not_final", "source": str(SOURCE),
    "review": str(REVIEW), "parts": [],
    "content_checks": {
        "automatic_captions": True, "representative_video_frames": True,
        "audio_listening": False, "full_video_watch": False,
        "note": "Audio input is unavailable in this session. Boundaries require listening before final adoption.",
    },
}
cursor = 0
for clip_id, start, end, purpose in parts:
    dest = OUT / f"{clip_id}.mp4"
    if not dest.exists():
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
             "-ss", str(start), "-i", str(SOURCE), "-t", str(end-start),
             "-map", "0:v:0", "-map", "0:a:0", "-r", "30", "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
             "-movflags", "+faststart", str(dest)])
    info = probe(dest)
    duration = float(info["format"]["duration"])
    if abs(duration-(end-start)) > .12:
        raise RuntimeError(f"Unexpected duration: {clip_id}: {duration}")
    manifest["parts"].append({"id": clip_id, "source_in": start, "source_out": end,
        "timeline_in": cursor, "timeline_out": cursor+duration,
        "duration": duration, "path": str(dest), "purpose": purpose})
    cursor += duration
    print(clip_id, duration, flush=True)

concat = OUT / "concat.txt"
concat.write_text("\n".join(f"file '{p['id']}.mp4'" for p in manifest["parts"])+"\n", encoding="utf-8")
label = OUT / "source_label.txt"
label.write_text("出典：ニュースの争点（2025-11-05公開）｜会田氏の当時の説明・政策提案", encoding="utf-8")
relative_label = label.relative_to(ROOT).as_posix()
vf = ("scale=1216:684,pad=1280:720:32:36:color=black,"
      "drawtext=fontfile='C\\:/Windows/Fonts/meiryo.ttc':"
      f"textfile='{relative_label}':fontcolor=white:fontsize=20:x=16:y=5")
if not REVIEW.exists():
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-f", "concat",
         "-safe", "0", "-i", str(concat), "-vf", vf, "-r", "30", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
         "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(REVIEW)])
info = probe(REVIEW)
actual = float(info["format"]["duration"])
if abs(actual-cursor)>.2:
    raise RuntimeError(f"Review duration mismatch {actual} vs {cursor}")
run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(REVIEW),
     "-f", "null", "-"])
manifest["technical_checks"] = {"full_decode": "passed", "duration_seconds": actual,
    "expected_seconds": cursor, "streams": [{k: s.get(k) for k in
    ["codec_type", "codec_name", "width", "height", "r_frame_rate", "sample_rate", "channels"]}
    for s in info["streams"]]}
META.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print("REVIEW", REVIEW, actual, flush=True)
