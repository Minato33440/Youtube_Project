"""Render only current head PNGs from assembly.json; never edit source artwork."""
from pathlib import Path
import sys, json, hashlib
HEAD = Path(__file__).resolve().parent
sys.path.insert(0, str(HEAD.parents[3] / 'output/live2d/risa_parts_v1/tools/pylib'))
from PIL import Image, ImageDraw, ImageFont

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def background(im):
    out = Image.new('RGBA', im.size, (80, 105, 110, 255))
    out.alpha_composite(im)
    return out.convert('RGB')

def render(manifest, output):
    output.mkdir(parents=True, exist_ok=True)
    canvas = Image.new('RGBA', (4000, 1600))
    hashes = {}
    for layer in manifest['layers']:
        path = HEAD / layer['file']
        im = Image.open(path).convert('RGBA')
        assert list(im.size) == layer['size'], (path.name, im.size, layer['size'])
        hashes[layer['file']] = sha(path)
        if layer['flipHorizontal']:
            im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        canvas.alpha_composite(im, tuple(layer['globalPosition']))
    crop = tuple(manifest['globalCrop'])
    head = canvas.crop(crop)
    head.save(output/'head_sample.png')
    background(head).save(output/'head_sample_gray.png')
    raw = Image.open(HEAD/'reference/ren-stand-pony-front-4000x6000.png').convert('RGBA')
    font = ImageFont.truetype('C:/Windows/Fonts/meiryo.ttc', 24)
    for filename, box, size in [('comparison_original.jpg', crop, (666, 702)), ('comparison_face_detail.jpg', (1650, 650, 2350, 1190), (840, 648))]:
        w, h = size
        out = Image.new('RGB', (w*2, h+50), (58, 63, 67))
        d = ImageDraw.Draw(out)
        for i, (im, label) in enumerate([(raw.crop(box), '原画'), (canvas.crop(box), '最新頭部：後ろ髪・下地修正反映')]):
            out.paste(background(im).resize(size, Image.Resampling.LANCZOS), (i*w, 50))
            d.text((i*w+10, 8), label, font=font, fill='white')
        out.save(output/filename, quality=98)
    assert all(sha(HEAD/p) == s for p, s in hashes.items())
    return hashes

if __name__ == '__main__':
    manifest = json.loads((HEAD/'assembly.json').read_text(encoding='utf8'))
    # Review output only; promotion to preview/acceptance requires visual review.
    hashes = render(manifest, HEAD/'work/render_current')
    print(json.dumps({'parts': len(hashes), 'inputArtworkUnchanged': True}))
