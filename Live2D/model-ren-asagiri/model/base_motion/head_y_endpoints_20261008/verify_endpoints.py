"""Read-only verification of Cubism-authored three-key Y endpoint draft."""
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
sys.path.insert(0, str(BASE / 'head_y_implementation_20261008'))
from verify_head_y import Cmo, positions, mesh_data

def stripped(obj, *keys):
    return {k: v for k, v in obj.items() if k not in keys}

def keyform(obj, value):
    guid = next(g['form'] for g in obj['grid'] if g['keys'] == [['ParamAngleY', value]])
    return next(f for f in obj['forms'] if f['guid'] == guid)

def main():
    before = Cmo(BASE / 'Ren_base6.cmo3')
    after = Cmo(BASE / 'Ren_base7(2).cmo3')
    donor = Cmo(HERE / 'Ren_base7_with_under_chin_before.cmo3')
    a, b, ds = before.summarize(), after.summarize(), donor.summarize()
    old = {v['name']: v for v in a['meshes'] + a['deformers']}
    new = {v['name']: v for v in b['meshes'] + b['deformers']}
    targets = {'Face_Warp', 'Mouth_Y_Follow', 'Hair_Y_Follow', 'ear_L', 'ear_R', 'neck-clavicle', 'under_chin'}
    changed_originals = {'Face_Warp', 'ear_L', 'ear_R', 'neck-clavicle', 'Mouth_Warp', 'Hair_Base_Warp'}
    changes = {n: [k for k in o if k != 'editable_mesh_sha256' and o[k] != new[n].get(k)] for n, o in old.items()}
    changes = {n: v for n, v in changes.items() if v}
    topo_a, topo_b = mesh_data(before), mesh_data(after)
    checks = {
        'source_matches_backup': before.data == (HERE / 'Ren_base6_before_endpoints.cmo3').read_bytes(),
        'source_matches_initial_hash': hashlib.sha256(before.data).hexdigest() == 'a0caa0d82aff2d7cf1d5281a80be7891d64a3126225fa58ac4af065f4b7e4256',
        'previous_base7_unchanged': hashlib.sha256((BASE / 'Ren_base7.cmo3').read_bytes()).hexdigest() == 'e61fdd7a19b28aedcfe18cc225f343a33d45ddbc0cdf8ec0908188cd55ab875b',
        'parameter_definitions_preserved': a['parameters'] == b['parameters'],
        'all_original_objects_retained': set(old) <= set(new),
        'only_expected_additions': set(new) - set(old) == {'Mouth_Y_Follow', 'Hair_Y_Follow', 'under_chin'},
        'original_mesh_topology_preserved': all(topo_a[n] == topo_b[n] for n in topo_a),
        'all_original_images_and_placement_preserved': all(o['image'] == new[o['name']]['image'] for o in a['meshes']),
        'under_chin_image_matches_imported_donor': new['under_chin']['image'] == next(m['image'] for m in ds['meshes'] if m['name'] == 'under_chin'),
        'only_expected_original_objects_changed': set(changes) == changed_originals,
        'all_other_original_rig_data_preserved': all(stripped(o, 'editable_mesh_sha256') == stripped(new[n], 'editable_mesh_sha256') for n, o in old.items() if n not in changed_originals),
        'exactly_seven_y_objects': {n for n, o in new.items() if any(v['parameter'] == 'ParamAngleY' for v in o['bindings'])} == targets,
        'all_y_bindings_only_minus30_zero_plus30': all(new[n]['bindings'] == [{'parameter': 'ParamAngleY', 'keys': [-30, 0, 30]}] for n in targets),
        'head_x_remains_unbound_as_in_base6': not any(v['parameter'] == 'ParamAngleX' for o in new.values() for v in o['bindings']),
        'physics_and_atlas_count_preserved': a['physics'] == b['physics'] and a['atlas_count'] == b['atlas_count'],
        'under_chin_hidden_at_front_and_down': all(keyform(new['under_chin'], v)['opacity'] == 0 for v in (-30, 0)),
        'under_chin_visible_at_up': keyform(new['under_chin'], 30)['opacity'] == 1,
        'new_parents_inserted_in_expected_hierarchy': all(new[p]['parent'] == 'Head_XY_Base' and new[c]['parent'] == p for c, p in [('Mouth_Warp', 'Mouth_Y_Follow'), ('Hair_Base_Warp', 'Hair_Y_Follow')]) and new['under_chin']['parent'] == 'Jaw_Open',
    }
    for n in ('Face_Warp', 'ear_L', 'ear_R', 'neck-clavicle'):
        checks[n + '_neutral_exact'] = stripped(keyform(new[n], 0), 'guid') == stripped(old[n]['forms'][0], 'guid')
    # GUI insertion converts child coordinates into its new parent's rectangle.
    # Reconstruct the affine neutral parent map before comparing all old forms.
    errors = {}
    regular = np.array([(x / 5, y / 5, 1) for y in range(6) for x in range(6)])
    for child, parent in [('Hair_Base_Warp', 'Hair_Y_Follow'), ('Mouth_Warp', 'Mouth_Y_Follow')]:
        pp = positions(after, parent, keyform(new[parent], 0)['guid'])
        transform = np.linalg.lstsq(regular, pp, rcond=None)[0]
        affine_error = float(np.max(np.abs(regular @ transform - pp)))
        max_error = 0.0
        for f in old[child]['forms']:
            prior = positions(before, child, f['guid'])
            current = positions(after, child, f['guid'])
            remapped = np.column_stack([current, np.ones(len(current))]) @ transform
            max_error = max(max_error, float(np.max(np.abs(remapped - prior))))
        errors[child] = {'neutral_parent_affine_error': affine_error, 'all_forms_max_coordinate_error_in_original_parent': max_error}
        checks[child + '_all_original_forms_geometry_preserved_within_1e_5'] = affine_error < 1e-5 and max_error < 1e-5
        omit = ('positions_sha256', 'positions_bbox')
        checks[child + '_original_keys_and_nonposition_attributes_preserved'] = old[child]['grid'] == new[child]['grid'] and old[child]['bindings'] == new[child]['bindings'] and [stripped(f, *omit) for f in old[child]['forms']] == [stripped(f, *omit) for f in new[child]['forms']]
    grid_errors = []
    for n, obj in new.items():
        wanted = set(itertools.product(*(v['keys'] for v in obj['bindings'])))
        got = [tuple(dict(g['keys'])[v['parameter']] for v in obj['bindings']) for g in obj['grid']]
        if set(got) != wanted or len(got) != len(set(got)) or any(g['form'] not in {f['guid'] for f in obj['forms']} for g in obj['grid']):
            grid_errors.append(n)
    checks['all_key_grids_complete_unique_and_resolved'] = not grid_errors
    checks['files_unchanged_during_read'] = all(c.data == c.path.read_bytes() for c in (before, after, donor))
    result = {
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Read-only CAFF structure and neutral-parent coordinate reconstruction. Not visual acceptance, runtime validation, intermediate tuning or compound-pose validation.',
        'checks': checks, 'all_static_checks_pass': all(checks.values()),
        'existing_object_changes': changes, 'coordinate_errors': errors, 'grid_errors': grid_errors,
        'counts': {'meshes': len(b['meshes']), 'deformers': len(b['deformers']), 'parameters': len(b['parameters'])},
        'y_bindings': {n: new[n]['bindings'] for n in sorted(targets)},
        'files': {label: {'path': str(c.path), 'bytes': len(c.data), 'sha256': hashlib.sha256(c.data).hexdigest()} for label, c in [('source', before), ('output', after), ('donor_backup', donor)]},
    }
    for filename, value in [('after_inventory.json', b), ('verification.json', result)]:
        (HERE / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result['all_static_checks_pass']:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
