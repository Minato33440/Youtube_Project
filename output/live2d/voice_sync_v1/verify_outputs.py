"""Check media decode, timestamps, extracted audio and actual rendered mouth motion."""
from pathlib import Path
import csv
import hashlib
import json
import subprocess
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
SOURCE = Path('C:/Users/Setona/Desktop/Voicd-Sample.mp4')

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))

def pcm(path):
    return np.frombuffer(subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-vn', '-ac', '1', '-ar', '44100', '-f', 's16le', '-']), dtype='<i2').astype(np.float64)

def main():
    report = {'source': probe(SOURCE), 'outputs': {}, 'checks': {}}
    original = pcm(SOURCE)
    extracted = pcm(ROOT / 'audio_mono_44100_pcm16.wav')
    assert np.array_equal(original, extracted), 'WAV differs from source decoded audio'
    report['checks']['wav_exactly_matches_source_pcm'] = True
    for name in ['Risa_narration_composite.mp4', 'Risa_lipsync_closeup.mp4']:
        path = ROOT / name
        result = probe(path)
        v = next(s for s in result['streams'] if s['codec_type'] == 'video')
        a = next(s for s in result['streams'] if s['codec_type'] == 'audio')
        assert int(v['nb_frames']) == 478 and v['r_frame_rate'] == '30/1'
        assert abs(float(v['duration']) - 478 / 30) < .001
        assert abs(float(v['start_time']) - float(a['start_time'])) < .001
        decoded = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'null', '-'], capture_output=True, text=True)
        assert decoded.returncode == 0 and not decoded.stderr
        sound = pcm(path)
        n = min(len(original), len(sound))
        corr = float(np.corrcoef(original[:n], sound[:n])[0, 1])
        assert corr > .99
        report['outputs'][name] = {'probe': result, 'decode_pass': True, 'audio_zero_offset_correlation': corr, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    rows = list(csv.DictReader((ROOT / 'mouth_curve.csv').open(encoding='utf-8')))
    mouth = np.array([float(r['mouth_open_y']) for r in rows])
    paths = sorted((ROOT / 'frames').glob('*.png'))
    assert len(paths) == len(rows) == 478
    closed = np.array(Image.open(paths[0]))
    measures, outside = [], 0
    for path in paths:
        arr = np.array(Image.open(path))
        diff = np.any(arr != closed, axis=2)
        measures.append(int(diff[190:228, 346:406].sum()))
        diff[190:228, 346:406] = False
        outside = max(outside, int(diff.sum()))
    measures = np.array(measures)
    assert outside == 0, f'Unexpected non-mouth changes: {outside}'
    assert measures.max() > 100 and np.all(measures[mouth == 0] == 0)
    lag_scores = {}
    for lag in range(-3, 4):
        x, y = (mouth[:lag], measures[-lag:]) if lag < 0 else ((mouth[lag:], measures[:-lag]) if lag > 0 else (mouth, measures))
        lag_scores[str(lag)] = float(np.corrcoef(x, y)[0, 1])
    assert max(lag_scores, key=lag_scores.get) == '0'
    report['checks'].update({'png_frames': len(paths), 'transparent_background': bool(closed[0, 0, 3] == 0), 'only_mouth_pixels_change': True, 'rendered_closed_when_curve_zero': True, 'mouth_pixel_change_vs_curve_lag_correlations': lag_scores})
    selected = [0, int(np.argmax(mouth)), 300, 477]
    sheet = Image.new('RGB', (1000, 440), '#101e2b')
    draw = ImageDraw.Draw(sheet)
    for i, frame in enumerate(selected):
        im = Image.open(paths[frame]).crop((260, 80, 510, 450))
        sheet.paste(im, (i * 250, 40), im)
        draw.text((i * 250 + 12, 14), f'{frame/30:.3f}s / mouth {mouth[frame]:.3f}', fill='white')
    sheet.save(ROOT / 'mouth_review.png')
    (ROOT / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'checks': report['checks'], 'audio_correlations': {k:v['audio_zero_offset_correlation'] for k,v in report['outputs'].items()}}, indent=2))

if __name__ == '__main__':
    main()
