"""Pixel-level display diagnosis for the preserved today-baseline regression failure."""
from pathlib import Path
import json
import os
import tempfile

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import numpy as np
from PIL import Image, ImageDraw
import live2d.v3 as live2d
from OpenGL.GL import glReadPixels, GL_RGBA, GL_UNSIGNED_BYTE, glFinish

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'preview'
SIZE = (1200, 1800)
FPS = 30
DEFAULTS = {'ParamEyeLOpen': 1, 'ParamEyeROpen': 1, 'ParamMouthOpenY': 0,
            'ParamAngleX': 0, 'ParamAngleY': 0, 'ParamAngleZ': 0,
            'ParamHairFront': 0, 'ParamHairSide': 0, 'ParamHairBack': 0}


def main():
    pygame.display.init()
    live2d.init()
    pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)
    pygame.display.set_mode(SIZE, pygame.OPENGL | pygame.DOUBLEBUF | pygame.HIDDEN)
    live2d.glInit()
    models = []

    def load_static(path):
        config = json.loads(path.read_text(encoding='utf-8'))
        config['FileReferences'].pop('Physics', None)
        with tempfile.TemporaryDirectory(prefix='ren-rig-diagnose-') as temp:
            for key in ('Moc', 'DisplayInfo'):
                if key in config['FileReferences']:
                    config['FileReferences'][key] = os.path.relpath(path.parent / config['FileReferences'][key], temp).replace('\\', '/')
            config['FileReferences']['Textures'] = [os.path.relpath(path.parent / p, temp).replace('\\', '/') for p in config['FileReferences']['Textures']]
            fixture = Path(temp) / 'no_physics.model3.json'
            fixture.write_text(json.dumps(config), encoding='utf-8')
            model = live2d.LAppModel()
            model.LoadModelJson(str(fixture))
        model.Resize(*SIZE)
        model.SetAutoBlinkEnable(False)
        model.SetAutoBreathEnable(False)
        models.append(model)
        return model

    def raw_render(values, target):
        pygame.event.pump()
        for param, value in (DEFAULTS | values).items():
            target.SetParameterValue(param, float(value))
        target._model.Update(1 / FPS)
        live2d.clearBuffer(0, 0, 0, 0)
        target.Draw()
        glFinish()
        rgba = np.frombuffer(glReadPixels(0, 0, *SIZE, GL_RGBA, GL_UNSIGNED_BYTE), np.uint8).reshape(SIZE[1], SIZE[0], 4).copy()
        return rgba[::-1].copy()

    def unpremultiply(raw):
        result = raw.copy()
        alpha = raw[:, :, 3:4].astype(np.float32)
        result[:, :, :3] = np.clip(np.rint(raw[:, :, :3].astype(np.float32) * 255 / np.maximum(alpha, 1)), 0, 255)
        return result

    def composite(raw, background):
        alpha = raw[:, :, 3:4].astype(np.float32) / 255
        return np.clip(np.rint(raw[:, :, :3].astype(np.float32) + np.asarray(background, dtype=np.float32) * (1 - alpha)), 0, 255).astype(np.uint8)

    def pixel_records(current_raw, before_raw, current_display, before_display, threshold=8):
        delta = np.abs(current_display.astype(np.int16) - before_display.astype(np.int16))
        ys, xs = np.where(delta.max(axis=2) > threshold)
        records = []
        for y, x in zip(ys[:100], xs[:100]):
            records.append({'full_canvas_xy': [int(x), int(y)], 'case_crop_xy': [int(x - 390), int(y)] if 390 <= x < 810 and y < 570 else None,
                            'current_raw_rgba': current_raw[y, x].tolist(), 'before_raw_rgba': before_raw[y, x].tolist(),
                            'current_display_rgba': current_display[y, x].tolist(), 'before_display_rgba': before_display[y, x].tolist(),
                            'display_abs_delta_rgba': delta[y, x].tolist()})
        return records

    def composite_records(current_raw, before_raw, background, threshold=2):
        current = composite(current_raw, background)
        before = composite(before_raw, background)
        delta = np.abs(current.astype(np.int16) - before.astype(np.int16))
        ys, xs = np.where(delta.max(axis=2) > threshold)
        records = []
        for y, x in zip(ys[:100], xs[:100]):
            records.append({'full_canvas_xy': [int(x), int(y)], 'case_crop_xy': [int(x - 390), int(y)] if 390 <= x < 810 and y < 570 else None,
                            'current_composited_rgb': current[y, x].tolist(), 'before_composited_rgb': before[y, x].tolist(),
                            'composited_abs_delta_rgb': delta[y, x].tolist(),
                            'current_raw_rgba': current_raw[y, x].tolist(), 'before_raw_rgba': before_raw[y, x].tolist()})
        return records

    def save_exception_enlargement(current_raw, before_raw):
        background = [234, 228, 218]
        current, before = composite(current_raw, background), composite(before_raw, background)
        diff = np.abs(current.astype(np.int16) - before.astype(np.int16)).astype(np.uint8)
        y, x = np.unravel_index(np.argmax(diff.max(axis=2)), diff.shape[:2])
        box = (max(0, x - 10), max(0, y - 10), min(SIZE[0], x + 11), min(SIZE[1], y + 11))
        panels = []
        for source, label in ((before, 'Before'), (current, 'Current'), (diff * 80, 'Abs diff x80')):
            crop = Image.fromarray(source).crop(box).resize((420, 420), Image.Resampling.NEAREST)
            ImageDraw.Draw(crop).rectangle(((x - box[0]) * 20, (y - box[1]) * 20, (x - box[0] + 1) * 20 - 1, (y - box[1] + 1) * 20 - 1), outline='red', width=2)
            panels.append((crop, label))
        sheet = Image.new('RGB', (1260, 460), 'white')
        for index, (panel, label) in enumerate(panels):
            sheet.paste(panel, (index * 420, 40))
            ImageDraw.Draw(sheet).text((10 + index * 420, 10), label, fill='black')
        sheet.save(OUT / 'today_baseline_x0_y-6_blink_aa_exception_20x.png')

    try:
        current = load_static(ROOT / 'runtime/Ren_front.model3.json')
        before = load_static(ROOT / 'archive/before_tilted_reference_20260926/runtime/Ren_front.model3.json')
        cases = [('Neutral', {}), ('X0 Y-30', {'ParamAngleY': -30}), ('X0 Y-15', {'ParamAngleY': -15}),
                 ('X0 Y0', {}), ('X0 Y+6', {'ParamAngleY': 6}), ('X0 Y+21', {'ParamAngleY': 21}),
                 ('X0 Y-6 Blink', {'ParamAngleY': -6, 'ParamEyeLOpen': 0, 'ParamEyeROpen': 0}),
                 ('Tilt -', {'ParamAngleZ': -30}), ('Tilt +', {'ParamAngleZ': 30})]
        results = []
        for name, values in cases:
            current_raw, before_raw = raw_render(values, current), raw_render(values, before)
            current_display, before_display = unpremultiply(current_raw), unpremultiply(before_raw)
            display_delta = np.abs(current_display.astype(np.int16) - before_display.astype(np.int16))
            backgrounds = {}
            for background_name, background in [('white', [255, 255, 255]), ('review_gray', [234, 228, 218])]:
                display_current, display_before = composite(current_raw, background), composite(before_raw, background)
                diff = np.abs(display_current.astype(np.int16) - display_before.astype(np.int16))
                backgrounds[background_name] = {'max_rgb_delta': int(diff.max()), 'pixels_over_8': int(np.count_nonzero(diff.max(axis=2) > 8))}
            results.append({'case': name, 'requested': values,
                            'raw_rgba_max_delta': int(np.abs(current_raw.astype(np.int16) - before_raw.astype(np.int16)).max()),
                            'unpremultiplied_rgba_max_delta': int(display_delta.max()),
                            'unpremultiplied_pixels_over_8': int(np.count_nonzero(display_delta.max(axis=2) > 8)),
                            'background_composite_rgb': backgrounds,
                            'pixels_over_8': pixel_records(current_raw, before_raw, current_display, before_display),
                            'white_composite_pixels_over_2': composite_records(current_raw, before_raw, [255, 255, 255]),
                            'review_gray_composite_pixels_over_2': composite_records(current_raw, before_raw, [234, 228, 218])})
            if name == 'X0 Y-6 Blink':
                save_exception_enlargement(current_raw, before_raw)
        report = {'status': 'diagnostic-only',
                  'raw_readback': 'OpenGL RGBA readback after Cubism draw; RGB is treated as premultiplied by the existing preview pipeline.',
                  'vertex_diagnosis': {'available': False, 'reason': 'Installed live2d.v3 Python wrapper exposes drawable IDs but no public drawable vertex-position API.'},
                  'cases': results}
        (OUT / 'today_baseline_pixel_diagnosis.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'cases': len(results), 'pixels_over_8': {x['case']: x['unpremultiplied_pixels_over_8'] for x in results}}, indent=2))
    finally:
        for model in models:
            model.DestroyRenderer()
        live2d.dispose()
        pygame.quit()


if __name__ == '__main__':
    main()
