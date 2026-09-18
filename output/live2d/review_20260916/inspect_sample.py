"""Read-only source review: extract actual export frames and summarize N01 curves."""
import csv
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
VIDEO = ROOT / 'Politics_Economics/2026-09-09_fiscal_policy/exports/Risa_Layered_Trial_20260915_MotionFixed.mp4'
rows = list(csv.DictReader((ROOT / 'output/live2d/full_sample_v1/N01/performance_curve.csv').open(encoding='utf-8-sig')))
selected = [('neutral', 0)]
for p in ['a', 'i', 'u', 'e', 'o']:
    candidates = [r for r in rows if r['phoneme'].lower() == p]
    row = max(candidates, key=lambda r: float(r['mouth_open_y']))
    selected.append((p, int(row['frame'])))
for key, fun in [('angle_z', min), ('angle_z', max), ('mouth_form', min), ('mouth_open_y', max)]:
    row = fun(rows, key=lambda r: float(r[key]))
    selected.append((key + (' min' if fun is min else ' max'), int(row['frame'])))
sequence = list(range(0, 479, 15))
indexes = sorted(set(sequence + [i for _, i in selected]))
expr = '+'.join(f'eq(n\\,{643+i})' for i in indexes)
raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(VIDEO), '-vf',
    f"select='{expr}',crop=384:420:1275:99", '-fps_mode', 'passthrough', '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'])
size = 384 * 420 * 3
assert len(raw) == size * len(indexes)
frames = {n: Image.frombytes('RGB', (384, 420), raw[j*size:(j+1)*size]) for j, n in enumerate(indexes)}
sheet = Image.new('RGB', (1000, 390 * 3), '#dddddd')
draw = ImageDraw.Draw(sheet)
for j, (label, n) in enumerate(selected):
    x, y = (j % 4) * 250, (j // 4) * 390
    r = rows[n]
    face = frames[n].crop((70, 0, 310, 255))
    sheet.paste(face, (x, y+50))
    mouth = frames[n].crop((151, 136, 230, 174)).resize((237, 76))
    sheet.paste(mouth, (x, y+308))
    draw.text((x+3, y+3), f'{label}: N01 {n/30:.2f}s / video {(643+n)/30:.2f}s', fill='black')
    draw.text((x+3, y+18), f'open={float(r["mouth_open_y"]):.3f} form={float(r["mouth_form"]):.3f}', fill='black')
    draw.text((x+3, y+32), f'AngleZ={float(r["angle_z"]):.3f}', fill='black')
sheet.save(OUT / 'mouth_neck_details.jpg', quality=95)
seq = Image.new('RGB', (240*8, 282*4), '#dddddd')
draw = ImageDraw.Draw(seq)
for j, n in enumerate(sequence):
    x, y = (j % 8)*240, (j // 8)*282
    seq.paste(frames[n].crop((70, 0, 310, 255)), (x,y+25))
    draw.text((x+4,y+5), f'video {(643+n)/30:.2f}s', fill='black')
seq.save(OUT / 'narration_sequence.jpg', quality=94)
stats = {k: {'min': min(float(r[k]) for r in rows), 'max': max(float(r[k]) for r in rows)}
         for k in ['mouth_open_y','mouth_form','angle_z']}
stats.update(source=str(VIDEO), source_untouched=True, frames=len(rows),
             narration_start_s=643/30, narration_end_s=1122/30,
             review='Actual export frame sequence and parameter data; no real-time audiovisual playback in this review.')
(OUT/'review_measurements.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(stats,ensure_ascii=False,indent=2))
