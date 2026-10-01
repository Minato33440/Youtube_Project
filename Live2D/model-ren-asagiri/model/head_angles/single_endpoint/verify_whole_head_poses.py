"""Render the exported candidate, preserving source/model files unchanged.

The face-only checks expose interpolation and jaw movement without eyes/hair.
No model warp, artwork edit, or physics evaluation occurs in this script.
"""
from pathlib import Path
from datetime import datetime
import os, json, hashlib
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import live2d.v3 as live2d
from OpenGL.GL import glReadPixels, GL_RGBA, GL_UNSIGNED_BYTE, glFinish

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'whole_head_pose_check'
SIZE = (2000, 3000)
BG = np.array([235, 232, 226])
DEFAULTS = {'ParamAngleX': 0, 'ParamAngleY': 0, 'ParamAngleZ': 0,
            'ParamEyeLOpen': 1, 'ParamEyeROpen': 1, 'ParamMouthOpenY': 0,
            'ParamHairFront': 0, 'ParamHairSide': 0, 'ParamHairBack': 0}
FONT = ImageFont.truetype('C:/Windows/Fonts/meiryo.ttc', 17)
SMALL = ImageFont.truetype('C:/Windows/Fonts/meiryo.ttc', 15)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def flat(raw):
    return np.clip(np.rint(raw[:, :, :3].astype(float) + BG * (1 - raw[:, :, 3:4]/255)), 0, 255).astype(np.uint8)


def border(mask):
    p = np.pad(mask, 1)
    return mask & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])


def row_diagnostic(raw, threshold=16):
    # A connected, filled face silhouette should have one visible run per row.
    # This finds raster splits/holes but does not prove triangle orientation.
    mask = raw[:, :, 3] >= threshold
    transitions = np.diff(np.pad(mask.astype(np.int8), ((0, 0), (1, 1))), axis=1)
    runs = (transitions == 1).sum(axis=1)
    occupied = np.flatnonzero(runs)
    return {'alpha_threshold': threshold, 'max_runs_per_row': int(runs.max()),
            'rows_with_multiple_runs': int(np.count_nonzero(runs > 1)),
            'empty_rows_inside_bbox': int(np.count_nonzero(runs[occupied[0]:occupied[-1]+1] == 0)),
            'opaque_pixels': int(np.count_nonzero(mask))}


def boundary_delta(a, b):
    # Symmetric Chebyshev distance of raster boundaries (exact on the pixel grid).
    ea, eb = border(a[:, :, 3] >= 16), border(b[:, :, 3] >= 16)
    bounds = []
    for source, target in ((ea, eb), (eb, ea)):
        expanded = target.copy()
        values = np.full(source.shape, -1, dtype=np.int16)
        values[source & expanded] = 0
        for radius in range(1, 17):
            p = np.pad(expanded, 1)
            expanded = np.logical_or.reduce([p[dy:dy+SIZE[1], dx:dx+SIZE[0]] for dy in range(3) for dx in range(3)])
            values[source & expanded & (values < 0)] = radius
            if np.all(values[source] >= 0):
                break
        measured = values[source]
        bounds.append({'max_render_px': int(measured.max()) if np.all(measured >= 0) else None,
                       'unmatched_beyond_16px': int(np.count_nonzero(measured < 0)),
                       'p90_render_px': float(np.percentile(measured[measured >= 0], 90))})
    return {'metric': 'symmetric Chebyshev distance at 2000x3000; original-canvas pixels are x2',
            'directions': bounds}


def tile(raw, label, crop, width=400):
    im = Image.fromarray(flat(raw)).crop(crop)
    im = im.resize((width, round(im.height*width/im.width)), Image.Resampling.LANCZOS)
    result = Image.new('RGB', (width, im.height+38), (248, 247, 243))
    result.paste(im, (0, 38))
    ImageDraw.Draw(result).text((10, 8), label, font=FONT, fill=(25, 28, 35))
    return result


