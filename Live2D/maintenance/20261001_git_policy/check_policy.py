"""Read-only policy regression and preservation checks. No Git mutation."""
from pathlib import Path
import hashlib, json, os, subprocess, sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
REN = 'Live2D/model-ren-asagiri'
os.environ['GIT_OPTIONAL_LOCKS'] = '0'

def git(*args, data=None):
    p = subprocess.run(['git','--no-optional-locks',*args], cwd=ROOT,
                       input=data, capture_output=True)
    if p.returncode not in (0,1):
        raise RuntimeError(p.stderr.decode('utf8',errors='replace'))
    return p.stdout

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def scan_files(folder):
    files, errors = {}, []
    for directory, subdirs, names in os.walk(folder, onerror=lambda e: errors.append(str(e))):
        for name in names:
            path = Path(directory)/name
            try: files[path.relative_to(ROOT).as_posix()] = sha(path)
            except OSError as e: errors.append(str(e))
    return files, errors

def rules(paths):
    raw=git('check-ignore','--no-index','-v','-z','--stdin',data=('\0'.join(paths)+'\0').encode()).split(b'\0')
    out={}
    for i in range(0,len(raw)-1,4):
        source,line,pattern,path=[v.decode('utf8') for v in raw[i:i+4]]
        out[path]=dict(ignored=not pattern.startswith('!'),source=source,line=int(line),pattern=pattern)
    return {p:out.get(p,dict(ignored=False,source=None)) for p in paths}

def probes():
    p={}
    for depth in ['', 'nested/', 'nested/archive/', 'nested/backup/parts/']:
        for ext in ['png','PNG','pNg','jpg','JPG','jPg','jpeg','JPEG','jPeG','psd','PSD','pSd','gif','GIF','gIf']:
            p[f'{REN}/art/latest_png_collection/{depth}sample.{ext}']=False
    for folder in ['art/head/parts','art/work/new','art_assets','latest_preview','test_png_20261001_132300/selected','model/base_motion/review_front_gui_20261001','model/base_motion/brow_implementation_20261001','model/head_angles/archive/old']:
        for ext in ['png','PNG','JpG','JPEG','pSd','GIF','webp','BMP']:
            p[f'{REN}/{folder}/sample.{ext}']=True
    for folder in ['art/head/parts','art/head/parts/archive/old','test_png_20261001_132300/selected','model/base_motion/review_front_gui_20261001','model/head_angles/archive/old','model/base_motion/brow_implementation_20261001']:
        for ext in ['md','json','py','js','ps1','csv','txt']:
            p[f'{REN}/{folder}/record.{ext}']=False
    for folder in ['model/head_angles','model/head_angles/archive/old','model/base_motion/review_test','model/base_motion/brow_implementation_new','model/base_motion/archive/old','model/base_motion/backup/new','model/base_motion/buckup/new']:
        p[f'{REN}/{folder}/copy.cmo3']=True
    for name in ['Ren_base.cmo3','Ren_base4.cmo3','Ren_base5.cmo3','Ren_base99.cmo3']:
        p[f'{REN}/model/base_motion/{name}']=name in ('Ren_base.cmo3','Ren_base4.cmo3')
    p[f'{REN}/model/head_neck_hair/runtime/Ren_front.moc3']=False
    p[f'{REN}/model/head_neck_hair/runtime/Ren_front.model3.json']=False
    p[f'{REN}/art/latest_png_collection/README.md']=False
    p[f'{REN}/art/latest_png_collection/manifest.json']=False
    p[f'{REN}/art/latest_png_collection/deep/clip.mp4']=True
    p[f'{REN}/art/archive/credentials.json']=True
    p['Live2D/maintenance/20260928_asset_cleanup/verify_cleanup.py']=False
    p['Live2D/CHARACTER_PRODUCTION_WORKFLOW.md']=False
    return p

def main():
    baseline=json.loads((HERE/'baseline.json').read_text(encoding='utf8'))
    expected=probes();actual=rules(list(expected))
    failures={p:dict(expected=v,actual=actual[p]) for p,v in expected.items() if actual[p]['ignored']!=v}
    now,errors=scan_files(ROOT/REN)
    before=baseline['ren_files']
    preservation=dict(missing=sorted(set(before)-set(now)),changed=[p for p in before if p in now and before[p]!=now[p]],added=sorted(set(now)-set(before)),scan_errors=errors)
    outside=rules(list(baseline['outside_rule_probes']))
    outside_changes={p:dict(before=v,after=outside[p]['ignored']) for p,v in baseline['outside_rule_probes'].items() if v!=outside[p]['ignored']}
    tracked=[p.decode() for p in git('ls-files','-z','--',REN).split(b'\0') if p]
    removals=git('diff','--cached','--name-status','-z').decode().split('\0')
    result=dict(test_count=len(expected),failures=failures,outside_rule_changes=outside_changes,preservation=preservation,
                tracked_ren_count=len(tracked),staged_name_status=removals,
                stage0_before=baseline['initial_cached_diff_empty'],index_sha256=sha(ROOT/'.git/index'))
    (HERE/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('staged_name_status',)},ensure_ascii=True,indent=2))
    return int(bool(failures or outside_changes or preservation['missing'] or preservation['changed']))

if __name__=='__main__':sys.exit(main())
