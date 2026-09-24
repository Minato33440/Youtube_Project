"""Verify current source PNG hashes and load the actual exported Cubism file."""
from pathlib import Path
import os,json,hashlib
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
ROOT=Path(__file__).resolve().parent
ART=ROOT.parents[1]/'art'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
for q in json.loads((ART/'psd_front/manifest.json').read_text(encoding='utf-8'))['layers']:
    p=(ART/'psd_front'/q['path']).resolve()
    checks.append({'file':str(p),'unchanged':sha(p)==q['sha256']})
for n,h in json.loads((ART/'expression_rig/source_hashes.json').read_text()).items():
    p=ART/'head/expression_sources/mouth'/f'{n}.png'
    checks.append({'file':str(p),'unchanged':sha(p)==h})
for side,h in json.loads((ART/'expression_rig/blink_source_hashes.json').read_text()).items():
    p=ART/'head/expression_sources/blink'/f'eyelash_upper_{side}_original.png'
    checks.append({'file':str(p),'unchanged':sha(p)==h})
assert len(checks)==48 and all(q['unchanged'] for q in checks),checks
import pygame,live2d.v3 as live2d
pygame.display.init();live2d.init()
pygame.display.set_mode((320,480),pygame.OPENGL|pygame.DOUBLEBUF|pygame.HIDDEN);live2d.glInit()
model=live2d.LAppModel()
try:
    model.LoadModelJson(str(ROOT/'runtime/Ren_front.model3.json'))
    ids=model.GetDrawableIds();parameters=model.GetParamIds()
    assert len(ids)==48,(len(ids),ids)
    expected=['ParamEyeLOpen','ParamEyeROpen','ParamMouthOpenY']
    assert all(p in parameters for p in expected)
    report={'passed':True,'source_png_count':len(checks),'sources':checks,'drawable_count':len(ids),'drawable_ids':ids,
            'implemented_parameters':expected,'all_parameter_ids':parameters,
            'editor_file_sha256':sha(ROOT/'Ren_front.cmo3'),
            'runtime_hashes':{str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'runtime').rglob('*') if p.is_file()},
            'limitations':['Jaw, head/neck angles, hair physics and laugh opening are not implemented.',
                           'Preview texture is one 2048x2048 atlas; source PNG resolution is unchanged.',
                           'VTube Studio and nizima LIVE have not been tested.']}
    (ROOT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':True,'source_png_count':48,'drawable_count':len(ids),'parameters':expected}))
finally:
    model.DestroyRenderer();live2d.dispose();pygame.quit()
