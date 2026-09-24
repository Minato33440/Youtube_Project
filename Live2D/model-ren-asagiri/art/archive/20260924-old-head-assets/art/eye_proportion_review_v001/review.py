from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
from PIL import Image,ImageDraw,ImageFont
raw=Image.open(ROOT/'art_assets/ren-stand-pony-front-4000x6000.png').convert('RGBA')
# Latest sample uses the global crop (1460,80,2540,1700), at 1:1 resolution.
sample=Image.open(ROOT/'art/eye_style_v006/face_with_brows.jpg').convert('RGB')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
def bg(im):
 b=Image.new('RGBA',im.size,(80,105,110));b.alpha_composite(im);return b.convert('RGB')
rawface=bg(raw.crop((1460,80,2540,1700)))
comp=Image.new('RGB',(1080,720),(80,105,110));d=ImageDraw.Draw(comp)
for i,im in enumerate([rawface,sample]):
 im=im.crop((0,160,1080,1520)).resize((540,680));comp.paste(im,(i*540,40));d.text((i*540+15,8),'Original art' if i==0 else 'Current sample',font=font,fill='white')
comp.save(OUT/'face_comparison.jpg',quality=97)
eye=Image.new('RGB',(1400,430),(80,105,110));d=ImageDraw.Draw(eye)
for i,im in enumerate([rawface,sample]):
 tile=im.crop((240,600,940,970));eye.paste(tile,(700*i,45));d.text((700*i+15,10),'Original / same scale' if i==0 else 'Sample / same scale',font=font,fill='white')
eye.save(OUT/'eyes_comparison.jpg',quality=97)
parts=ROOT/'art/processing_v001/front/parts';rows=[]
for n in ['iris_R_original','iris_L_original','ALT_iris_R_brown','ALT_iris_L_blue','FILL_eye_white_R','FILL_eye_white_L']:
 im=Image.open(parts/(n+'.png')).convert('RGBA');rows.append({'name':n,'size':im.size,'bbox':im.getbbox()})
(OUT/'measurements.json').write_text(json.dumps({'original_size':raw.size,'sample_global_crop':[1460,80,2540,1700],'parts':rows},indent=2),encoding='utf8');print(json.dumps(rows))
