"""Render deterministic Base Motion review assets from the exported SDK model.

Run only after Cubism exports runtime/Ren_base.model3.json and its referenced
files. This script never edits the CMO3 or source artwork.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import live2d.v3 as live2d
import numpy as np
from OpenGL.GL import GL_RGBA, GL_UNSIGNED_BYTE, glFinish, glReadPixels
from PIL import Image, ImageDraw, ImageFont
import pygame


ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "runtime/Ren_base.model3.json"
OUT = ROOT / "preview"
SIZE = (1200, 1800)
FPS = 30
CROP = (390, 0, 810, 570)
DEFAULTS = {
    "ParamEyeLOpen": 1,
    "ParamEyeROpen": 1,
    "ParamMouthOpenY": 0,
    "ParamAngleX": 0,
    "ParamAngleY": 0,
    "ParamAngleZ": 0,
    "ParamHairFront": 0,
    "ParamHairSide": 0,
    "ParamHairBack": 0,
    "Param": 0,
}
PHYSICS_OUTPUTS = (
    "ParamHairFront",
    "Param",
    "ParamHairSide",
    "ParamHairBack",
)


def main() -> None:
    if not MODEL.exists():
        raise FileNotFoundError(
            "Export the Cubism model to base_motion/runtime/Ren_base.model3.json first."
        )
    OUT.mkdir(parents=True, exist_ok=True)
    pygame.display.init()
    live2d.init()
    pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)
    pygame.display.set_mode(SIZE, pygame.OPENGL | pygame.DOUBLEBUF | pygame.HIDDEN)
    live2d.glInit()
    models = []

    def load(path: Path):
        model = live2d.LAppModel()
        model.LoadModelJson(str(path))
        model.Resize(*SIZE)
        model.SetAutoBlinkEnable(False)
        model.SetAutoBreathEnable(False)
        models.append(model)
        return model

    model = load(MODEL)
    config = json.loads(MODEL.read_text(encoding="utf-8-sig"))
    config["FileReferences"].pop("Physics", None)
    with tempfile.TemporaryDirectory(prefix="ren-base-no-physics-") as temp_name:
        temp = Path(temp_name)
        refs = config["FileReferences"]
        for key in ("Moc", "DisplayInfo"):
            if key in refs:
                refs[key] = os.path.relpath(MODEL.parent / refs[key], temp).replace(
                    "\\", "/"
                )
        refs["Textures"] = [
            os.path.relpath(MODEL.parent / path, temp).replace("\\", "/")
            for path in refs["Textures"]
        ]
        fixture = temp / "Ren_base_no_physics.model3.json"
        fixture.write_text(json.dumps(config), encoding="utf-8")
        static_model = load(fixture)

    parameter_ids = model.GetParamIds()
    assert set(DEFAULTS) <= set(parameter_ids)
    assert len(model.GetDrawableIds()) == 46
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    report = {
        "source": str(MODEL),
        "drawable_count": len(model.GetDrawableIds()),
        "parameter_ids": parameter_ids,
        "cases": [],
    }

    def actual(target, names=DEFAULTS):
        ids = target.GetParamIds()
        return {name: float(target.GetParameterValue(ids.index(name))) for name in names}

    def render(values: dict, target=static_model) -> Image.Image:
        pygame.event.pump()
        for parameter, value in (DEFAULTS | values).items():
            target.SetParameterValue(parameter, float(value))
        target._model.Update(1 / FPS)
        live2d.clearBuffer(0, 0, 0, 0)
        target.Draw()
        glFinish()
        rgba = np.frombuffer(
            glReadPixels(0, 0, *SIZE, GL_RGBA, GL_UNSIGNED_BYTE), np.uint8
        ).reshape(SIZE[1], SIZE[0], 4).copy()
        alpha = rgba[:, :, 3:4].astype(np.float32)
        rgba[:, :, :3] = np.clip(
            np.rint(rgba[:, :, :3].astype(np.float32) * 255 / np.maximum(alpha, 1)),
            0,
            255,
        )
        return Image.fromarray(rgba).transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    def tile(image: Image.Image, label: str) -> Image.Image:
        background = Image.new("RGBA", (420, 570), (234, 228, 218, 255))
        background.alpha_composite(image.crop(CROP))
        result = Image.new("RGB", (420, 608), (244, 241, 236))
        result.paste(background.convert("RGB"), (0, 38))
        ImageDraw.Draw(result).text((10, 10), label, fill=(30, 35, 43), font=font)
        return result

    try:
        neutral = render({})
        neutral.save(OUT / "neutral_full.png")
        cases = [
            ("Neutral", {}),
            ("Blink left", {"ParamEyeLOpen": 0}),
            ("Blink right", {"ParamEyeROpen": 0}),
            ("Blink both", {"ParamEyeLOpen": 0, "ParamEyeROpen": 0}),
            ("Mouth / jaw 0.5", {"ParamMouthOpenY": 0.5}),
            ("Mouth / jaw 1.0", {"ParamMouthOpenY": 1}),
            ("Z -30", {"ParamAngleZ": -30}),
            ("Z +30", {"ParamAngleZ": 30}),
            ("Side hair -1", {"ParamHairSide": -1}),
            ("Side hair +1", {"ParamHairSide": 1}),
            ("Back hair -1", {"ParamHairBack": -1}),
            ("Back hair +1", {"ParamHairBack": 1}),
            ("Z + blink", {"ParamAngleZ": 30, "ParamEyeLOpen": 0, "ParamEyeROpen": 0}),
            ("Z + speech", {"ParamAngleZ": -30, "ParamMouthOpenY": 0.7}),
            (
                "Combined",
                {
                    "ParamAngleZ": 20,
                    "ParamMouthOpenY": 0.6,
                    "ParamHairFront": 0.5,
                    "ParamHairSide": -0.5,
                    "ParamHairBack": 0.5,
                },
            ),
        ]
        sheet = Image.new(
            "RGB",
            (420 * 4, 608 * math.ceil(len(cases) / 4)),
            (244, 241, 236),
        )
        neutral_array = np.asarray(neutral).astype(np.int16)
        for index, (label, values) in enumerate(cases):
            image = render(values)
            image.crop(CROP).save(OUT / f"case_{index:02d}.png")
            sheet.paste(tile(image, label), (index % 4 * 420, index // 4 * 608))
            difference = np.max(
                np.abs(np.asarray(image).astype(np.int16) - neutral_array), axis=2
            )
            report["cases"].append(
                {
                    "label": label,
                    "requested": values,
                    "actual": actual(static_model),
                    "changed_pixels_over_8": int(np.count_nonzero(difference > 8)),
                }
            )
        sheet.save(OUT / "base_motion_review.jpg", quality=95)

        curve = []
        video_path = OUT / "Ren_base_motion.mp4"
        ffmpeg = subprocess.Popen(
            [
                "ffmpeg", "-y", "-nostdin", "-v", "error",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "420x608",
                "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
                "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(video_path),
            ],
            stdin=subprocess.PIPE,
        )
        for frame_number in range(FPS * 12):
            time = frame_number / FPS
            angle_z = 26 * math.sin(2 * math.pi * time / 6)
            eye = min(1.0, *(abs(time - center) / 0.18 for center in (1.1, 4.4, 7.3, 10.8)))
            mouth = 0.65 * max(0, math.sin(2 * math.pi * time / 0.85)) if 2 < time < 10 else 0
            values = {
                "ParamAngleZ": angle_z,
                "ParamEyeLOpen": eye,
                "ParamEyeROpen": eye,
                "ParamMouthOpenY": mouth,
            }
            frame = tile(render(values, model), f"Z {angle_z:+.0f}  Mouth {mouth:.2f}  Hair: physics")
            ffmpeg.stdin.write(frame.tobytes())
            curve.append({"time": time, "input": values, "actual": actual(model)})
        ffmpeg.stdin.close()
        if ffmpeg.wait() != 0:
            raise RuntimeError("ffmpeg failed while writing the Base Motion preview")
        subprocess.run(
            [
                "ffmpeg", "-y", "-nostdin", "-v", "error", "-i", str(video_path),
                "-filter_complex",
                "[0:v]fps=15,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a",
                "-loop", "0", str(OUT / "Ren_base_motion.gif"),
            ],
            check=True,
        )
        report["frames"] = len(curve)
        report["fps"] = FPS
        report["duration_seconds"] = 12
        report["physics_ranges"] = {
            parameter: [
                min(frame["actual"][parameter] for frame in curve),
                max(frame["actual"][parameter] for frame in curve),
            ]
            for parameter in PHYSICS_OUTPUTS
        }
        for parameter in ("ParamHairFront", "ParamHairSide", "ParamHairBack"):
            low, high = report["physics_ranges"][parameter]
            assert high - low > 0.05, (parameter, low, high)
        report["ahoge_limit"] = (
            "Param is preserved and measured, but the current ahoge keyforms are a known no-op "
            "until Boss rebuilds the shape."
        )
        report["runtime_hashes"] = {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (ROOT / "runtime").rglob("*")
            if path.is_file()
        }
        (OUT / "parameter_curve.json").write_text(
            json.dumps(curve, ensure_ascii=False), encoding="utf-8"
        )
        (OUT / "render_verification.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print("PREVIEW_COMPLETE", OUT)
    finally:
        for loaded_model in models:
            loaded_model.DestroyRenderer()
        live2d.dispose()
        pygame.quit()


if __name__ == "__main__":
    main()
