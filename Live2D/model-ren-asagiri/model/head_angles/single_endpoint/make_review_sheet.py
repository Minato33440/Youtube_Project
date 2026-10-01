"""Lay out the already-rendered contour diagnostic; never edit model artwork."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent
src = root / 'contour_check'
box = (720, 300, 1250, 760)
font = ImageFont.truetype('C:/Windows/Fonts/meiryo.ttc', 24)
small = ImageFont.truetype('C:/Windows/Fonts/meiryo.ttc', 21)
sheet = Image.new('RGB', (1590, 604), (248, 247, 243))
draw = ImageDraw.Draw(sheet)
panels = [
    ('source_reference_2000x3000_review.png', '原画：傾きを保持した目標'),
    ('face_underfill_render_2000x3000_review.png', '今回：Cubismの顔下地'),
    ('face_underfill_alpha_target_overlay_2000x3000.png', '輪郭と基準点の重ね合わせ'),
]
for col, (filename, label) in enumerate(panels):
    sheet.paste(Image.open(src / filename).convert('RGB').crop(box), (530 * col, 48))
    draw.text((530 * col + 12, 7), label, font=font, fill=(31, 36, 45))
draw.text((16, 520), '水色：原画の見える輪郭と計測点　赤：モデルの輪郭　桃色：鼻・顎の目標位置', font=small, fill=(31, 36, 45))
draw.text((16, 560), '工程1〜3の静止確認。目・口・耳・髪の位置合わせは次工程。髪に隠れる輪郭は計測対象外。', font=small, fill=(31, 36, 45))
output = root / 'preview/single_endpoint_contour_review.png'
sheet.save(output)
print(output)
