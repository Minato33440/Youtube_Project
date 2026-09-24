"""Render and inspect the actual exported rig, without altering source artwork."""
from pathlib import Path
import os
import json
import math
import hashlib
import subprocess
import tempfile
import faulthandler
faulthandler.enable()
faulthandler.dump_traceback_later(45, repeat=True)

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import live2d.v3 as live2d
from OpenGL.GL import glReadPixels, GL_RGBA, GL_UNSIGNED_BYTE, glFinish

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / 'runtime/Ren_front.model3.json'
OUT = ROOT / 'preview'
SIZE = (1200, 1800)
FPS = 30
CROP = (390, 0, 810, 570)
DEFAULTS = {
    'ParamEyeLOpen': 1, 'ParamEyeROpen': 1, 'ParamMouthOpenY': 0,
    'ParamAngleX': 0, 'ParamAngleY': 0, 'ParamAngleZ': 0,
    'ParamHairFront': 0, 'ParamHairSide': 0, 'ParamHairBack': 0,
}


def main():
    if not MODEL.exists():
        raise FileNotFoundError('Export the working Cubism model to runtime first.')
    OUT.mkdir(exist_ok=True)
    print('INIT', flush=True)
    pygame.display.init()
    print('DISPLAY_INIT', flush=True)
    live2d.init()
    pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)
    pygame.display.set_mode(SIZE, pygame.OPENGL | pygame.DOUBLEBUF | pygame.HIDDEN)
    print('GL_INIT', flush=True)
    live2d.glInit()
    models = []
    def load(path):
        print('LOAD', path, flush=True)
        m = live2d.LAppModel()
        m.LoadModelJson(str(path))
        print('LOADED', flush=True)
        m.Resize(*SIZE)
        m.SetAutoBlinkEnable(False)
        m.SetAutoBreathEnable(False)
        models.append(m)
        return m
    model = load(MODEL)
    config = json.loads(MODEL.read_text(encoding='utf-8'))
    config['FileReferences'].pop('Physics')
    with tempfile.TemporaryDirectory(prefix='ren-rig-check-') as temp:
        for key in ('Moc', 'DisplayInfo'):
            if key in config['FileReferences']:
                config['FileReferences'][key] = os.path.relpath(MODEL.parent / config['FileReferences'][key], temp).replace('\\', '/')
        config['FileReferences']['Textures'] = [os.path.relpath(MODEL.parent / p, temp).replace('\\', '/') for p in config['FileReferences']['Textures']]
        fixture = Path(temp) / 'no_physics.model3.json'
        fixture.write_text(json.dumps(config), encoding='utf-8')
        static_model = load(fixture)
    baseline = load(ROOT.parent / 'basic_expression/runtime/Ren_front.model3.json')
    ids = model.GetParamIds()
    assert set(DEFAULTS) <= set(ids)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
    report = {'source': 'Actual exported moc3 rendering', 'cases': [],
              'drawable_count': len(model.GetDrawableIds()), 'parameter_ids': ids}

    def render(values, target=static_model):
        pygame.event.pump()
        for p, v in (DEFAULTS | values).items():
            target.SetParameterValue(p, float(v))
        target._model.Update(1 / FPS)
        live2d.clearBuffer(0, 0, 0, 0)
        target.Draw()
        glFinish()
        rgba = np.frombuffer(glReadPixels(0, 0, *SIZE, GL_RGBA, GL_UNSIGNED_BYTE),
                             np.uint8).reshape(SIZE[1], SIZE[0], 4).copy()
        alpha = rgba[:, :, 3:4].astype(np.float32)
        rgba[:, :, :3] = np.clip(np.rint(rgba[:, :, :3].astype(np.float32)
                                       * 255 / np.maximum(alpha, 1)), 0, 255)
        return Image.fromarray(rgba).transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    def tile(im, label):
        bg = Image.new('RGBA', (420, 570), (234, 228, 218, 255))
        bg.alpha_composite(im.crop(CROP))
        result = Image.new('RGB', (420, 608), (244, 241, 236))
        result.paste(bg.convert('RGB'), (0, 38))
        ImageDraw.Draw(result).text((10, 10), label, fill=(30, 35, 43), font=font)
        return result

    try:
        neutral = render({})
        neutral.save(OUT / 'neutral_full.png')
        old_neutral = render({}, baseline)
        old_neutral.save(OUT / 'baseline_neutral.png')
        ndiff = np.abs(np.asarray(neutral).astype(np.int16)-np.asarray(old_neutral).astype(np.int16))
        report['neutral_vs_approved'] = {'max_channel_difference': int(ndiff.max()),
                                        'pixels_over_8': int(np.count_nonzero(ndiff.max(axis=2)>8))}
        cases = [('Neutral', {}), ('Mouth / jaw 0.5', {'ParamMouthOpenY': .5}),
                 ('Mouth / jaw 1.0', {'ParamMouthOpenY': 1})]
        for param, label in [('ParamAngleZ', 'Tilt'),
                             ('ParamHairFront', 'Front hair'),
                             ('ParamHairSide', 'Side hair'),
                             ('ParamHairBack', 'Back hair')]:
            span = 30 if param.startswith('ParamAngle') else 1
            cases.extend([(f'{label} -', {param: -span}),
                          (f'{label} +', {param: span})])
        cases.extend([
            ('Tilt + blink', {'ParamAngleZ': 30, 'ParamEyeLOpen': 0, 'ParamEyeROpen': 0}),
            ('Tilt + speech', {'ParamAngleZ': -30, 'ParamMouthOpenY': .7}),
            ('Combined', {'ParamAngleZ': 20,
                          'ParamMouthOpenY': .6, 'ParamHairFront': .5,
                          'ParamHairSide': -.5, 'ParamHairBack': .5}),
        ])
        sheet = Image.new('RGB', (420 * 4, 608 * math.ceil(len(cases) / 4)), (244, 241, 236))
        neutral_array = np.asarray(neutral).astype(np.int16)
        for i, (label, values) in enumerate(cases):
            im = render(values)
            im.crop(CROP).save(OUT / f'case_{i:02d}.png')
            sheet.paste(tile(im, label), (i % 4 * 420, i // 4 * 608))
            diff = np.max(np.abs(np.asarray(im).astype(np.int16) - neutral_array), axis=2)
            report['cases'].append({'label': label, 'requested': values,
                                    'actual': {p: float(static_model.GetParameterValue(ids.index(p)))
                                               for p in DEFAULTS},
                                    'changed_pixels_over_8': int(np.count_nonzero(diff > 8))})
        sheet.save(OUT / 'head_neck_hair_review.jpg', quality=95)
        comparison = Image.new('RGB', (840, 608), (244, 241, 236))
        comparison.paste(tile(old_neutral, 'Approved baseline'), (0, 0))
        comparison.paste(tile(neutral, 'Current neutral'), (420, 0))
        comparison.save(OUT / 'neutral_comparison.jpg', quality=95)
        curve = []
        ff = subprocess.Popen(['ffmpeg', '-y', '-nostdin', '-v', 'error', '-f', 'rawvideo',
                               '-pix_fmt', 'rgb24', '-s', '420x608', '-r', str(FPS), '-i', '-',
                               '-an', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
                               '-movflags', '+faststart', str(OUT / 'Ren_head_neck_hair.mp4')],
                              stdin=subprocess.PIPE)
        for f in range(FPS * 12):
            t = f / FPS
            z = 26 * math.sin(2 * math.pi * t / 6)
            eye = min(1., *(abs(t - c) / .18 for c in (1.1, 4.4, 7.3, 10.8)))
            mouth = .65 * max(0, math.sin(2 * math.pi * t / .85)) if 2 < t < 10 else 0
            vals = {'ParamAngleZ': z,
                    'ParamEyeLOpen': eye, 'ParamEyeROpen': eye, 'ParamMouthOpenY': mouth}
            frame = tile(render(vals, model), f'Tilt {z:+.0f}  Mouth {mouth:.2f}  Hair: physics')
            ff.stdin.write(frame.tobytes())
            curve.append({'time': t, 'input': vals, 'actual': {p: float(model.GetParameterValue(ids.index(p))) for p in DEFAULTS}})
        ff.stdin.close()
        assert ff.wait() == 0
        subprocess.run(['ffmpeg', '-y', '-nostdin', '-v', 'error',
                        '-i', str(OUT / 'Ren_head_neck_hair.mp4'), '-filter_complex',
                        '[0:v]fps=15,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a',
                        '-loop', '0', str(OUT / 'Ren_head_neck_hair.gif')], check=True)
        report.update(frames=360, fps=FPS, duration_seconds=12,
                      preview_input='AngleZ, blink, mouth driven by deterministic curves. Hair outputs generated only by exported Cubism physics.')
        report['physics_ranges'] = {p: [min(f['actual'][p] for f in curve), max(f['actual'][p] for f in curve)] for p in ('ParamHairFront', 'ParamHairSide', 'ParamHairBack')}
        assert all(hi-lo>.05 for lo, hi in report['physics_ranges'].values()), report['physics_ranges']
        assert len(model.GetDrawableIds()) == 48
        report['runtime_hashes'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in (ROOT / 'runtime').rglob('*') if p.is_file()}
        (OUT / 'parameter_curve.json').write_text(json.dumps(curve), encoding='utf-8')
        (OUT / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('PREVIEW_COMPLETE', OUT)
    finally:
        for m in models:
            m.DestroyRenderer()
        live2d.dispose()
        pygame.quit()


if __name__ == '__main__':
    main()
