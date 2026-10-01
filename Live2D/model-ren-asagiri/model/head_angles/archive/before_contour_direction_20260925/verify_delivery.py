"""Check source preservation, actual runtime results and preview timing."""
from pathlib import Path
import hashlib
import json
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
REPO = ROOT.parents[3]
OUT = ROOT / 'preview'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
snapshot = json.loads((ROOT / 'input_snapshot.json').read_text(encoding='utf-8'))
sources = []
for item in snapshot['source_parts']:
    path = PROJECT / item['path']
    sources.append({'path': item['path'], 'unchanged': sha(path) == item['sha256']})
assert all(x['unchanged'] for x in sources)
assert sha(REPO / snapshot['source_model']) == snapshot['source_sha256']
fit_snapshot = json.loads((ROOT / 'reference_fit_inputs.json').read_text(encoding='utf-8'))
fit_sources = [{'path': item['path'], 'unchanged': sha(Path(item['path'])) == item['sha256']}
               for item in fit_snapshot['source_parts']]
assert all(item['unchanged'] for item in fit_sources)
assert sha(ROOT / 'archive/before_reference_fit_20260925/Ren_front.cmo3') == fit_snapshot['baseline_cmo3_sha256']
r = json.loads((OUT / 'verification.json').read_text())
assert sha(ROOT / 'archive/before_oblique_contour_20260925/Ren_front.cmo3') == '56bddfd1bc889dd8af33def466515af09d65e2fdbf62d18e27215757247d1c0a'
assert len(r['front_nod_preservation']) == 63
# Inserting identity warp deformers adds at most 2/255 of raster rounding.
assert all(x['max_channel_difference'] <= 2 and x['pixels_over_8'] == 0
           for x in r['front_nod_preservation'])
assert r['neutral_vs_approved']['max_channel_difference'] <= 1
for case in r['preserved_expression_cases']:
    if case['name'] == 'Tilt':
        # The earlier Head_XY baseline already differs at two edge pixels from
        # head_neck_hair. The archived head_angles Tilt+ image has no >8 delta.
        assert case['pixels_over_8'] <= 2 and case['max_channel_difference'] <= 24
    else:
        assert case['max_channel_difference'] <= 1
curve = json.loads((OUT / 'parameter_curve.json').read_text())
angle_steps = {p: max(abs(b['input'][p]-a['input'][p]) for a,b in zip(curve, curve[1:]))
               for p in ['ParamAngleX','ParamAngleY','ParamAngleZ']}
assert max(angle_steps.values()) < 1.4, angle_steps
for i in (0, 90, 180, 270):
    assert all(abs(curve[i]['input'][p]) < .001 for p in angle_steps)
assert r['drawable_count'] == 48
assert len(r['cases']) == 16
for case in r['cases'][1:]:
    assert case['changed_pixels_over_8'] > 100
    for key, requested in case['requested'].items():
        assert abs(case['actual'][key] - requested) < .001
for name, expected in r['runtime_hashes'].items():
    assert sha(ROOT / name) == expected
config = json.loads((ROOT / 'runtime/Ren_front.model3.json').read_text())
refs = config['FileReferences']
for name in [refs['Moc'], refs['Physics'], refs['DisplayInfo'], *refs['Textures']]:
    assert (ROOT / 'runtime' / name).is_file()
physics = json.loads((ROOT / 'runtime' / refs['Physics']).read_text())
assert physics['Meta']['PhysicsSettingCount'] == 3
assert physics['Meta']['Fps'] == 60
assert r['physics_regression']['max_difference_vs_previous'] < .00001
assert all(hi-lo > .05 for lo, hi in r['physics_regression']['current_ranges'].values())
assert len(refs['Textures']) == 1
assert Image.open(ROOT / 'runtime' / refs['Textures'][0]).size == (2048, 2048)
neutral = np.asarray(Image.open(OUT / 'case_00.png')).astype(np.int16)
shirt = []
for path in sorted(OUT.glob('case_*.png')):
    a = np.asarray(Image.open(path)).astype(np.int16)
    delta = int(np.abs(a[465:560, 75:345] - neutral[465:560, 75:345]).max())
    shirt.append({'case': path.name, 'max_difference': delta})
assert all(x['max_difference'] <= 1 for x in shirt)
probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
    '-show_format', '-of', 'json', str(OUT / 'Ren_head_angles.mp4')], text=True))
v = next(s for s in probe['streams'] if s['codec_type'] == 'video')
assert (v['width'], v['height'], int(v['nb_frames'])) == (420, 608, 360)
assert abs(float(probe['format']['duration']) - 12) < .01
filmstrip = Image.new('RGB', (420*4, 608*3), '#f4f1ec')
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
with Image.open(OUT / 'Ren_head_angles.gif') as gif:
    assert gif.n_frames == 180
    duration = 0
    for i in range(gif.n_frames):
        gif.seek(i)
        duration += gif.info['duration']
    assert abs(duration - 12000) <= 20
    for i, frame_no in enumerate([0, 15, 30, 45, 66, 83, 100, 117, 130, 145, 162, 177]):
        gif.seek(frame_no)
        frame = gif.convert('RGB')
        ImageDraw.Draw(frame).text((10, 36), f'{frame_no/15:.2f} seconds', fill='#222222', font=font)
        filmstrip.paste(frame, (i%4*420, i//4*608))
filmstrip.save(OUT / 'animation_review.jpg', quality=95)
report = {
    'passed': True, 'source_png_count': len(sources), 'sources': sources,
    'reference_fit_source_count': len(fit_sources), 'reference_fit_sources': fit_sources,
    'previous_head_angles_backup_unchanged': True,
    'source_cmo3_unchanged': True, 'source_cmo3_sha256': snapshot['source_sha256'],
    'editor_file_sha256': sha(ROOT / 'Ren_front.cmo3'),
    'runtime_hashes': r['runtime_hashes'], 'neutral_vs_approved': r['neutral_vs_approved'],
    'actual_runtime_cases': 16, 'drawable_count': 48,
    'parameter_count': len(r['parameter_ids']), 'lower_shirt_invariance': shirt,
    'physics_ranges': r['physics_ranges'],
    'physics_regression': r['physics_regression'],
    'preserved_expression_cases': r['preserved_expression_cases'],
    'front_nod_preservation': r['front_nod_preservation'],
    'before_oblique_contour_backup_unchanged': True,
    'max_frame_angle_steps': angle_steps,
    'mp4': {'frames': 360, 'fps': 30, 'duration_seconds': 12},
    'gif': {'frames': 180, 'duration_ms': duration},
    'preview_hashes': {p.name: sha(p) for p in [OUT/'Ren_head_angles.mp4', OUT/'Ren_head_angles.gif']},
    'limits': ['Reference-adjusted small AngleX/Y forms; not a full profile rig.',
               'Looking_down and side-view source PNGs are position references, not imported replacement layers.',
               'Face_Contour_XY adds independent cheek/jaw forms; Neck_Shadow_X varies the existing painted neck shading. Far-ear width is reduced independently on each turn.',
               'Nose/eyes/hair retain existing Head_XY deformation; no additional eye-only warp or new under-chin artwork was added.',
               'Hair physics retains prior AngleZ inputs.',
               'Gentle preview inputs from rest produce no measurable hair physics output; stronger diagnostic input matches the prior rig. XY-driven sway is not added.',
               'Not tested in VTube Studio or nizima LIVE; Boss motion acceptance pending.']
}
(ROOT / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in ['passed','source_png_count','source_cmo3_unchanged','neutral_vs_approved','actual_runtime_cases']}))
