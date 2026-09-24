"""Read current art and compose a front PSD manifest; never edit source PNGs."""
from pathlib import Path
import sys, json, hashlib, os
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO/'output/live2d/risa_parts_v1/tools/pylib'))
from PIL import Image, ImageDraw, ImageFont

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')

def bg(im):
    out = Image.new('RGBA', im.size, (80, 105, 110, 255))
    out.alpha_composite(im)
    return out.convert('RGB')

def prepare():
    head = ROOT/'art/head'
    body = ROOT/'art/processing_v001/front/parts'
    old = json.loads((ROOT/'art/processing_v001/front/manifest.json').read_text())
    heads = json.loads((head/'assembly.json').read_text())
    accepted = json.loads((head/'acceptance.json').read_text())['partHashes']
    positions = {l['name']: [l['left'],l['top']] for l in old['layers']}
    positions.update({'shirt_inside':[1717,1128], 'neck-clavicle':[1822,1044],
                      'shirt_torso':[1422,1231], 'collar_R':[1725,1150], 'collar_L':[1964,1147]})
    order = ['shoe_R','shoe_L','trousers_R','trousers_L','hand_R','hand_L',
             'forearm_R','forearm_L','upper_arm_R','upper_arm_L',
             'shirt_inside','neck-clavicle','shirt_torso','sleeve_R','sleeve_L',
             'belt','collar_R','collar_L']
    layers = []
    for name in order:
        p = body/(name+'.png')
        im = Image.open(p).convert('RGBA')
        x,y = positions[name]
        layers.append({'name':name, 'path':os.path.relpath(p,OUT).replace('\\','/'),
                       'left':x,'top':y,'visible':True,'size':list(im.size),
                       'sha256':digest(p),'role':'body_context' if name not in ['neck-clavicle','shirt_inside','shirt_torso','collar_L','collar_R'] else 'neck_collar_integration'})
    changed = []
    for l in heads['layers']:
        p = head/l['file']
        im = Image.open(p).convert('RGBA')
        x,y = l['globalPosition']
        flip = l['flipHorizontal']
        if l['name']=='FILL_eye_white_L':
            # Current source already has the blue-eye orientation; old manifest's flip no longer applies.
            assert im.size==(159,101)
            x,y = 2070,763
            flip=False
        else:
            assert list(im.size)==l['size'], (l['name'],im.size,l['size'])
        assert not flip, 'Any additional transform needs an explicit export path.'
        sha = digest(p)
        if sha!=accepted.get(l['file']):
            changed.append({'file':l['file'],'previousSha256':accepted.get(l['file']), 'sha256':sha})
        layers.append({'name':l['name'],'path':os.path.relpath(p,OUT).replace('\\','/'),
                       'left':x,'top':y,'visible':True,'size':list(im.size),'sha256':sha,
                       'role':'current_head','flipHorizontal':False})
    assert len(layers)==41 and len({l['name'] for l in layers})==41
    manifest={'canvas':{'width':4000,'height':6000}, 'coordinateConvention':'Original front canvas; bottom-to-top layer order; R is character right / viewer left.',
              'status':'PSD preparation, neutral expression only; Cubism import and deformation not yet performed',
              'layers':layers,'changedHeadInputsSincePreviousRegistration':changed,
              'output':{'psd':'Ren_front.psd','flattenedPng':'Ren_front.png','previewPng':'Ren_front_preview.png','verificationJson':'psd_verification.json','previewBackground':'#50696E'}}
    save_json(OUT/'manifest.json',manifest)
    canvas=Image.new('RGBA',(4000,6000))
    for l in layers:
        im=Image.open(OUT/l['path']).convert('RGBA')
        canvas.alpha_composite(im,(l['left'],l['top']))
    canvas.save(OUT/'review/python_composite.png')
    bg(canvas).resize((800,1200),Image.Resampling.LANCZOS).save(OUT/'review/fullbody.jpg',quality=97)
    for name,box in [('head_neck',(1400,70,2600,1750)),('neck_collar',(1620,920,2390,1620)),('eyes',(1690,650,2310,910))]:
        bg(canvas.crop(box)).save(OUT/'review'/f'{name}.png')
    font=ImageFont.truetype('C:/Windows/Fonts/meiryo.ttc',25)
    raw=Image.open(ROOT/'art_assets/ren-stand-pony-front-4000x6000.png').convert('RGBA')
    box=(1400,70,2600,1750); size=(600,840)
    pair=Image.new('RGB',(1200,890),(58,63,67));draw=ImageDraw.Draw(pair)
    for i,(im,label) in enumerate([(raw,'原画'),(canvas,'最新パーツ：頭部・首・襟')]):
        pair.paste(bg(im.crop(box)).resize(size,Image.Resampling.LANCZOS),(i*600,50))
        draw.text((i*600+12,10),label,font=font,fill='white')
    pair.save(OUT/'review/comparison_original.jpg',quality=98)
    assert all(digest(OUT/l['path'])==l['sha256'] for l in layers)
    print(json.dumps({'layers':len(layers),'changedHeadInputs':changed,'sourceArtUnmodified':True},ensure_ascii=False))

if __name__=='__main__':
    prepare()
