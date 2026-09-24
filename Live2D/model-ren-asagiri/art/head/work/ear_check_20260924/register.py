from pathlib import Path
import json,hashlib,shutil
HERE=Path(__file__).resolve().parent;HEAD=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
qa=json.loads((HERE/'review_checks.json').read_text())
assert len(qa['parts'])==23 and qa['inputPartsUnchanged']
assert all(sha(HEAD/p)==h for p,h in qa['parts'].items())
archive=HEAD/'archive/20260924-before-ear-cleanup'
assert not archive.exists(),'Archive already exists; do not overwrite prior acceptance history'
(archive/'preview').mkdir(parents=True)
for p in (HEAD/'preview').iterdir():
 if p.is_file():shutil.copy2(p,archive/'preview'/p.name)
shutil.copy2(HEAD/'assembly.json',archive/'assembly.json')
shutil.copy2(HEAD/'README.md',archive/'README.md')
for n in ['head_sample.png','head_sample_gray.png','comparison_original.jpg','comparison_face_detail.jpg']:
 assert (HERE/n).is_file();shutil.copy2(HERE/n,HEAD/'preview'/n)
manifest=json.loads((HEAD/'assembly.json').read_text())
manifest['collectionValidationAtInitialImport']={k:manifest.pop(k) for k in ['sourcesUnchanged','collectedFilesMatch'] if k in manifest}
manifest['status']='accepted_front_head_png'
manifest['acceptedOn']='2026-09-24';manifest['acceptance']='acceptance.json'
manifest['currentPartHashes']=qa['parts']
manifest['manualRevisions']=[{'file':'parts/'+c['file'],'sha256':qa['parts']['parts/'+c['file']],'author':'Boss','change':'Outer-edge cleanup; native dimensions and original placement retained','date':'2026-09-24'} for c in qa['earChecks']]
manifest['sourcesNote']='Initial collection provenance is retained in sources. Current approved PNG bytes are identified by currentPartHashes, including Boss edits made directly in head/parts.'
(HEAD/'assembly.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
acceptance={'status':'accepted_front_head_png','label':'頭部前面・完成PNG','date':'2026-09-24','canonicalParts':'parts/','scope':'Front head, neutral open-eye closed-mouth static PNG artwork','approval':{'face':'Boss accepted appearance and requested completion registration','hair':'Boss explicitly accepted','ears':'Boss cleaned outer edges; assistant inspected isolated ears and composite before registration'},'partCount':23,'partHashes':qa['parts'],'earChecks':qa['earChecks'],'validation':{'nativeDimensionsPreserved':True,'allPartsUnmodifiedDuringReview':True,'isolatedEarDebrisAtAlphaAbove25':0,'earInteriorRgbUnchangedWhereBothVersionsOpaque':True,'visualReview':'Passed for static front-head PNG scope'},'preview':{n:sha(HEAD/'preview'/n) for n in ['head_sample.png','head_sample_gray.png','comparison_original.jpg','comparison_face_detail.jpg']},'notYetCompleted':['PSD integration','Cubism mesh creation','Blink and mouth motion on this final artwork','Angle and physics deformation validation','Body and back artwork approval']}
(HEAD/'acceptance.json').write_text(json.dumps(acceptance,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
assert all(sha(HEAD/p)==h for p,h in acceptance['partHashes'].items())
assert all(sha(HEAD/'preview'/p)==h for p,h in acceptance['preview'].items())
print('Registered accepted_front_head_png: 23 unchanged parts; updated previews verified')
