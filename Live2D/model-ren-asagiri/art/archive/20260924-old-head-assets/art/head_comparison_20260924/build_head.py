from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent;HEAD=ROOT/'art/head'
sys.path.insert(0,str(ROOT.parents[1]/'output/live2d/risa_parts_v1/tools/pylib'))
from PIL import Image,ImageDraw,ImageFont
import numpy as np
FACE=ROOT/'art/eye_adjust_v007/parts';BODY=ROOT/'art/processing_v001/front/parts'
for name in ['parts','preview','reference','reference/ear_surface']:(HEAD/name).mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
provenance=[]
def copy(src,dst,role):
 h=sha(src)
 if dst.exists():assert sha(dst)==h,'Destination has different hand-edited content: '+str(dst)
 else:shutil.copy2(src,dst)
 assert sha(dst)==h
 provenance.append({'source':str(src),'file':str(dst.relative_to(HEAD)),'sha256':h,'role':role})
assembly=json.loads((OUT/'assembly.json').read_text())
origin=assembly['originalComparisonRegistration']['translation']
for layer in assembly['layers']:
 src=FACE/layer['source'];assert sha(src)==assembly['sourceHashes'][src.name]
 copy(src,HEAD/'parts'/src.name,'active_face')
hair=['hair_back','hair_side_R','hair_side_L','hair_front_R','hair_front_L','hair_front_C','hair_ahoge'];ears=['ear_R','ear_L']
pos=json.loads((ROOT/'art/pre_rig_review_20260922/placements_review.json').read_text())['positions']
for name,item in json.loads((ROOT/'art/overlap_recheck_v002/registration.json').read_text()).items():pos[name]=item['position']
for name in hair+ears:
 # Current files, not old snapshot pixels. Historical coordinates are allowed only after byte equality is verified.
 folder='overlap_recheck_v002' if name in ['hair_side_R','hair_side_L','hair_front_R','hair_front_L','hair_front_C'] else 'pre_rig_review_20260922'
 assert sha(BODY/(name+'.png'))==sha(ROOT/'art'/folder/'source_snapshot'/(name+'.png')),'Re-register updated hair/ear: '+name
 copy(BODY/(name+'.png'),HEAD/'parts'/(name+'.png'),'active_hair' if name in hair else 'active_ear')
for name in ['ear_L_surface','ear_R_surface']:copy(BODY/(name+'.png'),HEAD/'reference/ear_surface'/(name+'.png'),'alternate_not_composited')
for name in ['facial_feature.png','facial_feature.psd','ren-stand-pony-front-4000x6000.png']:copy(FACE/name,HEAD/'reference'/name,'reference_only')
canvas=Image.new('RGBA',(4000,1600));manifest=[]
def add(name,xy,flip=False,size=None):
 im=Image.open(HEAD/'parts'/(name+'.png')).convert('RGBA')
 if flip:im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 if size and tuple(size)!=im.size:im=im.resize(tuple(size),Image.Resampling.LANCZOS)
 canvas.alpha_composite(im,tuple(xy));manifest.append({'name':name,'file':'parts/'+name+'.png','globalPosition':xy,'size':list(im.size),'flipHorizontal':flip})
for name in ['hair_back']+ears:add(name,pos[name])
for layer in assembly['layers']:add(layer['name'],[origin[0]+layer['pos'][0],origin[1]+layer['pos'][1]],layer['flip'],layer['size'])
for name in hair[1:]:add(name,pos[name])
crop=(1450,70,2560,1240);head=canvas.crop(crop);head.save(HEAD/'preview/head_sample.png')
def bg(im):
 c=Image.new('RGBA',im.size,(80,105,110,255));c.alpha_composite(im);return c.convert('RGB')
bg(head).save(HEAD/'preview/head_sample_gray.png')
original=Image.open(HEAD/'reference/ren-stand-pony-front-4000x6000.png').convert('RGBA')
font=ImageFont.truetype('C:/Windows/Fonts/meiryo.ttc',26)
def compare(images,size,path):
 w,h=size;c=Image.new('RGB',(w*2,h+52),(58,63,67));d=ImageDraw.Draw(c)
 for i,(im,label) in enumerate(zip(images,['原画','最新パーツ：下まぶた修正＋髪・耳'])):
  c.paste(bg(im).resize(size,Image.Resampling.LANCZOS),(i*w,52));d.text((i*w+14,10),label,font=font,fill='white')
 c.save(path,quality=98)
compare([original.crop(crop),head],(666,702),HEAD/'preview/comparison_original.jpg')
detail=(1650,650,2350,1190)
compare([original.crop(detail),canvas.crop(detail)],(840,648),HEAD/'preview/comparison_face_detail.jpg')
for layer in manifest:layer['previewPosition']=[layer['globalPosition'][0]-crop[0],layer['globalPosition'][1]-crop[1]]
record={'status':'current_png_head_assembly_preview_not_final_rig','canvas':list(head.size),'globalCrop':crop,'faceOrigin':origin,'layers':manifest,'sources':provenance,'sourcesUnchanged':all(sha(Path(x['source']))==x['sha256'] for x in provenance),'collectedFilesMatch':all(sha(HEAD/x['file'])==x['sha256'] for x in provenance),'activePartCount':len(manifest),'referenceOnly':['reference/'],'note':'Original drawing used only for visual comparison. Face from v007 latest 14 PNG; current hair/ears explicitly authorized. All scale and positions recorded.'}
assert record['sourcesUnchanged'] and record['collectedFilesMatch'] and record['activePartCount']==23
(HEAD/'assembly.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:record[k] for k in ['canvas','faceOrigin','activePartCount','sourcesUnchanged','collectedFilesMatch']},ensure_ascii=False))
