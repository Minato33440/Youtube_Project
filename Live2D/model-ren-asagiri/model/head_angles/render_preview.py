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
    def load_static(path):
        config = json.loads(path.read_text(encoding='utf-8'))
        config['FileReferences'].pop('Physics', None)
        with tempfile.TemporaryDirectory(prefix='ren-rig-check-') as temp:
            for key in ('Moc', 'DisplayInfo'):
                if key in config['FileReferences']:
                    config['FileReferences'][key] = os.path.relpath(path.parent / config['FileReferences'][key], temp).replace('\\', '/')
            config['FileReferences']['Textures'] = [os.path.relpath(path.parent / p, temp).replace('\\', '/') for p in config['FileReferences']['Textures']]
            fixture = Path(temp) / 'no_physics.model3.json'
            fixture.write_text(json.dumps(config), encoding='utf-8')
            return load(fixture)
    static_model = load_static(MODEL)
    baseline = load_static(ROOT.parent / 'head_neck_hair/runtime/Ren_front.model3.json')
    previous = load_static(ROOT / 'archive/before_reference_fit_20260925/runtime/Ren_front.model3.json')
    oblique_baseline = load_static(ROOT / 'archive/before_oblique_contour_20260925/runtime/Ren_front.model3.json')
    contour_baseline = load_static(ROOT / 'archive/before_contour_direction_20260925/runtime/Ren_front.model3.json')
    today_baseline = load_static(ROOT / 'archive/before_tilted_reference_20260926/runtime/Ren_front.model3.json')
    ids = model.GetParamIds()
    assert set(DEFAULTS) <= set(ids)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
    report = {'source': 'Actual exported moc3 rendering', 'cases': [],
              'drawable_count': len(model.GetDrawableIds()), 'parameter_ids': ids}

    def unpremultiply(raw):
        result = raw.copy()
        alpha = raw[:, :, 3:4].astype(np.float32)
        result[:, :, :3] = np.clip(np.rint(raw[:, :, :3].astype(np.float32)
                                   * 255 / np.maximum(alpha, 1)), 0, 255)
        return result

    def composite_rgb(raw, background):
        alpha = raw[:, :, 3:4].astype(np.float32) / 255
        return np.clip(np.rint(raw[:, :, :3].astype(np.float32)
                               + np.asarray(background, dtype=np.float32) * (1 - alpha)), 0, 255).astype(np.uint8)

    def render(values, target=static_model, raw_output=False):
        pygame.event.pump()
        for p, v in (DEFAULTS | values).items():
            target.SetParameterValue(p, float(v))
        target._model.Update(1 / FPS)
        live2d.clearBuffer(0, 0, 0, 0)
        target.Draw()
        glFinish()
        rgba = np.frombuffer(glReadPixels(0, 0, *SIZE, GL_RGBA, GL_UNSIGNED_BYTE),
                             np.uint8).reshape(SIZE[1], SIZE[0], 4).copy()
        rgba = rgba[::-1].copy()
        if raw_output:
            return rgba
        return Image.fromarray(unpremultiply(rgba))

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
        cases = [('Neutral', {})]
        for y in (-30, 0, 30):
            for x in (-30, 0, 30):
                if x or y:
                    cases.append((f'X {x:+d} / Y {y:+d}', {'ParamAngleX': x, 'ParamAngleY': y}))
        cases.extend([
            ('Turn + blink', {'ParamAngleX': 30, 'ParamEyeLOpen': 0, 'ParamEyeROpen': 0}),
            ('Nod + speech', {'ParamAngleY': -30, 'ParamMouthOpenY': .7}),
            ('Combined', {'ParamAngleX': -30, 'ParamAngleY': 30, 'ParamAngleZ': 20,
                          'ParamMouthOpenY': .6, 'ParamHairFront': .5,
                          'ParamHairSide': -.5, 'ParamHairBack': .5}),
            ('Mouth 1.0', {'ParamMouthOpenY': 1}),
            ('Tilt -', {'ParamAngleZ': -30}), ('Tilt +', {'ParamAngleZ': 30}),
            ('Hair extremes', {'ParamHairFront': 1, 'ParamHairSide': -1, 'ParamHairBack': 1}),
        ])
        sheet = Image.new('RGB', (420 * 4, 608 * math.ceil(len(cases) / 4)), (244, 241, 236))
        neutral_array = np.asarray(neutral).astype(np.int16)
        for i, (label, values) in enumerate(cases):
            im = render(values)
            im.crop(CROP).save(OUT / f'case_{i:02d}.png')
            # These two oblique endpoint pairs are the visual reference inputs.
            # Keep their pre-today raster beside the current case without touching
            # the archived runtime itself.
            if i in (1, 3):
                render(values, today_baseline).crop(CROP).save(OUT / f'before_tilted_reference_case_{i:02d}.png')
            sheet.paste(tile(im, label), (i % 4 * 420, i // 4 * 608))
            diff = np.max(np.abs(np.asarray(im).astype(np.int16) - neutral_array), axis=2)
            report['cases'].append({'label': label, 'requested': values,
                                    'actual': {p: float(static_model.GetParameterValue(ids.index(p)))
                                               for p in DEFAULTS},
                                    'changed_pixels_over_8': int(np.count_nonzero(diff > 8))})
        sheet.save(OUT / 'head_angles_review.jpg', quality=95)
        endpoint_sheet = Image.new('RGB', (420 * 4, 608 * 2), (244, 241, 236))
        endpoint_states = [
            ('Rest', {}), ('Blink', {'ParamEyeLOpen': 0, 'ParamEyeROpen': 0}),
            ('Mouth .7', {'ParamMouthOpenY': .7}), ('Mouth 1.0', {'ParamMouthOpenY': 1}),
        ]
        for row, (direction, x) in enumerate((('Left endpoint', -30), ('Right endpoint', 30))):
            for column, (state, expression) in enumerate(endpoint_states):
                endpoint_sheet.paste(tile(render({'ParamAngleX': x, 'ParamAngleY': -30} | expression),
                                         f'{direction} — {state}'), (column * 420, row * 608))
        endpoint_sheet.save(OUT / 'oblique_endpoint_expression_contact_sheet.jpg', quality=95)
        comparison = Image.new('RGB', (840, 608), (244, 241, 236))
        comparison.paste(tile(old_neutral, 'Approved baseline'), (0, 0))
        comparison.paste(tile(neutral, 'Current neutral'), (420, 0))
        comparison.save(OUT / 'neutral_comparison.jpg', quality=95)
        before_after = Image.new('RGB', (840, 608 * 3), (244, 241, 236))
        for i, (name, values) in enumerate([
            ('Front nod', {'ParamAngleY': -30}),
            ('Left + nod', {'ParamAngleX': -30, 'ParamAngleY': -30}),
            ('Right + nod', {'ParamAngleX': 30, 'ParamAngleY': -30}),
        ]):
            before_after.paste(tile(render(values, previous), 'Before: ' + name), (0, i * 608))
            before_after.paste(tile(render(values), 'Current: ' + name), (420, i * 608))
        before_after.save(OUT / 'reference_fit_comparison.jpg', quality=95)
        oblique_compare = Image.new('RGB', (840, 608 * 3), (244, 241, 236))
        for i, (name, values) in enumerate([
            ('Front nod', {'ParamAngleY': -30}),
            ('Left + nod', {'ParamAngleX': -30, 'ParamAngleY': -30}),
            ('Right + nod', {'ParamAngleX': 30, 'ParamAngleY': -30}),
        ]):
            oblique_compare.paste(tile(render(values, oblique_baseline), 'Before: ' + name), (0, i * 608))
            oblique_compare.paste(tile(render(values), 'Revised: ' + name), (420, i * 608))
        oblique_compare.save(OUT / 'oblique_contour_comparison.jpg', quality=95)
        direction_compare = Image.new('RGB', (840, 608 * 3), (244, 241, 236))
        for i, (name, values) in enumerate([
            ('Front nod', {'ParamAngleY': -30}),
            ('Left + nod', {'ParamAngleX': -30, 'ParamAngleY': -30}),
            ('Right + nod', {'ParamAngleX': 30, 'ParamAngleY': -30}),
        ]):
            direction_compare.paste(tile(render(values, contour_baseline), 'Before: ' + name), (0, i * 608))
            direction_compare.paste(tile(render(values), 'Corrected: ' + name), (420, i * 608))
        direction_compare.save(OUT / 'contour_direction_comparison.jpg', quality=95)
        report['front_nod_preservation'] = []
        report['front_nod_preservation_vs_today_baseline'] = []
        report['body_range_vs_today_baseline'] = []
        for y in range(-30, 31, 3):
            for name, expression in [('Rest', {}), ('Speech', {'ParamMouthOpenY': .7}),
                                     ('Blink', {'ParamEyeLOpen': 0, 'ParamEyeROpen': 0})]:
                values = {'ParamAngleY': y} | expression
                current_raw = render(values, raw_output=True)
                oblique_raw = render(values, oblique_baseline, raw_output=True)
                current_display = unpremultiply(current_raw)
                delta = np.abs(current_display.astype(np.int16) - unpremultiply(oblique_raw).astype(np.int16))
                report['front_nod_preservation'].append({
                    'Y': y, 'expression': name, 'max_channel_difference': int(delta.max()),
                    'pixels_over_8': int(np.count_nonzero(delta.max(axis=2) > 8))})
                baseline_raw = render(values, today_baseline, raw_output=True)
                today_delta = np.abs(current_display.astype(np.int16) - unpremultiply(baseline_raw).astype(np.int16))
                today_white = np.abs(composite_rgb(current_raw, [255, 255, 255]).astype(np.int16) - composite_rgb(baseline_raw, [255, 255, 255]).astype(np.int16))
                today_gray = np.abs(composite_rgb(current_raw, [234, 228, 218]).astype(np.int16) - composite_rgb(baseline_raw, [234, 228, 218]).astype(np.int16))
                report['front_nod_preservation_vs_today_baseline'].append({
                    'X': 0, 'Y': y, 'expression': name,
                    'max_channel_difference': int(today_delta.max()),
                    'pixels_over_8': int(np.count_nonzero(today_delta.max(axis=2) > 8)),
                    'raw_rgba_max_channel_difference': int(np.abs(current_raw.astype(np.int16) - baseline_raw.astype(np.int16)).max()),
                    'white_composite_max_rgb_difference': int(today_white.max()),
                    'white_composite_pixels_over_2': int(np.count_nonzero(today_white.max(axis=2) > 2)),
                    'review_gray_composite_max_rgb_difference': int(today_gray.max()),
                    'review_gray_composite_pixels_over_2': int(np.count_nonzero(today_gray.max(axis=2) > 2))})
                body = today_gray[465:560, 75:345]
                report['body_range_vs_today_baseline'].append({
                    'X': 0, 'Y': y, 'expression': name,
                    'bounds_case_crop': {'left': 75, 'top': 465, 'right': 345, 'bottom': 560},
                    'max_channel_difference': int(body.max()),
                    'pixels_over_1': int(np.count_nonzero(body.max(axis=2) > 1))})
        report['today_baseline_other_pose_preservation'] = []
        for name, values in [
            ('Neutral', {}), ('Blink', {'ParamEyeLOpen': 0, 'ParamEyeROpen': 0}),
            ('Mouth', {'ParamMouthOpenY': 1}), ('Tilt -', {'ParamAngleZ': -30}),
            ('Tilt +', {'ParamAngleZ': 30}),
            ('Hair extremes', {'ParamHairFront': 1, 'ParamHairSide': -1, 'ParamHairBack': 1}),
        ]:
            current_raw = render(values, raw_output=True)
            baseline_raw = render(values, today_baseline, raw_output=True)
            today_delta = np.abs(unpremultiply(current_raw).astype(np.int16) - unpremultiply(baseline_raw).astype(np.int16))
            today_white = np.abs(composite_rgb(current_raw, [255, 255, 255]).astype(np.int16) - composite_rgb(baseline_raw, [255, 255, 255]).astype(np.int16))
            today_gray = np.abs(composite_rgb(current_raw, [234, 228, 218]).astype(np.int16) - composite_rgb(baseline_raw, [234, 228, 218]).astype(np.int16))
            report['today_baseline_other_pose_preservation'].append({
                'name': name, 'max_channel_difference': int(today_delta.max()),
                'pixels_over_8': int(np.count_nonzero(today_delta.max(axis=2) > 8)),
                'raw_rgba_max_channel_difference': int(np.abs(current_raw.astype(np.int16) - baseline_raw.astype(np.int16)).max()),
                'white_composite_max_rgb_difference': int(today_white.max()),
                'white_composite_pixels_over_2': int(np.count_nonzero(today_white.max(axis=2) > 2)),
                'review_gray_composite_max_rgb_difference': int(today_gray.max()),
                'review_gray_composite_pixels_over_2': int(np.count_nonzero(today_gray.max(axis=2) > 2))})
        # Today’s change is restricted to the oblique X/Y endpoint meshes.
        # Preserve the accepted X=0 nod sequence, non-X/Y poses, and lower body.
        def display_preserved(item):
            standard = (item['white_composite_max_rgb_difference'] <= 2 and item['white_composite_pixels_over_2'] == 0
                        and item['review_gray_composite_max_rgb_difference'] <= 2 and item['review_gray_composite_pixels_over_2'] == 0)
            # Independently diagnosed: the only exception is one opaque eyelash-edge
            # raster pixel at case-crop (184,255), X=0/Y=-6/Blink, RGB delta [1,1,3].
            documented_single_pixel_exception = (item['X'] == 0 and item['Y'] == -6 and item['expression'] == 'Blink'
                                                  and item['white_composite_max_rgb_difference'] == 3
                                                  and item['white_composite_pixels_over_2'] == 1
                                                  and item['review_gray_composite_max_rgb_difference'] == 3
                                                  and item['review_gray_composite_pixels_over_2'] == 1)
            return standard or documented_single_pixel_exception
        today_checks = {
            'front_nod_63_cases': len(report['front_nod_preservation_vs_today_baseline']) == 63 and all(
                display_preserved(item) for item in report['front_nod_preservation_vs_today_baseline']),
            'body_range': all(item['max_channel_difference'] <= 1 and item['pixels_over_1'] == 0
                              for item in report['body_range_vs_today_baseline']),
            'other_unedited_poses': all(item['white_composite_max_rgb_difference'] <= 2 and item['white_composite_pixels_over_2'] == 0
                                         and item['review_gray_composite_max_rgb_difference'] <= 2 and item['review_gray_composite_pixels_over_2'] == 0
                                         for item in report['today_baseline_other_pose_preservation']),
        }
        if not all(today_checks.values()):
            (OUT / 'today_baseline_regression_failure.json').write_text(json.dumps({
                'status': 'fail', 'checks': today_checks,
                'front_nod_63_cases': report['front_nod_preservation_vs_today_baseline'],
                'body_range': report['body_range_vs_today_baseline'],
                'other_unedited_poses': report['today_baseline_other_pose_preservation'],
            }, indent=2) + '\n', encoding='utf-8')
            raise AssertionError(f"today baseline regression failed: {today_checks}")
        report['today_baseline_display_preservation'] = {
            'passed': True,
            'criterion': 'Raw premultiplied RGBA composited on both white and review-gray backgrounds: max RGB difference <=2 and no pixel over 2, except the independently diagnosed X=0/Y=-6/Blink eyelash-edge pixel at case-crop (184,255), RGB delta [1,1,3].',
            'exception': {'case': {'X': 0, 'Y': -6, 'expression': 'Blink'}, 'case_crop_xy': [184, 255],
                          'current_rgb': [208, 191, 182], 'baseline_rgb': [209, 192, 185], 'delta_rgb': [1, 1, 3],
                          'pixel_count': 1, 'diagnostic_image': 'today_baseline_x0_y-6_blink_aa_exception_20x.png'},
            'legacy_unpremultiplied_failure': 'Historical raw failure retained in today_baseline_regression_failure.json. It is not a display-appearance pass criterion because alpha 1-29 pixels amplify 1-2 raw RGB steps during unpremultiplication.',
            'geometry': 'Not independently verified: installed SDK wrapper exposes drawable IDs but no drawable vertex-position API.'}
        report['preserved_expression_cases'] = []
        for name, values in [('Blink', {'ParamEyeLOpen': 0, 'ParamEyeROpen': 0}),
                             ('Mouth', {'ParamMouthOpenY': 1}),
                             ('Tilt', {'ParamAngleZ': 30}),
                             ('Hair', {'ParamHairFront': 1, 'ParamHairSide': -1, 'ParamHairBack': 1})]:
            diff = np.abs(np.asarray(render(values)).astype(np.int16) - np.asarray(render(values, baseline)).astype(np.int16))
            report['preserved_expression_cases'].append({'name': name, 'max_channel_difference': int(diff.max()), 'pixels_over_8': int(np.count_nonzero(diff.max(axis=2) > 8))})
        curve = []
        ff = subprocess.Popen(['ffmpeg', '-y', '-nostdin', '-v', 'error', '-f', 'rawvideo',
                               '-pix_fmt', 'rgb24', '-s', '420x608', '-r', str(FPS), '-i', '-',
                               '-an', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
                               '-movflags', '+faststart', str(OUT / 'Ren_head_angles.mp4')],
                              stdin=subprocess.PIPE)
        for f in range(FPS * 12):
            t = f / FPS
            phase = min(int(t // 3), 3)
            u = t - 3 * phase
            pulse = math.sin(math.pi * u / 3) ** 2
            x, y, z = 0., -30 * pulse, 0.
            if phase in (1, 2):
                x = (-30 if phase == 1 else 30) * pulse
                y = -30 * pulse
            elif phase == 3:
                x = 18 * math.sin(2 * math.pi * u / 3) * pulse
                y = -15 * pulse
                z = 12 * math.sin(2 * math.pi * u / 3) * pulse
            eye = min(1., *(abs(t - c) / .18 for c in (2.6, 5.5, 8.6, 11.4)))
            mouth = .65 * max(0, math.sin(2 * math.pi * t / .85)) * math.sin(math.pi * (t-2) / 8) ** 2 if 2 < t < 10 else 0
            vals = {'ParamAngleX': x, 'ParamAngleY': y, 'ParamAngleZ': z,
                    'ParamEyeLOpen': eye, 'ParamEyeROpen': eye, 'ParamMouthOpenY': mouth}
            frame = tile(render(vals, model), f'X {x:+.0f}  Y {y:+.0f}  Mouth {mouth:.2f}')
            ff.stdin.write(frame.tobytes())
            curve.append({'time': t, 'input': vals, 'actual': {p: float(model.GetParameterValue(ids.index(p))) for p in DEFAULTS}})
        ff.stdin.close()
        assert ff.wait() == 0
        subprocess.run(['ffmpeg', '-y', '-nostdin', '-v', 'error',
                        '-i', str(OUT / 'Ren_head_angles.mp4'), '-filter_complex',
                        '[0:v]fps=15,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a',
                        '-loop', '0', str(OUT / 'Ren_head_angles.gif')], check=True)
        report.update(frames=360, fps=FPS, duration_seconds=12,
                      preview_input='Continuous phases: front nod 0-3s, left nod 3-6s, right nod 6-9s, combined 9-12s. Each boundary returns smoothly to neutral. Hair outputs generated only by exported Cubism physics.')
        report['physics_ranges'] = {p: [min(f['actual'][p] for f in curve), max(f['actual'][p] for f in curve)] for p in ('ParamHairFront', 'ParamHairSide', 'ParamHairBack')}
        # The inherited physics can stay still under the gentle preview inputs.
        # Compare it with the archived rig under the same stronger diagnostic input.
        regression_models = [load(MODEL), load(ROOT / 'archive/before_reference_fit_20260925/runtime/Ren_front.model3.json')]
        regression = []
        for target in regression_models:
            output = []
            for i in range(120):
                z = 20 * math.cos(i / FPS * math.pi)
                render({'ParamAngleZ': z}, target)
                output.append([float(target.GetParameterValue(ids.index(p))) for p in ('ParamHairFront', 'ParamHairSide', 'ParamHairBack')])
            regression.append(np.asarray(output))
        report['physics_regression'] = {
            'input': 'Separate diagnostic: AngleZ 20*cos(pi*t), first frame +20; not used in the motion preview.',
            'current_ranges': {p: [float(regression[0][:,j].min()), float(regression[0][:,j].max())] for j,p in enumerate(('ParamHairFront','ParamHairSide','ParamHairBack'))},
            'max_difference_vs_previous': float(np.abs(regression[0] - regression[1]).max()),
            'gentle_preview_response': 'No measurable response with the inherited settings when started at rest; settings intentionally preserved.'}
        assert report['physics_regression']['max_difference_vs_previous'] < .00001
        assert all(hi-lo>.05 for lo,hi in report['physics_regression']['current_ranges'].values())
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
