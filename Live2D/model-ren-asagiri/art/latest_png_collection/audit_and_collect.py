"""Read-only source audit; writes only new deliverables under this directory.
Run with python -B. Refuses to overwrite a completed run.
"""
import sys, os, json, hashlib, struct, io, shutil
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timezone
sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
ART = OUT.parent
MODEL = ART.parent
REPO = MODEL.parents[1]
sys.path.insert(0, str(MODEL / 'model/training_base_audit'))
from audit_cmo3 import Cmo
from PIL import Image, ImageDraw
import numpy as np

def sha(b): return hashlib.sha256(b).hexdigest()
def filehash(p): return sha(p.read_bytes())
def rel(p): return p.relative_to(ART).as_posix()
def save(name, obj):
    with (OUT/name).open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
def pixels(im):
    im=im.convert('RGBA'); a=np.asarray(im); alpha=a[:,:,3]
    raw=im.tobytes(); prefix=struct.pack('>II', *im.size)
    v=a.copy(); v[alpha==0,:3]=0
    return dict(size=list(im.size), rgba_sha256=sha(raw),
        dimension_rgba_sha256=sha(prefix+raw), visible_rgba_sha256=sha(prefix+v.tobytes()),
        alpha_min=int(alpha.min()),alpha_max=int(alpha.max()),
        transparent_pixels=int((alpha==0).sum()), partial_alpha_pixels=int(((alpha>0)&(alpha<255)).sum()),
        alpha_bbox=im.getchannel('A').getbbox())

