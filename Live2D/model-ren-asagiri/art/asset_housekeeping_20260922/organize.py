from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
PARTS=(ROOT/'art/eye_adjust_v007/parts').resolve()
ARCHIVE=PARTS/'archive/20260922-initial-eye-layers'
names=['eye_white_L.png','eye_white_R.png','iris_L.png','iris_R.png','lower_lid_L.png','lower_lid_R.png','REF_lower_lid_source_L.png','REF_lower_lid_source_R.png']
roles={'face_base':'face_underfill.png','brow_L':'brow_L.png','brow_R':'brow_R.png','upper_lash_L':'ALT_eyelash_upper_L.png','upper_lash_R':'ALT_eyelash_upper_R.png','iris_L':'ALT_iris_L_blue.png','iris_R':'ALT_iris_R_brown.png','eye_white_L':'FILL_eye_white_L.png','eye_white_R':'FILL_eye_white_R.png','lower_eyelid_L':'lower_eyelid_left.png','lower_eyelid_R':'lower_eyelid_right.png','orbital_line_L':'upper_crease_L.png','orbital_line_R':'upper_crease_R.png','mouth_closed':'mouth_closed.png'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def within(p):
 resolved=p.resolve();assert resolved.is_relative_to(PARTS),str(resolved);return resolved
active=list(roles.values())+['facial_feature.png','facial_feature.psd']
before={n:sha(PARTS/n) for n in active}
for n in names:
 assert (PARTS/n).is_file(),n
 assert not (ARCHIVE/n).exists(),n
within(ARCHIVE);ARCHIVE.mkdir(parents=True)
record={'canonicalParts':str(PARTS),'moved':[],'deleted':[],'activeHashesBefore':before}
for n in names:
 src=within(PARTS/n);dst=within(ARCHIVE/n);h=sha(src)
 shutil.move(str(src),str(dst));assert sha(dst)==h
 record['moved'].append({'from':str(src),'to':str(dst),'sha256':h,'reason':'Superseded initial render or original-art reference; keep for comparison'})
# Preserve the old manifest verbatim, then repair paths only; it remains historical.
mp=PARTS.parent/'manifest.json';shutil.copy2(mp,ARCHIVE/'manifest_before_organization.json');manifest=json.loads(mp.read_text(encoding='utf8'))
for layer in manifest['layers']:
 path=Path(layer['path']);name=path.name
 if name in names:layer['path']='parts/archive/20260922-initial-eye-layers/'+name
 elif not (mp.parent/path).exists() and (PARTS/'backup'/name).is_file():layer['path']='parts/backup/'+name
manifest['status']='historical_initial_layout_not_current'
manifest['note']='Paths repaired after organization. Shared filenames were manually revised; do not use this manifest as the current assembly. Use parts/current_parts.json and inspect facial_feature.psd transforms.'
mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
assert all((mp.parent/l['path']).is_file() for l in manifest['layers'])
# Redundant preview only: retained artifact exists and is byte-identical. Read both again immediately before removal.
duplicate=within(PARTS/'comparison_4_horizontal.jpg')
retained=(ROOT/'art/face_comparison_v010/comparison_4_horizontal.jpg').resolve()
assert duplicate!=retained and retained.is_file()
assert duplicate.stat().st_size==retained.stat().st_size and sha(duplicate)==sha(retained)
assert duplicate.read_bytes()==retained.read_bytes()
h=sha(duplicate);size=duplicate.stat().st_size
duplicate.unlink();assert retained.is_file() and sha(retained)==h and not duplicate.exists()
record['deleted'].append({'path':str(duplicate),'retained':str(retained),'sha256':h,'bytes':size,'reason':'Exact duplicate preview; no parts-path references found in repository text search; independent retained copy verified again'})
current={'status':'canonical_current_face_parts','sourceOfTruth':'Individual PNG files in this directory, as explicitly designated by Boss; folder version numbers do not indicate priority.','roles':roles,'placementReference':{'png':'facial_feature.png','psd':'facial_feature.psd','note':'Reference for positions and transforms, not guaranteed to contain the latest individual pixels. Replace outdated embedded base. L lower eyelid uses reflection and transformation.'},'excludeFromInput':['backup/','archive/'],'previousVersions':'backup/YYYYMMDD-HHMMSS/','policy':'README.md'}
(PARTS/'current_parts.json').write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
record['activeHashesAfter']={n:sha(PARTS/n) for n in active}
assert record['activeHashesBefore']==record['activeHashesAfter']
record['activeUnchanged']=True;record['historicalManifestPathsExist']=True
(OUT/'organization.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(ARCHIVE/'README.md').write_text('# 旧v007生成素材と原画参照\n\n2026-09-22に最新素材の置き場から退避。初期生成の白目・虹彩・下まぶた6枚と原画参照2枚。削除せず比較用に保持。manifest_before_organization.jsonは整理前の記録であり、現在の配置・再生成には使用しない。\n',encoding='utf8')
print(json.dumps({'moved':len(record['moved']),'deletedExactDuplicates':len(record['deleted']),'activeUnchanged':record['activeUnchanged'],'historicalManifestPathsExist':True},ensure_ascii=False))
