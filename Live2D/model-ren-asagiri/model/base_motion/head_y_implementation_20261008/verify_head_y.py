"""Read-only verification of the Cubism-authored Ren_base7 head Y pass."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import itertools
import json
import sys
import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE.parent / 'training_base_audit'))
sys.path.insert(0, str(BASE / 'iris_xy_implementation_20261002'))
from audit_cmo3 import Cmo
from verify_iris_xy import mesh_data

def positions(cmo, name, guid=None):
    obj = next(x for tag in ('CArtMeshSource', 'CWarpDeformerSource')
               for x in cmo.objects(tag) if cmo.name(x) == name)
    forms = [cmo.res(f) for f in cmo.field(obj, 'keyforms')]
    form = next((f for f in forms if cmo.val(next(f.iter('CFormGuid'), None)) == guid), forms[0])
    arr = next(q for q in form.iter() if q.get('xs.n') == 'positions')
    return np.array(arr.text.split(), dtype=float).reshape(-1, 2)

def main():
    before, after = [Cmo(BASE / n) for n in ('Ren_base6.cmo3', 'Ren_base7.cmo3')]
    a, b = before.summarize(), after.summarize()
    old = {v['name']: v for v in a['meshes'] + a['deformers']}
    new = {v['name']: v for v in b['meshes'] + b['deformers']}
    changes = {n: [k for k in v if k != 'editable_mesh_sha256' and v[k] != new[n].get(k)] for n, v in old.items()}
    changes = {n: v for n, v in changes.items() if v}
    targets = {'Head_XY_Base': [-30, 0, 30], 'Face_Warp': [-30, -15, 0, 15, 30], 'Neck_Y_Follow': [-30, 0, 30]}
    checks = {
        'source_matches_protected_backup': before.data == (HERE / 'Ren_base6_before_head_y.cmo3').read_bytes(),
        'source_matches_baseline_hash': hashlib.sha256(before.data).hexdigest() == json.loads((HERE / 'baseline.json').read_text(encoding='utf-8'))['sha256'],
        'all_parameter_definitions_preserved': a['parameters'] == b['parameters'],
        'all_48_artmeshes_retained': set(v['name'] for v in a['meshes']) == set(v['name'] for v in b['meshes']) and len(b['meshes']) == 48,
        'only_neck_y_deformer_added': set(new) - set(old) == {'Neck_Y_Follow'},
        'mesh_topology_preserved': mesh_data(before) == mesh_data(after),
        'images_and_placement_preserved': all(old[v['name']]['image'] == v['image'] for v in b['meshes']),
        'only_intended_original_objects_changed': changes == {'neck-clavicle': ['parent', 'forms'], 'Face_Warp': ['bindings', 'forms', 'grid'], 'Head_XY_Base': ['bindings', 'forms', 'grid']},
        'all_other_rig_data_including_z_iris_expression_ear_jaw_preserved': all(old[n] == new[n] for n in old if n not in ('Head_XY_Base', 'Face_Warp', 'neck-clavicle')),
        'all_y_bindings_single_axis_and_expected_keys': all(new[n]['bindings'] == [{'parameter': 'ParamAngleY', 'keys': keys}] for n, keys in targets.items()),
        'angle_x_remains_unbound': not any(v['parameter'] == 'ParamAngleX' for o in new.values() for v in o['bindings']),
        'only_three_y_objects': {n for n, o in new.items() if any(v['parameter'] == 'ParamAngleY' for v in o['bindings'])} == set(targets),
        'neck_y_inserted_inside_existing_z_parent': new['Neck_Y_Follow']['parent'] == 'Neck_Follow' and new['neck-clavicle']['parent'] == 'Neck_Y_Follow',
        'physics_and_atlas_count_preserved': a['physics'] == b['physics'] and a['atlas_count'] == b['atlas_count'],
    }
    for name in ('Head_XY_Base', 'Face_Warp'):
        guid = next(g['form'] for g in new[name]['grid'] if g['keys'] == [['ParamAngleY', 0.0]])
        form = next(f for f in new[name]['forms'] if f['guid'] == guid)
        # Adding keys assigns the original GUID to the first endpoint; central
        # form content must remain exact, independently of this identifier.
        checks[name + '_neutral_geometry_and_attributes_exactly_preserved'] = {k: v for k, v in form.items() if k != 'guid'} == {k: v for k, v in old[name]['forms'][0].items() if k != 'guid'}
    neutral_guid = next(g['form'] for g in new['Neck_Y_Follow']['grid'] if g['keys'] == [['ParamAngleY', 0.0]])
    neck_grid = positions(after, 'Neck_Y_Follow', neutral_guid)
    regular = np.array([(x / 5, y / 5) for y in range(6) for x in range(6)])
    # Rows can be stored transposed; both describe the same identity square.
    identity_error = min(float(np.max(np.abs(neck_grid - regular))), float(np.max(np.abs(neck_grid - regular[:, ::-1]))))
    neck_local_delta = float(np.max(np.abs(positions(before, 'neck-clavicle') - positions(after, 'neck-clavicle'))))
    checks['new_neck_neutral_grid_is_identity_within_1e_5'] = identity_error < 1e-5
    checks['neck_original_local_positions_preserved_within_1e_5'] = neck_local_delta < 1e-5
    errors = []
    for name, obj in new.items():
        wanted = set(itertools.product(*(v['keys'] for v in obj['bindings'])))
        got = [tuple(dict(g['keys'])[v['parameter']] for v in obj['bindings']) for g in obj['grid']]
        if set(got) != wanted or len(got) != len(set(got)) or any(g['form'] not in {f['guid'] for f in obj['forms']} for g in obj['grid']):
            errors.append(name)
    checks['all_key_grids_complete_unique_and_resolved'] = not errors
    checks['all_y_forms_distinct'] = all(len({f['positions_sha256'] for f in new[n]['forms']}) == len(keys) for n, keys in targets.items())
    checks['files_unchanged_during_read'] = all(c.data == c.path.read_bytes() for c in (before, after))
    result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'Read-only CAFF structure checks, separate from Editor visual acceptance. No runtime export test.',
              'checks': checks, 'all_static_checks_pass': all(checks.values()), 'existing_object_changes': changes,
              'neck_identity_error': identity_error, 'neck_local_coordinate_delta': neck_local_delta,
              'counts': {'meshes': len(b['meshes']), 'deformers': len(b['deformers']), 'parameters': len(b['parameters'])},
              'files': {label: {'path': str(c.path), 'bytes': len(c.data), 'sha256': hashlib.sha256(c.data).hexdigest()} for label, c in [('source', before), ('output', after)]},
              'key_bindings': targets, 'grid_errors': errors}
    for filename, data in [('after_inventory.json', b), ('verification.json', result)]:
        (HERE / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result['all_static_checks_pass']:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
