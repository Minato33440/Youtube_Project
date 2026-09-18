from pathlib import Path
import json, hashlib, shutil, zipfile
from datetime import datetime, timezone
from PIL import Image

root = Path('C:/Users/Setona/Desktop/AI Works/Youtube-Project/Live-2D')
assets = root / 'Illust_Image'
previous = Path('C:/Python/REX_AI/Youtube_Project/output/live2d/risa_parts_v1')
dest = root / 'v2'
dest.mkdir(exist_ok=True)
stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
snapshots = root / '_snapshots'
snapshots.mkdir(exist_ok=True)
model_source = previous / 'Risa_Live2D_Parts_v2.cmo3'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
snapshot = snapshots / f'v2_before_registration_{stamp}.zip'
with zipfile.ZipFile(snapshot, 'x', zipfile.ZIP_DEFLATED) as z:
    for p in assets.glob('*.png'): z.write(p, 'Illust_Image/' + p.name)
    z.write(model_source, 'Risa_Live2D_Parts_v2.cmo3')
with zipfile.ZipFile(snapshot) as z: assert z.testzip() is None

supplemented = []
for name in ['Brow_ViewerLeft.png','Brow_ViewerRight.png']:
    target = assets / name
    if not target.exists():
        source = previous / 'parts' / name
        shutil.copy2(source, target)
        assert digest(source) == digest(target)
        supplemented.append({'name':name,'source':str(source),'sha256':digest(target)})

model_target = dest / model_source.name
if model_target.exists() and digest(model_target) != digest(model_source):
    raise RuntimeError('Existing v2 model differs; will not overwrite')
shutil.copy2(model_source, model_target)
assert digest(model_target) == digest(model_source)

# Keep the earlier revised ears as alternatives, never substitute for the user's chosen directory.
variants = dest / 'variants' / 'previous_model_ears'
variants.mkdir(parents=True,exist_ok=True)
for name in ['Ear_ViewerLeft.png','Ear_ViewerRight.png']:
    source = previous / 'parts' / name
    shutil.copy2(source,variants/name)

references = {'Risa-Base.png','Risa-front.png'}
intermediates = {'Head_Skin_Nose_Ears_Neck.png','Head_Skin_Nose_Ears_Neck-2.png'}
rows=[]
for p in sorted(assets.glob('*.png')):
    with Image.open(p) as im:
        im.load()
        rgba=im.convert('RGBA')
        alpha=rgba.getchannel('A')
        rows.append({'file':'../Illust_Image/'+p.name,'id':p.name.removesuffix('.png').removesuffix('.png'),
            'role':'reference' if p.name in references else 'intermediate' if p.name in intermediates else 'part',
            'width':im.width,'height':im.height,'mode':im.mode,'alpha_extrema':alpha.getextrema(),
            'sha256':digest(p)})
manifest={'version':'v2','registered_at':datetime.now(timezone.utc).isoformat(),
    'authoritative_artwork_directory':str(assets),
    'authoritative_layout_model':'Risa_Live2D_Parts_v2.cmo3',
    'model_sha256':digest(model_target),'model_operation':'byte-identical copy of user model; no texture replacement or rigging',
    'inventory_only':True,'layout_coordinates':None,
    'important':'PNG filenames are source records, not proof of a live external link. Cubism embedded artwork and layout remain as saved by user.',
    'supplemented':supplemented,'assets':rows,
    'ear_policy':{'choice':'separate ear artmeshes with foreground hair overlap','merge_ear_into_hair':False,
        'current_source_size':[35,45],'previous_revised_source_size':[57,74],
        'previous_revised_sources':'variants/previous_model_ears','model_texture_synchronization':'not performed'},
    'filename_aliases':{'Hair_Front_Left_Pin.png.png':'Hair_Front_Left_Pin'},
    'pre_registration_snapshot':str(snapshot)}
(dest/'assets_v2.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'model':str(model_target),'assets':len(rows),'parts':sum(r['role']=='part' for r in rows),'supplemented':supplemented,'snapshot':str(snapshot)},ensure_ascii=False,indent=2))
