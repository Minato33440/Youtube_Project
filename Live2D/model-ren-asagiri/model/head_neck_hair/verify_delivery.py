"""Validate delivered files and source preservation; build review crops from renders."""
from pathlib import Path
import json
import hashlib
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
ART = ROOT.parents[1] / 'art'
OUT = ROOT / 'preview'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
checks = []
for item in json.loads((ART / 'psd_front/manifest.json').read_text(encoding='utf-8'))['layers']:
    path = (ART / 'psd_front' / item['path']).resolve()
    checks.append({'file': str(path), 'sha256': sha(path), 'unchanged': sha(path) == item['sha256']})
for name, expected in json.loads((ART / 'expression_rig/source_hashes.json').read_text()).items():
    path = ART / 'head/expression_sources/mouth' / f'{name}.png'
    checks.append({'file': str(path), 'sha256': sha(path), 'unchanged': sha(path) == expected})
for side, expected in json.loads((ART / 'expression_rig/blink_source_hashes.json').read_text()).items():
    path = ART / 'head/expression_sources/blink' / f'eyelash_upper_{side}_original.png'
    checks.append({'file': str(path), 'sha256': sha(path), 'unchanged': sha(path) == expected})
assert len(checks) == 48 and all(x['unchanged'] for x in checks)
baseline_hash = sha(ROOT.parent / 'basic_expression/Ren_front.cmo3')
assert baseline_hash == '293e779ee860359b50420b26b0da97f1fa1795db49affb7157cb92dbdf6bf221'
render = json.loads((OUT / 'verification.json').read_text())
assert render['neutral_vs_approved']['max_channel_difference'] <= 1
assert render['drawable_count'] == 48
for path, expected in render['runtime_hashes'].items():
    assert sha(ROOT / path) == expected, path
config = json.loads((ROOT / 'runtime/Ren_front.model3.json').read_text())
refs = config['FileReferences']
for path in [refs['Moc'], refs['Physics'], refs['DisplayInfo'], *refs['Textures']]:
    assert (ROOT / 'runtime' / path).is_file(), path
physics = json.loads((ROOT / 'runtime' / refs['Physics']).read_text())
assert physics['Meta']['PhysicsSettingCount'] == 3 and physics['Meta']['Fps'] == 60
assert len(refs['Textures']) == 1
with Image.open(ROOT / 'runtime' / refs['Textures'][0]) as texture:
    assert texture.size == (2048, 2048)
probe = json.loads(subprocess.check_output([
    'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json',
    str(OUT / 'Ren_head_neck_hair.mp4')], text=True))
video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
assert (video['width'], video['height'], int(video['nb_frames'])) == (420, 608, 360)
assert abs(float(probe['format']['duration']) - 12) < .01

# Compare the unaffected lower shirt in every exported parameter extreme.
neutral = np.asarray(Image.open(OUT / 'case_00.png')).astype(np.int16)
shirt_checks = []
for path in sorted(OUT.glob('case_*.png')):
    array = np.asarray(Image.open(path)).astype(np.int16)
    difference = np.abs(array[465:560, 75:345] - neutral[465:560, 75:345])
    shirt_checks.append({'case': path.name, 'max_difference': int(difference.max())})
assert all(c['max_difference'] <= 1 for c in shirt_checks)

font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
samples = [0, 16, 23, 38, 66, 83, 109, 128, 145, 164, 173, 179]
filmstrip = Image.new('RGB', (420 * 4, 608 * 3), '#f4f1ec')
with Image.open(OUT / 'Ren_head_neck_hair.gif') as gif:
    assert gif.n_frames == 180
    gif_duration_ms = 0
    for frame_no in range(gif.n_frames):
        gif.seek(frame_no)
        gif_duration_ms += gif.info['duration']
    assert abs(gif_duration_ms - 12000) <= 20, gif_duration_ms
    for i, frame_no in enumerate(samples):
        gif.seek(frame_no)
        frame = gif.convert('RGB')
        ImageDraw.Draw(frame).text((10, 36), f'{frame_no / 15:.2f} seconds', fill='#222222', font=font)
        filmstrip.paste(frame, (i % 4 * 420, i // 4 * 608))
filmstrip.save(OUT / 'animation_review.jpg', quality=95)

detail = Image.new('RGB', (400 * 3, 390 * 2), '#f4f1ec')
for i, (case, label) in enumerate([(0, 'Neutral'), (1, 'Mouth 0.5'), (2, 'Mouth 1.0'),
                                   (3, 'Tilt -'), (4, 'Tilt +'), (11, 'Tilt + blink')]):
    with Image.open(OUT / f'case_{case:02d}.png') as image:
        crop = image.crop((110, 260, 310, 435)).resize((400, 350))
        bg = Image.new('RGBA', crop.size, '#eae4da')
        bg.alpha_composite(crop)
        detail.paste(bg.convert('RGB'), (i % 3 * 400, i // 3 * 390 + 40))
        ImageDraw.Draw(detail).text((i % 3 * 400 + 10, i // 3 * 390 + 10), label, fill='#222222', font=font)
detail.save(OUT / 'jaw_neck_detail.jpg', quality=95)

report = {
    'passed': True, 'source_png_count': 48, 'sources': checks,
    'baseline_cmo3_unchanged': True, 'baseline_cmo3_sha256': baseline_hash,
    'editor_file_sha256': sha(ROOT / 'Ren_front.cmo3'),
    'runtime_hashes': render['runtime_hashes'],
    'neutral_vs_approved': render['neutral_vs_approved'],
    'lower_shirt_invariance': shirt_checks,
    'mp4': {'size': [420, 608], 'frames': 360, 'fps': '30/1', 'duration_seconds': 12},
    'gif_frames': 180, 'gif_duration_ms': gif_duration_ms,
    'exported_parameter_count': len(render['parameter_ids']),
    'physics_ranges': render['physics_ranges'],
    'limits': ['AngleZ roll only; no AngleX/Y turns or nods.',
               'Ahoge shares ParamHairFront.',
               'No extra laugh opening; conversation mouth retained.',
               'Preview uses one 2048 atlas; source PNGs unchanged.',
               'VTube Studio and nizima LIVE are not tested.',
               'Final subjective motion acceptance remains with Boss.']}
(ROOT / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in ['passed', 'source_png_count', 'baseline_cmo3_unchanged', 'exported_parameter_count', 'mp4']}))
