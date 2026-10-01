"""Read only frozen CMO3; local-coordinate diagnostics are NOT Cubism renders."""
import sys, json, hashlib, itertools, math, subprocess, os, traceback
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[2]
REPO = MODEL.parents[1]
sys.path.insert(0, str(MODEL / 'model/training_base_audit'))
from audit_cmo3 import Cmo

def sha(b): return hashlib.sha256(b).hexdigest()
def save(name, obj): (HERE/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf8')
c = Cmo(HERE/'Ren_base3_review.cmo3')
base = json.loads((HERE/'baseline.json').read_text())
assert sha(c.data) == base['sha256']
s = c.summarize()
objects = {c.name(x): x for tag in ('CArtMeshSource','CWarpDeformerSource','CRotationDeformerSource') for x in c.objects(tag)}
items = {x['name']:x for x in s['meshes']+s['deformers']}
guidnames = {c.val(x.find('ACDrawableSource'),'guid'): c.name(x) for x in c.objects('CArtMeshSource')}
parts = []
for x in c.objects('CPartSource'):
    ctl = next(x.iter('ACParameterControllableSource'))
    g = c.field(ctl,'keyformGridSource')
    parts.append(dict(name=c.name(x), visible=c.val(ctl,'isVisible'), bindings=[c.binding(b) for b in c.field(g,'keyformBindings')], forms=c.forms(x)))
s['parts'] = parts
raw = {}
usage = {k:[] for k in s['parameters']}
grid_checks = []
for name,x in items.items():
    obj = objects[name]; ctl = next(obj.iter('ACParameterControllableSource')); grid = c.field(ctl,'keyformGridSource')
    x['interpolation'] = [{**c.binding(b),'type':c.val(c.res(b),'interpolationType'),'extended':c.val(c.res(b),'extendedInterpolationType')} for b in c.field(grid,'keyformBindings')]
    for b in x['bindings']: usage[b['parameter']].append(name)
    forms = {}
    for f0 in c.field(obj,'keyforms'):
        f = c.res(f0); guid = c.val(next(f.iter('CFormGuid')))
        arrays = {q.get('xs.n'):np.fromstring(q.text or '', sep=' ').reshape(-1,2) for q in f.iter('float-array') if q.get('xs.n') in ('positions','points','point')}
        forms[guid] = arrays
    raw[name] = forms
    keys = [b['parameter'] for b in x['bindings']]
    combos = {tuple(dict(k['keys'])[p] for p in keys) for k in x['grid']}
    expected = set(itertools.product(*(b['keys'] for b in x['bindings'])))
    grid_checks.append(dict(name=name,expected=len(expected),actual=len(x['grid']),missing=list(expected-combos),duplicate_count=len(x['grid'])-len(combos),unresolved_forms=[k['form'] for k in x['grid'] if k['form'] not in forms]))
    x['clips_names'] = [guidnames.get(g,g) for g in x.get('clips',[])]
    fs = {f['guid']:f for f in x['forms']}
    x['key_values'] = [dict(parameters=dict(k['keys']),opacity=fs[k['form']].get('opacity'),draw_order=fs[k['form']].get('drawOrder'),geometry_sha256=fs[k['form']].get('positions_sha256',fs[k['form']].get('points_sha256'))) for k in x['grid']]
save('inventory.json',s)

copies=json.loads((MODEL/'art/latest_png_collection/copies.json').read_text(encoding='utf8'))
assets=[]
for mesh in s['meshes']:
    matches=[]
    for cp in copies:
        p=Path(cp['copy_path']);im=Image.open(p).convert('RGBA')
        if list(im.size)==mesh['image']['size'] and sha(im.tobytes())==mesh['image']['rgba_sha256']:
            matches.append(dict(copy=str(p),source=cp['source_path'],copy_bytes_unchanged=sha(p.read_bytes())==cp['sha256'],source_bytes_equal=Path(cp['source_path']).read_bytes()==p.read_bytes()))
    assets.append(dict(mesh=mesh['name'],image=mesh['image'],matches=matches))
save('active_image_comparison.json',assets)

def evaluate(name,values):
    """Multilinear local-keyform evaluation; hide outside keyed interval. No Core."""
    x=items[name]; axes=[]
    for b in x['bindings']:
        v=values.get(b['parameter'],s['parameters'][b['parameter']]['default']);ks=b['keys']
        if v<min(ks)-1e-9 or v>max(ks)+1e-9:return None,0
        exact=next((k for k in ks if abs(k-v)<1e-9),None)
        if exact is not None: axes.append([(b['parameter'],exact,1.)]);continue
        low=max(k for k in ks if k<v);high=min(k for k in ks if k>v);w=(v-low)/(high-low)
        axes.append([(b['parameter'],low,1-w),(b['parameter'],high,w)])
    points=None;opacity=0.;fs={f['guid']:f for f in x['forms']}
    for combo in itertools.product(*axes):
        wanted={p:v for p,v,w in combo};weight=math.prod(w for p,v,w in combo)
        k=next(k for k in x['grid'] if dict(k['keys'])==wanted);arr=raw[name][k['form']]
        a=arr.get('positions',arr.get('points',arr.get('point')))
        if a is not None:points=weight*a if points is None else points+weight*a
        opacity+=weight*fs[k['form']].get('opacity',1.)
    return points,opacity

# Geometry changes along each authored axis, independent of upstream deformation.
axis_changes=[]
for name,x in items.items():
    for b in x['bindings']:
        other=[q for q in x['bindings'] if q is not b]
        for vals in itertools.product(*(q['keys'] for q in other)):
            fixed={q['parameter']:v for q,v in zip(other,vals)};arr=[]
            for v in b['keys']:
                p,op=evaluate(name,fixed|{b['parameter']:v});arr.append((p,op))
            delta=max((float(np.max(np.linalg.norm(p-arr[0][0],axis=1))) for p,_ in arr if p is not None and arr[0][0] is not None),default=0)
            axis_changes.append(dict(name=name,parameter=b['parameter'],fixed=fixed,max_local_vertex_delta_from_first=delta,opacity_values=[op for _,op in arr]))
save('axis_changes.json',axis_changes)

boundary=[]
for side in ['L','R']:
    for smile in [0,.25,.5,.75,1]:
        for op in [0,.025,.0499,.05,.0501,.075,.1,.125,.1499,.15,.1501,.25,.5,.75,1]:
            vals={f'ParamEye{side}Open':op,f'ParamEye{side}Smile':smile}
            row=dict(side=side,open=op,smile=smile)
            for name in [f'eyelash_closed_{side}',f'ALT_eyelash_upper_{side}',f'FILL_eye_white_{side}','lower_eyelid_left' if side=='L' else 'lower_eyelid_right']:
                _,alpha=evaluate(name,vals);row[name]=alpha
            boundary.append(row)
save('eye_boundary_samples.json',boundary)

# Render textures on local ArtMesh triangles. Parent warp, final canvas, Core,
# blend colors, and application clipping implementation are intentionally absent.
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
texture_data={}
for name,x in items.items():
    if x['type']!='CArtMeshSource':continue
    obj=objects[name];ext=c.res(next(obj.iter('CTextureInputExtension')));inp=c.field(ext,'currentTextureInputData');mi=c.images[c.val(inp,'_modelImageGuid')]
    tex=c.image(mi);edit=next(obj.iter('GEditableMesh2'));uv=np.fromstring(c.field(edit,'point').text,sep=' ').reshape(-1,2)
    a=c.field(mi,'_materialLocalToCanvasTransform').attrib
    transform=np.array([[float(a['m00']),float(a['m01'])],[float(a['m10']),float(a['m11'])]])
    uv=(uv-np.array([float(a['m02']),float(a['m12'])])) @ np.linalg.inv(transform).T
    tri=np.fromstring(c.field(obj,'indices').text,sep=' ',dtype=int).reshape(-1,3)
    texture_data[name]=(tex,uv,tri)

def raster(name,values,size=(240,220)):
    points,opacity=evaluate(name,values);canvas=Image.new('RGBA',size)
    if points is None:return canvas,opacity
    tex,uv,tris=texture_data[name]
    dst=np.column_stack(((points[:,0]+.15)/1.45*size[0],(points[:,1]+.1)/1.35*size[1]))
    for tri in tris:
        xy=dst[tri];matrix=np.column_stack((xy,np.ones(3)))
        if abs(np.linalg.det(matrix))<1e-8:continue
        affine=np.linalg.solve(matrix,uv[tri]).T.flatten()
        patch=tex.transform(size,Image.Transform.AFFINE,affine,Image.Resampling.BILINEAR)
        mask=Image.new('L',size);ImageDraw.Draw(mask).polygon([tuple(p) for p in xy],fill=255)
        canvas.paste(patch,(0,0),mask)
    return canvas,opacity

def eye(side,opening,smile,other=1):
    vals={f'ParamEye{side}Open':opening,f'ParamEye{side}Smile':smile,f'ParamEye{"R" if side=="L" else "L"}Open':other}
    names=[f'FILL_eye_white_{side}',f'ALT_iris_{side}_{"blue" if side=="L" else "brown"}', 'lower_eyelid_left' if side=='L' else 'lower_eyelid_right',f'ALT_eyelash_upper_{side}',f'eyelash_closed_{side}']
    layers={n:raster(n,vals) for n in names};result=Image.new('RGBA',(240,220),(232,218,206,255))
    for n in names:
        im,opacity=layers[n];im=im.copy();alpha=im.getchannel('A')
        for clip in items[n]['clips_names']:
            if clip in layers:alpha=ImageChops.multiply(alpha,layers[clip][0].getchannel('A'))
        im.putalpha(alpha.point(lambda v:round(v*opacity)));result.alpha_composite(im)
    out=Image.new('RGB',(240,248),(248,247,244));out.paste(result.convert('RGB'),(0,28));ImageDraw.Draw(out).text((6,5),f'{side} open={opening:g} smile={smile:g}',font=font,fill='black');return out

sheet=Image.new('RGB',(1440,1556),'white');d=ImageDraw.Draw(sheet)
d.text((12,8),'LOCAL ArtMesh texture diagnostic ONLY - no parent warp / Cubism / final visual acceptance',font=font,fill='black')
d.text((12,30),'Linear keys; key-range hiding; white-alpha clipping. Numeric smile labels do not assert expression meaning.',font=font,fill='black')
for row,(side,smile) in enumerate(itertools.product(['L','R'],[0,.5,1])):
    for col,op in enumerate([0,.05,.1,.15,.5,1]):sheet.paste(eye(side,op,smile),(col*240,68+row*248))
sheet.save(HERE/'eye_local_diagnostic.png')

iris_metrics=[]
for side in ['L','R']:
    name=f'ALT_iris_{side}_{"blue" if side=="L" else "brown"}'
    for op in [0,.05,.1,.15,.25,.5,.75,1]:
        vals={f'ParamEye{side}Open':op}
        points,_=evaluate(name,vals)
        iris_metrics.append(dict(side=side,open=op,local_bbox=[*points.min(0),*points.max(0)],local_height=float(np.ptp(points[:,1])),local_width=float(np.ptp(points[:,0]))))
save('iris_local_metrics.json',iris_metrics)

# Brown iris: own-open=1 affine fit and triangle orientation across 101 values.
# This isolates local nonlinear deformation, but not parent-warp compensation.
distortion=[]
for side in ['L','R']:
    name=f'ALT_iris_{side}_{"blue" if side=="L" else "brown"}'
    ref,_=evaluate(name,{f'ParamEye{side}Open':1})
    tri=texture_data[name][2]
    def areas(p):
        a=p[tri[:,1]]-p[tri[:,0]];b=p[tri[:,2]]-p[tri[:,0]]
        return a[:,0]*b[:,1]-a[:,1]*b[:,0]
    a0=areas(ref);design=np.column_stack((ref,np.ones(len(ref))))
    for opening in np.linspace(0,1,101):
        points,_=evaluate(name,{f'ParamEye{side}Open':float(opening)})
        fit=design @ np.linalg.lstsq(design,points,rcond=None)[0]
        residual=np.linalg.norm(points-fit,axis=1);area=areas(points)
        distortion.append(dict(side=side,open=round(float(opening),4),local_height_ratio_to_own_open1=float(np.ptp(points[:,1])/np.ptp(ref[:,1])),local_affine_residual_rms=float(np.sqrt(np.mean(residual**2))),local_affine_residual_max=float(residual.max()),triangle_sign_changes_vs_open1=int(np.count_nonzero((a0*area)<-1e-12)),near_zero_local_triangles=int(np.count_nonzero(np.abs(area)<1e-9))))
save('iris_deformation_scan.json',distortion)
unmasked=Image.new('RGB',(1280,640),'white');ud=ImageDraw.Draw(unmasked)
ud.text((10,10),'UNMASKED iris local diagnostic; no parent compensation. Fixed local axes per tile; cropping is diagnostic.',font=font,fill='black')
for row,side in enumerate(['L','R']):
    name=f'ALT_iris_{side}_{"blue" if side=="L" else "brown"}'
    for col,op in enumerate([0,.05,.1,.15,.25,.5,.75,1]):
        # Expanded Y domain preserves all keyed iris points, never rescales each pose.
        points,_=evaluate(name,{f'ParamEye{side}Open':op}); tex,uv,tris=texture_data[name]
        dst=np.column_stack(((points[:,0]+.05)/1.1*160,(points[:,1]+.9)/2.5*270))
        canvas=Image.new('RGBA',(160,270))
        for tri in tris:
            xy=dst[tri];matrix=np.column_stack((xy,np.ones(3)))
            if abs(np.linalg.det(matrix))<1e-8:continue
            affine=np.linalg.solve(matrix,uv[tri]).T.flatten();patch=tex.transform(canvas.size,Image.Transform.AFFINE,affine,Image.Resampling.BILINEAR)
            mask=Image.new('L',canvas.size);ImageDraw.Draw(mask).polygon([tuple(p) for p in xy],fill=255);canvas.paste(patch,(0,0),mask)
        tile=Image.new('RGB',(160,296),(232,218,206));tile.paste(canvas,(0,26),canvas);ImageDraw.Draw(tile).text((5,5),f'{side} open={op:g}',font=font,fill='black');unmasked.paste(tile,(col*160,42+row*296))
unmasked.save(HERE/'iris_unmasked_local.png')

# Actual embedded source pixels, separate from posed model evaluation.
face_obj=objects['face_underfill'];ext=c.res(next(face_obj.iter('CTextureInputExtension')));mi=c.images[c.val(c.field(ext,'currentTextureInputData'),'_modelImageGuid')]
face=c.image(mi);face.thumbnail((650,650));source=Image.new('RGB',(720,730),(235,231,225));source.paste(face,((720-face.width)//2,60),face);ImageDraw.Draw(source).text((12,15),'Embedded face_underfill source pixels - NOT posed model',font=font,fill='black');source.save(HERE/'face_source.png')

attempt=subprocess.run([sys.executable,'-B',str(HERE.parent/'render_preview.py')],capture_output=True,text=True)
runtime=dict(command=[sys.executable,'-B',str(HERE.parent/'render_preview.py')],returncode=attempt.returncode,stdout=attempt.stdout,stderr=attempt.stderr,expected_model_json_exists=(HERE.parent/'runtime/Ren_base.model3.json').exists(),available_current_moc3=[str(p) for p in HERE.parent.rglob('*.moc3')],atlas_count=s['atlas_count'],gui_tool='Computer-use skill read; required node_repl/@oai/sky not exposed in this environment',process_query='Get-Process Cubism|Live2D returned no rows; does not prove user desktop has no Editor')
save('runtime_attempt.json',runtime)
os.environ['GIT_OPTIONAL_LOCKS']='0'
preservation=dict(source_sha256_at_end=sha(Path(base['source']).read_bytes()),snapshot_unchanged=sha((HERE/'Ren_base3_review.cmo3').read_bytes())==base['sha256'],index_bytes_unchanged=sha((REPO/'.git/index').read_bytes())==base['index_sha256'],index_entries_unchanged=sha(subprocess.check_output(['git','--no-optional-locks','ls-files','-s','-z'],cwd=REPO))==base['index_entries_sha256'],changed_protected_pngs=[p for p,h in base['protected_files'].items() if sha(Path(p).read_bytes())!=h])
result=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),source_sha256=base['sha256'],counts=dict(meshes=len(s['meshes']),deformers=len(s['deformers']),parameters=len(s['parameters']),parts=len(parts),physics_groups=len(s['physics'])),active_png_matches=sum(bool(x['matches']) for x in assets),parameter_bindings=usage,unbound_parameters=[p for p,n in usage.items() if not n],grid_checks=grid_checks,actual_cubism_render_completed=False,local_diagnostic_only=True,official_key_range_reference='https://docs.live2d.com/cubism-editor-manual/clipping-mask/',preservation=preservation)
save('verification.json',result)
print(json.dumps({k:v for k,v in result.items() if k not in ('parameter_bindings','grid_checks')},ensure_ascii=True,indent=2))
