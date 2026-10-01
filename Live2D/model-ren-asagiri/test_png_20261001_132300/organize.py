"""Curated test evidence copies; archive only two explicitly reviewed duplicate outputs.
No regeneration, Git mutation, model editing or deletion. Refuse overwrites.
"""
import os, sys, json, hashlib, re, subprocess
from pathlib import Path
from collections import defaultdict
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parent; MODEL=ROOT.parent; REPO=MODEL.parents[1]
OLD=MODEL/'art/latest_png_collection'
os.environ['GIT_OPTIONAL_LOCKS']='0'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,obj):
    with (ROOT/name).open('x',encoding='utf8') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
def read(name):return json.loads((ROOT/name).read_text(encoding='utf8'))
def files_under(root,exclude_output=True):
    for folder,ds,fs in os.walk(root):
        ds[:]=[d for d in ds if d not in ['pylib','node_modules','__pycache__','.git'] and (not exclude_output or Path(folder)/d!=ROOT)]
        for n in fs:yield Path(folder)/n
def git(*args):return subprocess.check_output(['git','--no-optional-locks',*args],cwd=REPO,stderr=subprocess.DEVNULL).decode('utf8','replace')
def prepare():
    if (ROOT/'selection.json').exists():raise RuntimeError('Already prepared')
    baseline={p.relative_to(MODEL).as_posix():dict(sha256=digest(p),bytes=p.stat().st_size) for p in files_under(MODEL)}
    save('preservation_before.json',dict(files=baseline,index_sha256=digest(REPO/'.git/index')))
    index={}
    for x in git('ls-files','-s','-z').split('\0'):
        if x:
            meta,p=x.split('\t');index[p]=meta
    status={x[3:]:x[:2] for x in git('status','--porcelain=v1','-uall','--','Live2D/model-ren-asagiri').splitlines() if x}
    selections=[]
    def add(path,group,label,date,evidence,state,condition=None,role='final_test_output'):
        src=MODEL/path; assert src.exists(),path
        assert not any(x in src.parts for x in ('parts','source_snapshot','runtime','face_runtime'))
        filename=f'{label}_{date}.png'; dest=ROOT/'selected'/group/filename
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as f:f.write(src.read_bytes())
        rp=src.relative_to(REPO).as_posix()
        selections.append(dict(original=path,copy=dest.relative_to(ROOT).as_posix(),sha256=digest(src),bytes=src.stat().st_size,
            group=group,test_date=date,date_basis=evidence,evidence=evidence,acceptance_state=state,condition=condition,role=role,
            git_index_entry=index.get(rp),git_status=status.get(rp,'tracked_clean' if rp in index else 'untracked_or_ignored'),original_retained=True))
    add('art/neck_collar_v004/neck_collar_review.png','01_static_assembly','neck_collar_v004','2026-09-21','art/neck_collar_v004/README.md','static_validation_pass')
    for n in ['head_sample','head_sample_gray']:
        add(f'art/head/preview/{n}.png','01_static_assembly',f'head_final_{n}','2026-09-24','art/head/README.md; art/head/acceptance.json','accepted_static_PNG_at_that_date')
    for n in ['eyes','head_neck','neck_collar','psd_readback_head_neck']:
        add(f'art/psd_front/review/{n}.png','02_psd_validation',f'psd41_{n}','2026-09-24','art/psd_front/README.md; prepare.py; verify.py','PSD_validation_pass_not_rig_acceptance')
    arch='art/archive/20260924-old-head-assets/art/'
    for state in ['closed','half','open']:
        add(arch+f'blink_assembly_v001/{state}/preview.png','03_accepted_shape_references',f'blink_shape_{state}','2026-09-22',arch+'blink_assembly_v001/README.md','historical_shape_reference_accepted_not_base3')
    for state in ['closed','small','medium','open']:
        add(arch+f'mouth_motion_v002/{state}/preview.png','03_accepted_shape_references',f'mouth_v002_{state}','2026-09-22',arch+'mouth_motion_v002/README.md','historical_talking_range_accepted_not_base3')
    add(arch+'face_comparison_v010/face_04.png','04_face_comparison','face_v010_current_sample','2026-09-22',arch+'face_comparison_v010/README.md','latest_v010_comparison_not_current_source')
    # Preserve the earlier hair-placement acceptance as a distinct pre-PSD revision.
    for n in ['registered_position','registered_position_gray']:
        add(f'art/head/work/hair_check_20260924/{n}.png','01_static_assembly',f'hair_seam_pre_PSD_{n}','2026-09-24','art/head/work/hair_check_20260924/approved_acceptance.json; validation.json','historical_static_acceptance_before_PSD_refresh')
    ep='model/head_angles/single_endpoint/'
    add(ep+'whole_head_outline_check/whole_head_runtime_guide_4up.png','06_unaccepted_contour_experiment','contour_344points_Xm30_Ym30','2026-09-26',ep+'whole_head_outline_check/README.md','latest_experiment_not_accepted')
    for n in ['face_intermediate_poses_ja','face_jaw_opening_ja','front_mouth_preservation_ja','other_pose_remesh_differences_ja']:
        add(ep+f'whole_head_pose_check/{n}.png','06_unaccepted_contour_experiment',f'whole_head_{n}','2026-09-26',ep+'README.md; whole_head_pose_check/whole_head_pose_checks.json','latest_experiment_with_remaining_edge_defects')
    add(ep+'dense_contour_check/cheek_jaw_comparison_ja.png','06_unaccepted_contour_experiment','contour_191points_mesh_refinement','2026-09-26',ep+'README.md section previous vertex refinement','earlier_different_guide_not_superseded_equivalent',role='distinct_measurement_baseline')
    for folder,group,date,state in [('head_neck_hair','05_accepted_initial_motion','2026-09-24','initial_motion_preview_accepted_2026-09-25_not_current_cmo3'),('head_angles','07_unaccepted_XY_experiment','2026-09-26','last_full_head_XY_experiment_not_accepted')]:
        report=json.loads((MODEL/f'model/{folder}/preview/verification.json').read_text(encoding='utf8'))
        for num,case in enumerate(report['cases']):
            # Values are authoritative; an old label says Tilt + speech while value is -30.
            cond=case['requested']; detail='_'.join(k.replace('Param','')+str(v).replace('-','m').replace('.','p') for k,v in cond.items()) or 'Neutral'
            add(f'model/{folder}/preview/case_{num:02d}.png',group,f'{folder}_{num:02d}_{detail}',date,
                f'model/{folder}/README.md; preview/verification.json cases[{num}]; render_preview.py enumerate(cases)',state,case)
    save('selection.json',selections)
    # Broad candidate inventory; inclusion here is not a declaration that an image is disposable.
    candidates=[]; group_hash=defaultdict(list)
    for r,meta in baseline.items():
        if not r.lower().endswith('.png') or r.startswith(('art/png_collection_','art_assets/')):continue
        parts=r.split('/')
        if any(x in parts for x in ['parts','source_snapshot','runtime','face_runtime','reference','ear_surface','editor_data','expression_sources']):continue
        if any(x in r for x in ['full_body_side_view','head_side_view','texture_','reference_overlay','art/Looking_down']):continue
        rp='Live2D/model-ren-asagiri/'+r
        category='selected' if any(s['original']==r for s in selections) else 'retain_review_conditions_or_dependencies'
        candidates.append(dict(path=r,**meta,disposition=category,git_index_entry=index.get(rp),git_status=status.get(rp,'tracked_clean' if rp in index else 'untracked_or_ignored')))
        group_hash[meta['sha256']].append(r)
    save('review_candidates.json',dict(scope='PNG likely test outputs only; excludes artwork, runtime, imports, former collection',candidates=candidates,
        exact_duplicate_groups=[dict(sha256=h,paths=ps,decision='Do not move automatically; same bytes may serve another test or baseline') for h,ps in group_hash.items() if len(ps)>1],
        known_dependency_holds=['model/*/preview/case_*.png consumed by validators','model/head_angles/preview/before_tilted_reference_case_*.png comparison inputs','latest_preview is shared handoff location','source snapshots and runtime relative paths protected'],
        limitations=['No claim all project history has one final image','Distinct guide sampling (191 vs 344), angles, expressions and before/after are preserved','JPG/GIF/MP4 not renamed or moved']))
    # Only duplicate snapshots with a preserved authoritative same-test output are proposed.
    moves=[]
    for n,replacement in [('head_sample.png','registered_position.png'),('head_sample_gray.png','registered_position_gray.png')]:
        src=f'art/head/work/hair_check_20260924/final_preview/{n}'
        keep=f'art/head/work/hair_check_20260924/{replacement}'
        assert baseline[src]['sha256']==baseline[keep]['sha256']
        copied=next(s['copy'] for s in selections if s['original']==keep)
        moves.append(dict(original=src,archive='archive/deletion_candidates/'+src,sha256=baseline[src]['sha256'],bytes=baseline[src]['bytes'],replacement_original=keep,replacement_copy=copied,
            reason='Same 2026-09-24 pre-PSD hair-seam test; final_preview duplicates registered_position byte-for-byte; accepted historical stage and separate new PSD-stage outputs retained',
            git_index_entry=index.get('Live2D/model-ren-asagiri/'+src),git_status=status.get('Live2D/model-ren-asagiri/'+src,'untracked_or_ignored'),state='proposed'))
    save('move_plan.json',moves)
    # Search project text/code for exact/subdirectory references, retaining historical inventory hits separately.
    refs=[]
    for f in files_under(REPO):
        if f.is_relative_to(ROOT) or f.suffix.lower() not in ['.py','.js','.ts','.json','.md','.ps1','.yaml','.yml'] or f.stat().st_size>4_000_000:continue
        try:txt=f.read_text(encoding='utf8').replace('\\\\','/').replace('\\','/')
        except (OSError,UnicodeError):continue
        terms=['final_preview','hair_check_20260924','head_sample.png','head_sample_gray.png']
        hits=[dict(line=i+1,text=l[:500]) for i,l in enumerate(txt.splitlines()) if any(t in l for t in terms)]
        if hits:refs.append(dict(file=str(f.relative_to(REPO)),historical_inventory=f.is_relative_to(OLD),hits=hits))
    save('reference_audit.json',dict(hits=refs,decision='Review before archive; generic filename hits alone do not establish a consumer',scope='Repository text/code excluding .git, pylib, node_modules, __pycache__; files <=4MB; literals and target directory names'))
    # Small contact sheets for actual visual inspection, not final image replacements.
    for start in range(0,len(selections),12):
        batch=selections[start:start+12]; sheet=Image.new('RGB',(1400,((len(batch)+3)//4)*310),(90,100,105));draw=ImageDraw.Draw(sheet)
        for j,s in enumerate(batch):
            im=Image.open(ROOT/s['copy']).convert('RGBA');im.thumbnail((340,265));x=(j%4)*350;y=(j//4)*310
            sheet.paste(im,(x+(350-im.width)//2,y),im)
            draw.text((x+3,y+267),f'{start+j:02d} '+Path(s['copy']).stem[:42],fill='white');draw.text((x+3,y+283),s['group'],fill='white')
        sheet.save(ROOT/f'qa_selection_{start//12+1}.jpg')
    print(json.dumps(dict(selected=len(selections),bytes=sum(s['bytes'] for s in selections),candidates=len(candidates),duplicate_groups=sum(len(x)>1 for x in group_hash.values()),proposed_moves=moves),ensure_ascii=True))

def archive():
    if (ROOT/'movement_manifest.json').exists():raise RuntimeError('Already archived')
    moves=read('move_plan.json')
    for m in moves:
        assert m['state']=='eligible_after_dependency_review', 'Blocked or unreviewed plan; do not move'
        src=(MODEL/m['original']).resolve();dst=(ROOT/m['archive']).resolve();keep=(MODEL/m['replacement_original']).resolve()
        assert src.is_relative_to(MODEL) and dst.is_relative_to(ROOT/'archive/deletion_candidates')
        assert src.is_file() and not dst.exists() and digest(src)==m['sha256']==digest(keep)==digest(ROOT/m['replacement_copy'])
        assert not m['git_index_entry'], 'Do not move an indexed file in this narrowly reviewed operation'
    save('movement_manifest.json',moves) # durable reversible manifest before first rename
    for m in moves:
        src=(MODEL/m['original']).resolve();dst=(ROOT/m['archive']).resolve();dst.parent.mkdir(parents=True,exist_ok=True);src.rename(dst)
        assert not src.exists() and digest(dst)==m['sha256']
    verify()

def verify():
    before=read('preservation_before.json');moves=read('movement_manifest.json') if (ROOT/'movement_manifest.json').exists() else []
    moved={m['original']:m for m in moves};bad=[]
    relocation_path=MODEL/'art/latest_png_collection/relocation.json'
    relocation=json.loads(relocation_path.read_text(encoding='utf8')) if relocation_path.exists() else {}
    updates=relocation.get('reference_updates',{})
    for r,meta in before['files'].items():
        current=r.replace('art/png_collection_base3_20261001_130414/','art/latest_png_collection/')
        p=ROOT/moved[r]['archive'] if r in moved else MODEL/current
        expected=meta['sha256']
        change=updates.get(r)
        if change and change['before_sha256']==expected:expected=change['after_sha256']
        if not p.exists() or digest(p)!=expected:bad.append(r)
    checks=dict(all_original_files_preserved_or_manifest_moved=not bad,bad_paths=bad,
        git_index_unchanged=digest(REPO/'.git/index')==before['index_sha256'],index_sha256=before['index_sha256'],
        copies_equal=all(digest(ROOT/s['copy'])==s['sha256']==digest(MODEL/s['original']) for s in read('selection.json')),
        moves_valid=all(not (MODEL/m['original']).exists() and digest(ROOT/m['archive'])==m['sha256'] for m in moves),
        original_files_checked=len(before['files']),moved_count=len(moves),moved_bytes=sum(m['bytes'] for m in moves),
        protected='All accessible original model project files excluding dependency libraries/cache; includes original 48 artwork, all CMO3/PSD/runtime and prior collection/reports')
    (ROOT/'verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')
    # Never restore or rewrite an index changed by another process. Report this separately.
    assert all(checks[k] for k in ['all_original_files_preserved_or_manifest_moved','copies_equal','moves_valid'])
    print(json.dumps(checks))
if __name__=='__main__':
    {'prepare':prepare,'archive-reviewed':archive,'verify':verify}[sys.argv[1] if len(sys.argv)>1 else 'prepare']()
