"""Read-only cleanup checks, except writing validation.json beside this file."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
REPORT = Path(__file__).resolve().parent
BASE = ROOT / 'Live2D/archive/20260928-generated-previews/baseline.json'
REN = ROOT / 'Live2D/model-ren-asagiri'
EDITED_DOCS = {'Live2D/README.md', 'Live2D/model-ren-asagiri/README.md',
               'Live2D/model-ren-asagiri/AGENTS.md'}


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def run(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8')


def main():
    base = json.loads(BASE.read_text('utf-8'))
    movement = json.loads((REPORT / 'movement_manifest.json').read_text('utf-8'))['moves']
    moves = {m['source']: m for m in movement}
    errors = []
    counts = {}
    for group in ('files', 'training'):
        checked = 0
        for row in base[group]:
            rel = row['path']
            path = ROOT / moves.get(rel, {}).get('destination', rel)
            if rel in EDITED_DOCS:
                path = ROOT / 'Live2D/archive/20260928-generated-previews/pre_cleanup_documents' / rel
            if not path.is_file() or sha(path) != row['sha256']:
                errors.append({'check': 'original_content_preserved', 'path': rel})
            checked += 1
        counts[group + '_hashes_checked'] = checked
    expected_training = {r['path'] for r in base['training']}
    actual_training = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'Live2D/Traning').rglob('*') if p.is_file()}
    if expected_training != actual_training:
        errors.append({'check': 'training_membership_unchanged'})
    if run('status', '--porcelain=v1', '-z', '--', 'Live2D/Traning') != base['training_status']:
        errors.append({'check': 'training_git_status_unchanged'})
    if (ROOT / '.gitignore').read_text('utf-8') != base['gitignore']:
        errors.append({'check': 'root_gitignore_unchanged'})
    if run('status', '--porcelain=v1', '-z', '--', '.', ':(exclude)Live2D') != base['outside_status']:
        errors.append({'check': 'outside_scope_status_unchanged'})
    if run('rev-parse', 'HEAD').strip() != base['head']:
        errors.append({'check': 'no_commit'})

    keep = []
    for p in REPORT.glob('git_*.txt'):
        keep.extend(p.read_text('utf-8').splitlines())
    staged = set(run('diff', '--cached', '--name-only', '-z').split('\0')[:-1])
    allowed_staged = set(keep) | {'Live2D/.gitignore', 'Live2D/ASSET_CATALOG.md'}
    allowed_staged.update(p.relative_to(ROOT).as_posix() for p in REPORT.iterdir() if p.is_file())
    if staged != allowed_staged:
        errors.append({'check': 'only_selected_new_files_staged',
                       'unexpected': sorted(staged - allowed_staged),
                       'missing': sorted(allowed_staged - staged)})
    if staged & set(base['tracked']):
        errors.append({'check': 'preexisting_tracked_changes_not_staged'})
    tracked = set(run('ls-files', '-z').split('\0')[:-1])
    result = subprocess.run(['git', 'check-ignore', '--stdin', '-z'], cwd=ROOT,
                            input=('\0'.join(keep) + '\0').encode('utf-8'), capture_output=True)
    ignored_selected = result.stdout.decode('utf-8').split('\0')[:-1]
    if ignored_selected:
        errors.append({'check': 'selected_files_not_ignored', 'paths': ignored_selected})
    for rel in keep:
        if rel.startswith('Live2D/Traning/') or not (ROOT / rel).is_file():
            errors.append({'check': 'commit_list_scope_or_missing', 'path': rel})
    current_untracked = set(run('ls-files', '--others', '--exclude-standard', '-z', '--', 'Live2D').split('\0')[:-1])
    unclassified = [p for p in current_untracked if p not in keep and not p.startswith(('Live2D/Traning/', 'Live2D/maintenance/'))
                    and p not in ('Live2D/.gitignore', 'Live2D/ASSET_CATALOG.md')]
    if unclassified:
        errors.append({'check': 'unclassified_visible_files', 'paths': unclassified})
    move_paths = [m['destination'] for m in movement]
    ignored_move_result = subprocess.run(['git', 'check-ignore', '--stdin', '-z'], cwd=ROOT,
                                         input=('\0'.join(move_paths) + '\0').encode(), capture_output=True)
    if set(ignored_move_result.stdout.decode().split('\0')[:-1]) != set(move_paths):
        errors.append({'check': 'moved_files_ignored'})

    source_checks = []
    for folder, name, key in [('art/head', 'assembly.json', 'file'),
                              ('art/psd_front', 'manifest.json', 'path'),
                              ('art/expression_rig', 'manifest.json', 'path'),
                              ('art/expression_rig', 'blink_manifest.json', 'path'),
                              ('art/processing_v001/back', 'manifest.json', 'path')]:
        directory = REN / folder
        data = json.loads((directory / name).read_text('utf-8-sig'))
        for layer in data['layers']:
            p = (directory / layer[key]).resolve()
            rel = p.relative_to(ROOT).as_posix()
            if not p.is_file() or rel not in tracked | set(keep):
                errors.append({'check': 'active_manifest_source_available_for_git', 'path': rel})
            source_checks.append(rel)
    runtime_refs = []
    for rel in sorted(tracked | set(keep)):
        p = ROOT / rel
        if not rel.startswith('Live2D/model-ren-asagiri/model/') or not rel.endswith('.model3.json') or not p.exists():
            continue
        data = json.loads(p.read_text('utf-8-sig'))['FileReferences']
        refs = []
        for key in ('Moc', 'Physics', 'Pose', 'DisplayInfo', 'UserData'):
            if data.get(key):
                refs.append(data[key])
        refs.extend(data.get('Textures', []))
        refs.extend(e['File'] for e in data.get('Expressions', []))
        for motions in data.get('Motions', {}).values():
            refs.extend(e['File'] for e in motions)
        for ref in refs:
            target = (p.parent / ref).resolve()
            relative = target.relative_to(ROOT).as_posix()
            if not target.is_file() or relative not in tracked | set(keep):
                errors.append({'check': 'runtime_reference_available_for_git', 'model': rel, 'path': relative})
            runtime_refs.append(relative)
    case_inputs = []
    for model, count in [('head_neck_hair', 14), ('head_angles', 16)]:
        for i in range(count):
            rel = f'Live2D/model-ren-asagiri/model/{model}/preview/case_{i:02d}.png'
            if not (ROOT / rel).is_file() or rel not in tracked | set(keep):
                errors.append({'check': 'verifier_case_input_preserved', 'path': rel})
            case_inputs.append(rel)
    counts.update(selected_new_files=len(keep), active_source_references=len(source_checks),
                  runtime_references=len(runtime_refs), moved_files=len(movement), deleted_files=0,
                  unclassified_visible_files=len(unclassified), staged_new_files=len(staged),
                  verifier_case_inputs=len(case_inputs))
    largest = max(((ROOT / p).stat().st_size, p) for p in keep)
    output = {'date': '2026-09-28', 'passed': not errors, 'counts': counts, 'errors': errors,
              'largest_selected_file': {'path': largest[1], 'bytes': largest[0]},
              'scope': 'File preservation, Git selection, live source manifests and runtime references; no Cubism visual revalidation',
              'historical_limitations': 'Historical absolute paths and old verifier current/baseline semantics are not rewritten or certified.',
              'preserved_formatting_note': 'Existing head_angles/test_report.md has one extra blank line at EOF. Preserved verbatim. Windows CRLF files are checked with cr-at-eol.'}
    (REPORT / 'validation.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(json.dumps(output, ensure_ascii=False, indent=2))
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
