"""Reference comparison: similarity alignment only, no source-art modification."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'preview'
reference = ROOT.parents[1] / 'art/Looking_down/Looking_down (2).png'
src = np.array([[295.9, 527.3], [487.3, 507.3]])
dst = np.array([[145.8, 248.8], [220.3, 248.4]])
v, w = src[1] - src[0], dst[1] - dst[0]
a = np.dot(v, w) / np.dot(v, v)
b = (v[0]*w[1]-v[1]*w[0]) / np.dot(v, v)
mat = np.array([[a, -b], [b, a]])
offset = dst[0] - mat @ src[0]
inv = np.linalg.inv(mat)
coeff = np.column_stack((inv, -inv @ offset)).ravel()
ref = Image.open(reference).convert('RGBA').transform((420,570), Image.Transform.AFFINE, coeff, Image.Resampling.BICUBIC)
before = Image.open(ROOT / 'archive/before_contour_direction_20260925/preview/case_01.png').convert('RGBA')
current = Image.open(OUT / 'case_01.png').convert('RGBA')
font = ImageFont.truetype('C:/Windows/Fonts/meiryo.ttc', 17)
sheet = Image.new('RGB', (1260, 615), '#f4f1ec')
for i,(im,title) in enumerate([(ref,'原画 (2)：目の間隔・傾きを揃えた比較'), (before,'今回の修正前'),(current,'修正後：実モデルの描画')]):
    bg = Image.new('RGBA',im.size,'#eae4da')
    bg.alpha_composite(im)
    sheet.paste(bg.convert('RGB'),(i*420,45))
    ImageDraw.Draw(sheet).text((i*420+10,10),title,font=font,fill='#222222')
sheet.save(OUT / 'reference_contour_comparison.jpg',quality=96)
points = {name:(mat @ np.array(point)+offset).tolist() for name,point in {'mouth':[417,655],'chin':[424,730],'nose':[384,588]}.items()}
(OUT / 'reference_alignment.json').write_text(json.dumps({'method':'Manual eye landmarks, rotation and uniform scale only. Approximate guide, not automatic face fitting.','reference_eye_centres':src.tolist(),'target_eye_centres':dst.tolist(),'reference_points_aligned':points},indent=2),encoding='utf8')
print(points)
