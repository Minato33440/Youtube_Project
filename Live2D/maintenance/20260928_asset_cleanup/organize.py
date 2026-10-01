"""One-shot, manifest-backed Live2D cleanup. Never touches Traning or Git index.

Requires the immutable pre-cleanup baseline captured in the local temp directory.
This is an execution record for this cleanup, not a recurring cleanup policy.
"""
from pathlib import Path
import collections
import csv
import hashlib
import json
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
LIVE = ROOT / 'Live2D'
REPORT = Path(__file__).resolve().parent
ARCHIVE = LIVE / 'archive/20260928-generated-previews'
BASELINE = Path(tempfile.gettempdir()) / 'ren_cleanup_20260928/baseline.json'
REN = 'Live2D/model-ren-asagiri/'


def digest(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def safe_path(relative):
    p = (ROOT / relative).resolve()
    if not p.is_relative_to(LIVE.resolve()) or p.is_relative_to((LIVE / 'Traning').resolve()):
        raise ValueError(f'Outside permitted scope: {relative}')
    return p


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8')


def main():
    base = json.loads(BASELINE.read_text('utf-8'))
    if (REPORT / 'movement_manifest.json').exists():
        raise SystemExit('Already applied; use the manifest to inspect or restore, not rerun.')
    tracked = set(base['tracked'])
    visible = set(base['untracked'])
    records = []
    moves = []
    keep = set()
    source_prefixes = [
        'art_assets/', 'art/head/reference/', 'art/head/editor_data/',
        'art/head/expression_sources/', 'art/head/preview/',
        'art/full_body_side_view/', 'art/head_side_view/', 'art/Looking_down/',
    ]
    part_dirs = ['art/head/parts', 'art/expression_rig/parts',
                 'art/processing_v001/front/parts', 'art/processing_v001/back/parts']
    exact_sources = {
        'art/psd_front/Ren_front.psd', 'art/psd_front/Ren_front.png',
        'art/expression_rig/Ren_blink_transition.psd',
        'art/expression_rig/Ren_mouth_addition.psd',
        'art/expression_rig/mouth_on_current_head.jpg',
        'art/processing_v001/front/Ren_front_parts_v001.psd',
        'art/processing_v001/back/Ren_back_parts_v001.psd',
        'art/neck_collar_v004/Ren_neck_collar_v004.psd',
    }
    preview_names = {
        'Ren_blink_mouth.gif', 'Ren_blink_mouth.mp4', 'expression_review.jpg',
        'Ren_head_neck_hair.gif', 'Ren_head_neck_hair.mp4',
        'head_neck_hair_review.jpg', 'jaw_neck_detail.jpg', 'neutral_full.png',
        'neutral_comparison.jpg', 'animation_review.jpg',
    }
    for record in base['files']:
        rel = record['path']
        p = safe_path(rel)
        sub = rel.removeprefix(REN)
        segments = Path(sub).parts
        historical = any(s.lower() in ('archive', 'backup', 'buckup') for s in segments)
        category, reason = 'local_generated_or_history', 'Existing ignored output; retain locally, not a production source'
        movable = False
        if rel in tracked:
            category, reason = 'already_tracked', 'Preserve existing tracked file and user changes'
        elif '__pycache__' in segments or 'pylib' in segments:
            category, reason = 'local_dependency_or_cache', 'Existing local environment; do not relocate an imported dependency'
        elif historical:
            category, reason = 'local_archive', 'Historical archive excluded by default; no deletion'
            # Keep compact rollback/runtime dependencies at their original paths.
            # Their relative model3 references and old diagnostic scripts stay resolvable.
            if sub.startswith('model/head_angles/') and (
                p.suffix == '.cmo3' or '/runtime/' in sub or '/face_runtime/' in sub
                or p.name in ('README.md', 'verification.json')
                or (p.name in ('case_01.png', 'case_03.png') and '/preview/' in sub)
            ):
                category, reason = 'git_experiment', 'Rollback or runtime dependency for retained failure evidence; not accepted production'
        elif sub.startswith('model/') and '/preview/' in sub and (
            re.fullmatch(r'case_\d+\.png', p.name) or re.fullmatch(r'video_frame_\d+\.png', p.name)
        ):
            if re.fullmatch(r'case_\d+\.png', p.name) and sub.startswith(('model/head_angles/', 'model/head_neck_hair/')):
                category = 'git_experiment' if sub.startswith('model/head_angles/') else 'git_asset'
                reason = 'Direct or globbed input to retained verifier; preserve full case set'
            else:
                category, reason = 'archive_generated_frame', 'Re-renderable individual frame; keep contact sheets and motion samples'
                movable = True
        elif sub.startswith('model/head_angles/') and p.suffix == '.log':
            category, reason = 'archive_generated_log', 'Superseded render console log; structured verification retained'
            movable = True
        elif rel.startswith(REN) and (
            any(sub.startswith(prefix) for prefix in source_prefixes)
            or str(Path(sub).parent).replace('\\', '/') in part_dirs
            or sub in exact_sources
            or (sub.startswith(('model/basic_expression/runtime/', 'model/head_neck_hair/runtime/')))
            or ('/preview/' in sub and p.name in preview_names and not sub.startswith('model/head_angles/'))
        ):
            category, reason = 'git_asset', 'Source artwork, edited part, editable project, runtime dependency, or accepted review sample'
        elif sub.startswith('model/head_angles/'):
            category, reason = 'git_experiment', 'Unaccepted contour/angle experiment, code and comparison evidence'
        elif rel in visible:
            category, reason = 'git_document_or_project', 'Production documentation, reusable template, or distinct voice project'
        if category.startswith('git_'):
            if p.suffix in ('.pyc', '.log'):
                raise ValueError(f'Unexpected cache/log selected: {rel}')
            keep.add(rel)
        row = dict(record, category=category, reason=reason, destination='')
        if movable:
            dest = ARCHIVE / p.relative_to(LIVE)
            safe_path(dest.relative_to(ROOT))
            if dest.exists():
                raise FileExistsError(dest)
            row['destination'] = dest.relative_to(ROOT).as_posix()
            moves.append({'source': rel, 'destination': row['destination'],
                          'size': record['size'], 'sha256': record['sha256'], 'reason': reason})
        records.append(row)

    # Preflight every mutation before performing any move.
    for move in moves:
        if move['source'] in tracked:
            raise ValueError('Refusing to move a tracked file')
        if digest(safe_path(move['source'])) != move['sha256']:
            raise ValueError(f"Concurrent source change: {move['source']}")
    ignore_path = LIVE / '.gitignore'
    if ignore_path.exists():
        raise FileExistsError('Do not overwrite a preexisting Live2D/.gitignore')

    REPORT.mkdir(parents=True, exist_ok=True)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    # Local rollback record includes original Git status and protected-file hashes.
    (ARCHIVE / 'baseline.json').write_text(json.dumps(base, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    for move in moves:
        src, dest = safe_path(move['source']), safe_path(move['destination'])
        dest.parent.mkdir(parents=True, exist_ok=True)
        src.replace(dest)
        if digest(dest) != move['sha256']:
            raise ValueError(f"Post-move mismatch: {dest}")

    # Exact-file exceptions intentionally prevent unrelated future renders from becoming Git candidates.
    rules = [
        '# Live2D asset classification, 2026-09-28. Traning is user-managed and unaffected.',
        '# Existing tracked archive metadata stays tracked; ignore does not remove it from Git.',
        '/archive/', '/model-ren-asagiri/**/archive/',
        '/model-ren-asagiri/**/backup/', '/model-ren-asagiri/**/buckup/',
        '', '# Selected source assets and evidence override root image/PSD/parts exclusions.',
    ]
    directories = set()
    for rel in keep:
        local = Path(rel).relative_to('Live2D')
        for parent in local.parents:
            if parent.as_posix() != '.':
                directories.add(parent.as_posix())
    # Reopen only directories containing selected files, then ignore their contents
    # again when they are beneath archive. Final exact-file lines opt in selected evidence.
    for directory in sorted(directories, key=lambda s: (s.count('/'), s)):
        rules.append('!/' + directory + '/')
        if any(s.lower() in ('archive', 'backup', 'buckup') for s in directory.split('/')):
            rules.append('/' + directory + '/*')
    rules.extend('!/' + str(Path(rel).relative_to('Live2D')).replace('\\', '/') for rel in sorted(keep))
    ignore_path.write_text('\n'.join(rules) + '\n', 'utf-8')

    manifest = {'date': '2026-09-28', 'scope': 'Live2D excluding Traning',
                'baseline_head': base['head'], 'policy': 'No deletion; no Git index changes; preserve source paths',
                'moves': moves}
    (REPORT / 'movement_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    with (REPORT / 'inventory.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['path', 'size', 'mtime_ns', 'sha256', 'category', 'reason', 'destination'])
        w.writeheader(); w.writerows(records)
    groups = collections.defaultdict(list)
    for row in records:
        if row['category'].startswith('git_'):
            groups[row['category']].append(row['path'])
    for category, paths in groups.items():
        (REPORT / (category + '.txt')).write_text('\n'.join(sorted(paths)) + '\n', 'utf-8')
    summary = {category: {'files': sum(x['category'] == category for x in records),
                          'bytes': sum(x['size'] for x in records if x['category'] == category)}
               for category in sorted({x['category'] for x in records})}
    (REPORT / 'classification_summary.json').write_text(json.dumps(summary, indent=2) + '\n', 'utf-8')
    print(json.dumps({'classification': summary, 'moved': len(moves), 'deleted': 0}, indent=2))


if __name__ == '__main__':
    main()
