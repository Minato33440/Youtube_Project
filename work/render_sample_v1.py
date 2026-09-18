#!/usr/bin/env python3
"""Render the sample_v1 review cut from its JSON timeline.

This is deliberately a small, reproducible FFmpeg driver.  It creates only its
own intermediates, manifests and final export; it never changes supplied media.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any


FPS_DEFAULT = 30
SAMPLE_RATE = 48_000
THREADS = 4
TOOL_NAME = "render_sample_v1.py"


def die(message: str) -> None:
    raise RuntimeError(message)


def run(command: list[str], label: str) -> subprocess.CompletedProcess[str]:
    print(f"[{label}] {' '.join(command[:3])} ...", flush=True)
    result = subprocess.run(command, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=False)
    if result.returncode:
        print(result.stderr, file=sys.stderr)
        die(f"{label} failed (ffmpeg exit {result.returncode})")
    return result


def probe(path: Path) -> dict[str, Any]:
    result = run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                  "-of", "json", str(path)], f"probe {path.name}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        die(f"ffprobe returned invalid JSON for {path}: {exc}")


def duration_of(path: Path) -> float:
    data = probe(path)
    try:
        return float(data["format"]["duration"])
    except (KeyError, TypeError, ValueError):
        die(f"could not measure duration of {path}")


def file_stat(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def frame_count(seconds: float, fps: int) -> int:
    # Half-up avoids Python's banker's rounding at an exact half-frame.
    return max(1, int(math.floor(seconds * fps + 0.5)))


def ff_time(frames: int, fps: int) -> str:
    return f"{frames / fps:.9f}"


def filter_file(path: Path) -> str:
    """Escape an absolute Windows path for FFmpeg's filter option parser."""
    value = path.resolve().as_posix()
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def concat_quote(path: Path) -> str:
    return path.resolve().as_posix().replace("'", r"'\\''")


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def text_file(path: Path, value: str) -> Path:
    path.write_text(value + "\n", encoding="utf-8")
    return path


def media_streams(data: dict[str, Any]) -> list[dict[str, Any]]:
    return list(data.get("streams", []))


def assert_final_format(data: dict[str, Any], width: int, height: int, fps: int) -> dict[str, Any]:
    streams = media_streams(data)
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not video or not audio:
        die("final output does not contain both video and audio streams")
    if int(video.get("width", 0)) != width or int(video.get("height", 0)) != height:
        die("final output resolution differs from specification")
    if video.get("pix_fmt") != "yuv420p":
        die(f"final output pixel format is {video.get('pix_fmt')}, expected yuv420p")
    if video.get("codec_name") != "h264" or audio.get("codec_name") != "aac":
        die("unexpected final codecs")
    if (video.get("r_frame_rate") != f"{fps}/1" or
            abs(float(Fraction(video.get("avg_frame_rate", "0/1"))) - fps) > .001):
        die("unexpected final frame rate")
    if int(audio.get("sample_rate", 0)) != SAMPLE_RATE or int(audio.get("channels", 0)) != 2:
        die("final output audio is not 48 kHz stereo")
    return {"video": video, "audio": audio, "format": data.get("format", {})}