def sheet(panels, cols, title, footer, path):
    w, h = panels[0].size
    rows = (len(panels)+cols-1)//cols
    result = Image.new('RGB', (w*cols, h*rows+96), (248, 247, 243))
    d = ImageDraw.Draw(result)
    d.text((12, 10), title, font=FONT, fill=(25, 28, 35))
    for i, panel in enumerate(panels):
        result.paste(panel, (i%cols*w, i//cols*h+48))
    d.text((12, result.height-34), footer, font=SMALL, fill=(60, 64, 72))
    result.save(path)


def main():
    OUT.mkdir(exist_ok=True)
    pygame.display.init(); live2d.init()
    pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)
    pygame.display.set_mode(SIZE, pygame.OPENGL | pygame.DOUBLEBUF | pygame.HIDDEN)
    live2d.glInit()
    models = []
    paths = {'face': ROOT/'face_runtime/Ren_face_endpoint.model3.json',
             'old_face': ROOT/'archive/before_whole_head_outline_20260926/face_runtime/Ren_face_endpoint.model3.json',
             'full': ROOT/'runtime/Ren_face_endpoint.model3.json',
             'baseline': ROOT/'archive/before_whole_head_outline_20260926/runtime/Ren_face_endpoint.model3.json'}
    def load(path):
        m = live2d.LAppModel(); m.LoadModelJson(str(path)); m.Resize(*SIZE)
        m.SetAutoBlinkEnable(False); m.SetAutoBreathEnable(False)
        models.append(m)
        return m
    def render(m, params):
        pygame.event.pump()
        for key, value in (DEFAULTS | params).items():
            m.SetParameterValue(key, float(value))
        m._model.Update(1/30)
        live2d.clearBuffer(0, 0, 0, 0); m.Draw(); glFinish()
        return np.frombuffer(glReadPixels(0, 0, *SIZE, GL_RGBA, GL_UNSIGNED_BYTE), np.uint8).reshape(SIZE[1], SIZE[0], 4)[::-1].copy()
    report = {'checked_at': datetime.now().astimezone().isoformat(),
              'render_size': SIZE, 'physics_evaluated': False, 'source_or_raster_warp': False,
              'provenance': {}, 'face_pose_cases': [], 'front_face_preservation': [],
              'full_front_preservation': [], 'other_unedited_pose_diagnostics': []}
    try:
        face, old_face, full, baseline = [load(paths[k]) for k in ('face', 'old_face', 'full', 'baseline')]
        for name, path in paths.items():
            cfg = json.loads(path.read_text(encoding='utf-8'))
            report['provenance'][name] = {'model3': str(path), 'moc3_sha256': sha(path.parent/cfg['FileReferences']['Moc'])}
        report['face_drawables'] = face.GetDrawableIds()
        # All points along the diagonal, plus two unequal-angle intermediate poses.
        cases = [('正面', 0, 0), ('中間 1', -7.5, -7.5), ('中間 2', -15, -15),
                 ('中間 3', -22.5, -22.5), ('終点', -30, -30),
                 ('中間 X-15 / Y-30', -15, -30), ('中間 X-30 / Y-15', -30, -15),
                 ('正面の頷き', 0, -30)]
        middle_panels, jaw_panels = [], []
        for label, x, y in cases:
            for mouth in (0, .35, .7, 1):
                params = {'ParamAngleX': x, 'ParamAngleY': y, 'ParamMouthOpenY': mouth}
                raw = render(face, params)
                report['face_pose_cases'].append({'label': label, 'params': params,
                    'raster': row_diagnostic(raw), 'raster_alpha64': row_diagnostic(raw, 64)})
                if mouth == 0:
                    middle_panels.append(tile(raw, label, (700, 100, 1280, 820)))
                if label in ('正面の頷き', '終点'):
                    jaw_panels.append(tile(raw, f'{label} / 口 {mouth:g}', (700, 100, 1280, 820)))
        sheet(middle_panels, 4, '顔下地のみ：中間姿勢の確認（実 Cubism 出力）',
              '同じ切り取り位置と倍率。髪・目・口・耳の終点位置は今回の調整範囲外。', OUT/'face_intermediate_poses_ja.png')
        sheet(jaw_panels, 4, '顔下地のみ：口開閉に伴う顎の追従',
              '上段：斜め終点、下段：正面頷き。左から閉口／小／会話／最大。', OUT/'face_jaw_opening_ja.png')
        # Compare the existing frontal nod and jaw movement to the prior topology.
        for y in (-30, -15, 0, 15, 30):
            for mouth in (0, .7, 1):
                params = {'ParamAngleY': y, 'ParamMouthOpenY': mouth}
                a, b = render(old_face, params), render(face, params)
                delta = np.abs(flat(a).astype(np.int16)-flat(b).astype(np.int16))
                report['front_face_preservation'].append({'params': params,
                    'display_max': int(delta.max()), 'display_pixels_over_2': int(np.count_nonzero(delta.max(axis=2)>2)),
                    'boundary_delta': boundary_delta(a, b)})
        full_panels = []
        for y in (0, -30):
            for mouth in (0, .35, .7, 1):
                params = {'ParamAngleY': y, 'ParamMouthOpenY': mouth}
                a, b = render(baseline, params), render(full, params)
                delta = np.abs(flat(a).astype(np.int16)-flat(b).astype(np.int16))
                mask = delta.max(axis=2)>2
                yy, xx = np.nonzero(mask)
                report['full_front_preservation'].append({'params': params, 'display_max': int(delta.max()),
                    'display_pixels_over_2': int(mask.sum()),
                    'changed_bbox': [int(xx.min()), int(yy.min()), int(xx.max()), int(yy.max())] if len(xx) else None})
                full_panels.extend([tile(a, f'前：Y{y} / 口{mouth:g}', (770, 260, 1230, 640), 360),
                                    tile(b, f'後：Y{y} / 口{mouth:g}', (770, 260, 1230, 640), 360)])
        sheet(full_panels, 4, '正面の口開閉・頷き：調整前と調整後',
              '各「前・後」のペアは同条件。表情・髪の設定は変更していません。', OUT/'front_mouth_preservation_ja.png')
        other_panels = []
        for label, x, y in [('反対側の終点', 30, -30), ('同側・頷きなし', -30, 0), ('同側・上向き', -30, 30)]:
            params = {'ParamAngleX': x, 'ParamAngleY': y}
            a, b = render(old_face, params), render(face, params)
            report['other_unedited_pose_diagnostics'].append({'label': label, 'params': params,
                'boundary_delta': boundary_delta(a, b), 'raster_alpha64': row_diagnostic(b, 64)})
            other_panels.extend([tile(a, label+'：前', (700, 100, 1280, 820)),
                                 tile(b, label+'：後', (700, 100, 1280, 820))])
        sheet(other_panels, 2, 'メッシュ未編集姿勢の確認：他の3姿勢',
              '左：今回の調整前、右：今回。これらの終点の形は今回直接編集していません。', OUT/'other_pose_remesh_differences_ja.png')
        report['all_face_rasters_single_filled_silhouette'] = all(
            row['raster']['max_runs_per_row']==1 and row['raster']['empty_rows_inside_bbox']==0
            for row in report['face_pose_cases'])
        report['all_face_rasters_single_filled_silhouette_alpha64'] = all(
            row['raster_alpha64']['max_runs_per_row']==1 and row['raster_alpha64']['empty_rows_inside_bbox']==0
            for row in report['face_pose_cases'])
        report['front_face_max_boundary_distance_render_px'] = max(
            d['max_render_px'] for row in report['front_face_preservation'] for d in row['boundary_delta']['directions'])
        report['geometry_limit'] = 'Wrapper has no vertex/index buffer API; no claim of a numerical triangle inversion audit.'
        report['visual_acceptance'] = 'Needs human inspection of sheets; numerical raster checks are not aesthetic acceptance.'
    finally:
        for model in models: model.DestroyRenderer()
        live2d.dispose(); pygame.quit()
    (OUT/'whole_head_pose_checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'face_pose_count':len(report['face_pose_cases']),
                      'single_silhouette': report['all_face_rasters_single_filled_silhouette'],
                      'front_boundary_max_render_px':report['front_face_max_boundary_distance_render_px']}, ensure_ascii=False))


if __name__ == '__main__': main()
