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
r = json.loads((OUT / 'verification.json').read_text())
assert r['neutral_vs_approved']['max_channel_difference'] <= 1
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
assert all(hi-lo > .05 for lo, hi in r['physics_ranges'].values())
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
    'source_cmo3_unchanged': True, 'source_cmo3_sha256': snapshot['source_sha256'],
    'editor_file_sha256': sha(ROOT / 'Ren_front.cmo3'),
    'runtime_hashes': r['runtime_hashes'], 'neutral_vs_approved': r['neutral_vs_approved'],
    'actual_runtime_cases': 16, 'drawable_count': 48,
    'parameter_count': len(r['parameter_ids']), 'lower_shirt_invariance': shirt,
    'physics_ranges': r['physics_ranges'],
    'mp4': {'frames': 360, 'fps': 30, 'duration_seconds': 12},
    'gif': {'frames': 180, 'duration_ms': duration},
    'preview_hashes': {p.name: sha(p) for p in [OUT/'Ren_head_angles.mp4', OUT/'Ren_head_angles.gif']},
    'limits': ['Initial small AngleX/Y forms; not a full profile rig.',
               'Side-view source PNGs are references, not imported replacement layers.',
               'Neck_Follow remains the prior AngleZ implementation; no independent XY neck keys.',
               'Hair physics retains prior AngleZ inputs.',
               'Not tested in VTube Studio or nizima LIVE; Boss motion acceptance pending.']
}
(ROOT / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in ['passed','source_png_count','source_cmo3_unchanged','neutral_vs_approved','actual_runtime_cases']}))