def main() -> int:
    parser = argparse.ArgumentParser(description="Render sample_v1 with FFmpeg.")
    parser.add_argument("--spec", type=Path,
                        default=Path("Politics_Economics/2026-09-09_fiscal_policy/code_edit/sample_v1_spec.json"),
                        help="timeline JSON (default: fiscal-policy sample_v1 spec)")
    args = parser.parse_args()
    spec_path = args.spec.resolve()
    if not spec_path.is_file():
        die(f"spec does not exist: {spec_path}")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    required = {"version", "width", "height", "fps", "output", "segments"}
    missing = required - set(spec)
    if missing or spec.get("version") != "sample_v1":
        die(f"invalid sample_v1 spec; missing={sorted(missing)} version={spec.get('version')!r}")
    if not isinstance(spec["segments"], list) or not spec["segments"]:
        die("spec must contain at least one segment")

    root = spec_path.parent.parent
    width, height, fps = int(spec["width"]), int(spec["height"]), int(spec["fps"])
    if (width, height, fps) != (1920, 1080, FPS_DEFAULT):
        die("sample_v1 renderer requires 1920x1080 at 30 fps")
    output = (root / spec["output"]).resolve()
    state_dir = root / "code_edit" / "sample_v1"
    rendered_dir = root / "media" / "sample_v1" / "rendered"
    manifest_path = state_dir / "render_manifest.json"
    timeline_path = state_dir / "timeline.csv"
    rendered_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    # Do not claim ownership of a file merely because it has our requested name.
    if output.exists():
        if not manifest_path.is_file():
            die(f"refusing to overwrite existing output without own manifest: {output}")
        try:
            old_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            die(f"refusing to overwrite output; manifest is unreadable: {manifest_path}")
        if (old_manifest.get("created_by") != TOOL_NAME or
                old_manifest.get("output") != str(output)):
            die(f"refusing to overwrite output not owned by this renderer: {output}")

    rows: list[dict[str, Any]] = []
    rendered: list[Path] = []
    for index, segment in enumerate(spec["segments"], start=1):
        kind = segment.get("type")
        segment_id = str(segment.get("id", ""))
        if not segment_id or kind not in {"video", "narration"}:
            die(f"segment {index} needs a non-empty id and type video or narration")
        intermediate = rendered_dir / f"{segment_id}.mkv"
        sidecar = rendered_dir / f"{segment_id}.manifest.json"
        chapter = str(segment.get("chapter", ""))
        if kind == "video":
            for key in ("source", "source_in", "source_out", "source_label"):
                if key not in segment:
                    die(f"video segment {segment_id} missing {key}")
            source = (root / str(segment["source"])).resolve()
            source_in, source_out = float(segment["source_in"]), float(segment["source_out"])
            if not source.is_file() or source_in < 0 or source_out <= source_in:
                die(f"video segment {segment_id} has invalid source or range")
            measured = source_out - source_in
            inputs = {"source": str(source), "source_stat": file_stat(source)}
        else:
            for key in ("wav", "card", "text"):
                if key not in segment:
                    die(f"narration segment {segment_id} missing {key}")
            wav, card = (root / str(segment["wav"])).resolve(), (root / str(segment["card"])).resolve()
            if not wav.is_file() or not card.is_file():
                die(f"narration segment {segment_id} has missing WAV or card")
            subtitle = None
            if "subtitles" in segment:
                subtitle = (root / str(segment["subtitles"])).resolve()
                if not subtitle.is_file():
                    die(f"narration segment {segment_id} has missing subtitle file")
            measured = duration_of(wav) + 0.35
            inputs = {"wav": str(wav), "wav_stat": file_stat(wav), "card": str(card), "card_stat": file_stat(card)}
            if subtitle:
                inputs["subtitles"] = str(subtitle)
                inputs["subtitles_stat"] = file_stat(subtitle)
        frames = frame_count(measured, fps)
        exact_duration = frames / fps
        fingerprint = hashlib.sha256(json.dumps({
            "renderer": 3 if kind == "video" else 2, "segment": segment, "inputs": inputs,
            "width": width, "height": height, "fps": fps,
            "audio": {"loudnorm": "I=-18:TP=-2:LRA=11", "rate": SAMPLE_RATE, "channels": 2},
        }, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        reusable = False
        if intermediate.is_file() and sidecar.is_file():
            try:
                reusable = json.loads(sidecar.read_text(encoding="utf-8")).get("fingerprint") == fingerprint
            except json.JSONDecodeError:
                reusable = False
        if reusable:
            print(f"[{index}/{len(spec['segments'])}] reuse {segment_id}: {frames} frames", flush=True)
        else:
            print(f"[{index}/{len(spec['segments'])}] render {segment_id}: {frames} frames", flush=True)
            segment_tmp = intermediate.with_suffix(".mkv.tmp")
            if segment_tmp.exists():
                segment_tmp.unlink()
            duration = ff_time(frames, fps)
            audio = ("aresample=48000,loudnorm=I=-18:TP=-2:LRA=11,apad,"
                     f"atrim=duration={duration},asetpts=PTS-STARTPTS,"
                     "aformat=sample_rates=48000:channel_layouts=stereo[a]")
            if kind == "video":
                header_file = rendered_dir / f"{segment_id}.header.ass"
                header_file.write_text(
                    "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n"
                    "[V4+ Styles]\n"
                    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                    "Style: Default,Meiryo,32,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1\n"
                    "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                    f"Dialogue: 0,0:00:00.00,1:00:00.00,Default,,0,0,0,,{{\\an7\\pos(64,2)}}{chapter}\n"
                    f"Dialogue: 0,0:00:00.00,1:00:00.00,Default,,0,0,0,,{{\\an7\\pos(64,40)\\fs22}}{segment['source_label']}\n",
                    encoding="utf-8-sig")
                video = ("[0:v]setpts=PTS-STARTPTS,"
                         "scale=1792:1008:force_original_aspect_ratio=decrease,"
                         "pad=1920:1080:64:72:color=black,"
                         f"subtitles=filename='{filter_file(header_file)}',"
                         f"fps={fps},tpad=stop_mode=clone:stop_duration=0.1,trim=end_frame={frames},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[v]")
                command = ["ffmpeg", "-hide_banner", "-y", "-threads", str(THREADS), "-ss", str(source_in), "-t", str(measured), "-i", str(source),
                           "-filter_complex_threads", "2", "-filter_complex", video + ";[0:a]asetpts=PTS-STARTPTS," + audio, "-map", "[v]", "-map", "[a]",
                           "-c:v", "libx264", "-threads", str(THREADS), "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-c:a", "pcm_s16le", "-ar", str(SAMPLE_RATE), "-ac", "2", "-shortest", "-f", "matroska", str(segment_tmp)]
            else:
                subtitle_filter = ""
                if subtitle:
                    # ASS is intentionally passed through as authored: the timeline owns
                    # caption positions and styling for the card's reserved lower area.
                    subtitle_filter = f",subtitles=filename='{filter_file(subtitle)}'"
                video = (f"[0:v]trim=end_frame={frames},setpts=PTS-STARTPTS"
                         f"{subtitle_filter},format=yuv420p[v]")
                command = ["ffmpeg", "-hide_banner", "-y", "-threads", str(THREADS), "-loop", "1", "-framerate", str(fps),
                           "-i", str(card), "-i", str(wav), "-filter_complex_threads", "2", "-filter_complex", video + ";[1:a]" + audio,
                           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-threads", str(THREADS), "-preset", "veryfast", "-crf", "20",
                           "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-ar", str(SAMPLE_RATE), "-ac", "2",
                           "-shortest", "-f", "matroska", str(segment_tmp)]
            run(command, f"render {segment_id}")
            os.replace(segment_tmp, intermediate)
            atomic_json(sidecar, {"created_by": TOOL_NAME, "fingerprint": fingerprint, "inputs": inputs,
                                  "frames": frames, "duration_seconds": exact_duration})
        rendered.append(intermediate)
        cumulative_frames = sum(int(row["planned_frames"]) for row in rows)
        rows.append({"sequence": index, "id": segment_id, "type": kind, "chapter": chapter,
                     "timeline_in": cumulative_frames / fps, "timeline_out": (cumulative_frames + frames) / fps,
                     "source": inputs.get("source", inputs.get("wav")),
                     "source_in": segment.get("source_in", ""), "source_out": segment.get("source_out", ""),
                     "measured_seconds": f"{measured:.9f}", "planned_frames": frames,
                     "planned_seconds": f"{exact_duration:.9f}", "intermediate": str(intermediate)})

    with timeline_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    concat_list = state_dir / "concat_sample_v1.txt"
    concat_list.write_text("".join(f"file '{concat_quote(path)}'\n" for path in rendered), encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output_tmp = output.with_suffix(".mp4.tmp")
    if output_tmp.exists():
        output_tmp.unlink()
    run(["ffmpeg", "-hide_banner", "-y", "-threads", str(THREADS), "-f", "concat", "-safe", "0", "-i", str(concat_list),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-f", "mp4", str(output_tmp)], "concat")
    final_probe = probe(output_tmp)
    format_info = assert_final_format(final_probe, width, height, fps)
    planned_frames = sum(int(row["planned_frames"]) for row in rows)
    if int(format_info["video"].get("nb_frames", 0)) != planned_frames:
        die("final video frame count differs from timeline")
    planned_duration = planned_frames / fps
    actual_duration = float(final_probe["format"]["duration"])
    if abs(actual_duration - planned_duration) > (1 / fps + 0.001):
        die(f"final duration {actual_duration:.6f}s differs from planned {planned_duration:.6f}s by over one frame")
    run(["ffmpeg", "-v", "error", "-xerror", "-i", str(output_tmp), "-map", "0", "-f", "null", "-"], "decode validation")
    os.replace(output_tmp, output)
    manifest = {"created_by": TOOL_NAME, "status": "technical_validation_passed",
                "generated_at_utc": datetime.now(timezone.utc).isoformat(), "spec": str(spec_path), "output": str(output),
                "format": {"width": width, "height": height, "fps": fps, "pixel_format": "yuv420p",
                           "intermediate_audio": "pcm_s16le 48000 Hz stereo", "final_audio": "aac 192k 48000 Hz stereo"},
                "audio_filter": "loudnorm=I=-18:TP=-2:LRA=11, apad, atrim to frame-rounded duration",
                "timeline_csv": str(timeline_path), "planned_frames": planned_frames,
                "planned_duration_seconds": planned_duration, "actual_duration_seconds": actual_duration,
                "duration_tolerance_seconds": 1 / fps, "streams": format_info, "segments": rows,
                "verification": {"ffprobe": "passed", "full_stream_decode": "passed",
                                 "listening": "not performed by this script", "content_review": "not performed by this script"}}
    atomic_json(manifest_path, manifest)
    print(f"DONE: {output} ({actual_duration:.3f}s, {planned_frames} frames)", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