def run():
    if (OUT/'inventory.json').exists(): raise RuntimeError('Completed output already exists; choose a new directory')
    model=MODEL/'model/base_motion/Ren_base3.cmo3'
    index=REPO/'.git/index'
    before_model=filehash(model); before_index=filehash(index)
    c=Cmo(model)
    snapshot=[]; errors=[]; skipped=[]
    for folder,dirs,names in os.walk(ART, followlinks=False, onerror=lambda e:errors.append(dict(path=e.filename,error=str(e)))):
        dirs[:]=[d for d in dirs if Path(folder)/d!=OUT]
        for d in list(dirs):
            p=Path(folder)/d
            if p.is_symlink() or p.is_junction(): dirs.remove(d); skipped.append(str(p))
        for name in names:
            if name.lower().endswith('.png'): snapshot.append(Path(folder)/name)
    snapshot.sort()
    rows=[]; cache={}
    for p in snapshot:
        row=dict(source_path=str(p),art_relative_path=rel(p),copy_path=None,model_matches=[],review_reasons=[])
        try:
            data=p.read_bytes(); h=sha(data); row.update(sha256=h,bytes=len(data),mtime_ns=p.stat().st_mtime_ns)
            if h not in cache:
                with Image.open(io.BytesIO(data)) as im:
                    info=pixels(im); info['original_mode']=im.mode; info['frames']=getattr(im,'n_frames',1)
                    cache[h]=info
            row.update(cache[h])
            if row['alpha_max']==0: row['review_reasons'].append('fully_transparent')
            if row['alpha_min']==255: row['review_reasons'].append('fully_opaque_review_if_cutout')
            if row['frames']!=1: row['review_reasons'].append('animated_png_not_static_equivalence')
        except Exception as e:row['review_reasons'].append('read_or_decode_error: '+str(e))
        rows.append(row)
    meshes=defaultdict(list)
    for x in c.objects('CArtMeshSource'):
        ext=c.res(next(x.iter('CTextureInputExtension'),None))
        guid=c.val(c.field(ext,'currentTextureInputData'),'_modelImageGuid')
        src=x.find('ACDrawableSource')
        meshes[guid].append(dict(name=c.name(x),id=c.val(src,'id')))
    images=[]; decoded={}
    for guid,mi in c.images.items():
        resource=c.field(mi,'_filteredImage'); f=next(resource.iter('file'),None) if resource is not None else None
        row=dict(guid=guid,name=c.val(mi,'name'),meshes=meshes.get(guid,[]),active=bool(meshes.get(guid)),
                 embedded_entry=f.get('path') if f is not None else None,candidates=[],selected_source=None,review_reasons=[])
        try:
            data=c.entry(f.get('path')); im=Image.open(io.BytesIO(data)).convert('RGBA'); decoded[guid]=im
            row.update(pixels(im));row['embedded_byte_sha256']=sha(data)
            for r in rows:
                if r.get('dimension_rgba_sha256')==row['dimension_rgba_sha256'] and r.get('frames')==1:
                    match=dict(image_guid=guid,image_name=row['name'],active=row['active'],mesh_ids=[m['id'] for m in row['meshes']],
                               evidence='embedded_bytes_equal' if r['sha256']==row['embedded_byte_sha256'] else 'exact_dimensions_and_decoded_RGBA')
                    r['model_matches'].append(match);row['candidates'].append(r['art_relative_path'])
            if row['active']:
                # Evidence establishes image equality; current source directories establish source authority.
                name=row['name']+'.png'
                preferences=['head/parts/'+name,'expression_rig/parts/'+name,'processing_v001/front/parts/'+name]
                selected=next((p for p in preferences if p in row['candidates']),None)
                if selected:row.update(selected_source=selected,selection_reason='Exact RGBA plus user-designated/current source directory and material name')
                elif len(row['candidates'])==1 and not any(s in row['candidates'][0].split('/') for s in ('archive','backup','buckup')):
                    row.update(selected_source=row['candidates'][0],selection_reason='Unique non-archive exact RGBA candidate')
                else:row['review_reasons'].append('no_authoritative_exact_source' if row['candidates'] else 'no_exact_RGBA_match_in_art')
                row['name_only_candidates']=[r['art_relative_path'] for r in rows if Path(r['source_path']).stem==row['name'] and r['art_relative_path'] not in row['candidates']]
                row['visible_only_candidates']=[r['art_relative_path'] for r in rows if r.get('visible_rgba_sha256')==row['visible_rgba_sha256'] and r['art_relative_path'] not in row['candidates']]
        except Exception as e:row['review_reasons'].append('embedded_decode_error: '+str(e))
        images.append(row)
    bypath={r['art_relative_path']:r for r in rows}
    selected={i['selected_source'] for i in images if i['selected_source']}
    copies=[]
    for source in sorted(selected):
        r=bypath[source];p=Path(r['source_path']);dest=OUT/'confirmed_png'/source
        dest.parent.mkdir(parents=True,exist_ok=True)
        if filehash(p)!=r['sha256']:raise RuntimeError('Source changed before copy: '+source)
        with dest.open('xb') as f:f.write(p.read_bytes())
        r['copy_path']=str(dest)
        copies.append(dict(source_path=str(p),copy_path=str(dest),sha256=r['sha256'],bytes=r['bytes'],model_matches=r['model_matches'],
                           evidence='original source bytes copied; exact embedded decoded RGBA',verified=filehash(dest)==r['sha256']))
    bytegroups=defaultdict(list); pixelgroups=defaultdict(list)
    for r in rows:
        if 'sha256' in r:bytegroups[r['sha256']].append(r)
        if 'dimension_rgba_sha256' in r:pixelgroups[r['dimension_rgba_sha256']].append(r)
        active=[m for m in r['model_matches'] if m['active']]
        r['classification']='selected_active_source' if r['copy_path'] else 'active_image_equivalent_alternative' if active else 'embedded_unused_image_match' if r['model_matches'] else 'no_exact_match_to_model_images'
        if not active:r['review_reasons'].append('not_matched_to_current_mesh_texture_not_a_deletion_decision')
    duplicates=[dict(sha256=h,bytes_each=rs[0]['bytes'],paths=[r['source_path'] for r in rs],potential_redundant_bytes=rs[0]['bytes']*(len(rs)-1),
                     caution='Identical bytes do not prove redundant role; keep source/runtime/recovery references') for h,rs in bytegroups.items() if len(rs)>1]
    pixelduplicates=[dict(dimension_rgba_sha256=h,paths=[r['source_path'] for r in rs],byte_hashes=sorted(set(r['sha256'] for r in rs)),
                          reason='Same decoded RGBA; encoding/metadata differs, not necessarily metadata only') for h,rs in pixelgroups.items() if len(set(r['sha256'] for r in rs))>1]
    sources=[{q.get('xs.n'):c.val(q) for q in x if q.tag in ('s','file')} for x in c.objects('CLayeredImage')]
    # Read-only source references can be stale; never rewrite the model or recover by old path alone.
    for s in sources:
        p=Path(s.get('psdFile',''));s['exists_now']=p.exists();s['inside_art']=p.is_relative_to(ART);s['historical_import_reference_not_live_link']=True
    unchanged=[]
    for r in rows:
        if 'sha256' in r and filehash(Path(r['source_path']))!=r['sha256']:unchanged.append(r['source_path'])
    verify=dict(all_original_png_hashes_unchanged=not unchanged,changed_sources=unchanged,model_hash_unchanged=filehash(model)==before_model,
                git_index_hash_unchanged=filehash(index)==before_index,index_sha256=before_index,all_copy_hashes_equal=all(x['verified'] for x in copies),
                scan_errors=errors,skipped_reparse=skipped,scope='All enumerable art PNGs before new output; all 59 embedded model images; current texture links of 48 ArtMeshes; no GUI/rendered rig validation')
    summary=dict(checked_utc=datetime.now(timezone.utc).isoformat(),model_path=str(model),model_sha256=before_model,model_bytes=model.stat().st_size,
                 model_mtime_utc=datetime.fromtimestamp(model.stat().st_mtime,timezone.utc).isoformat(),png_count=len(rows),png_bytes=sum(r.get('bytes',0) for r in rows),
                 embedded_images=len(images),active_images=sum(i['active'] for i in images),mesh_count=sum(len(m) for m in meshes.values()),
                 confirmed_copies=len(copies),copy_bytes=sum(x['bytes'] for x in copies),unresolved_active=[i['name'] for i in images if i['active'] and not i['selected_source']],
                 byte_duplicate_groups=len(duplicates),byte_duplicate_paths=sum(len(g['paths']) for g in duplicates),same_pixels_different_bytes_groups=len(pixelduplicates),
                 classifications=dict(Counter(r['classification'] for r in rows)),read_errors=sum('read_or_decode_error' in ' '.join(r['review_reasons']) for r in rows))
    save('inventory.json',dict(schema_version=1,summary=summary,pngs=rows,model_images=images,model_import_sources=sources))
    save('duplicates.json',dict(exact_byte_groups=duplicates,same_pixels_different_bytes=pixelduplicates,deletion_authorized=False))
    save('copies.json',copies);save('verification.json',verify)
    # QA thumbnails are separate illustrations, never substitutes for original PNG copies.
    active=[i for i in images if i['active']]
    for start in range(0,len(active),24):
        page=active[start:start+24];sheet=Image.new('RGB',(1200,((len(page)+5)//6)*200),(210,210,210));d=ImageDraw.Draw(sheet)
        for j,r in enumerate(page):
            x=(j%6)*200;y=(j//6)*200
            for yy in range(y,y+170,10):
                for xx in range(x,x+200,10):d.rectangle((xx,yy,xx+9,yy+9),fill=(235,235,235) if ((xx//10+yy//10)%2) else (185,185,185))
            im=decoded[r['guid']].copy();im.thumbnail((190,160));sheet.paste(im,(x+(200-im.width)//2,y+(170-im.height)//2),im)
            d.text((x+3,y+171),r['name'],fill='black');d.text((x+3,y+185),'MATCH' if r['selected_source'] else 'REVIEW',fill='black')
        sheet.save(OUT/f'qa_active_{start//24+1}.jpg')
    print(json.dumps(summary,ensure_ascii=True));print(json.dumps(verify,ensure_ascii=True))

if __name__=='__main__':run()
