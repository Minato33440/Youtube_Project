"""Read-only verification of the Cubism-authored base4 -> base5 eyebrow change.

Uses the repository's internal CAFF reader; this is not runtime validation.
Never writes a CMO3. Re-run after an Editor save to refresh the evidence JSON.
"""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import itertools
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE.parent / "training_base_audit"))
from audit_cmo3 import Cmo


def digest(data):
    return hashlib.sha256(data).hexdigest()


def semantic(cmo, element):
    """Resolve archive references; omit only serializer bookkeeping attributes."""
    if element is None:
        return None
    field_name = element.get("xs.n")
    element = cmo.res(element)
    attrs = {k: v for k, v in element.attrib.items()
             if k not in ("xs.id", "xs.ref", "xs.idx")}
    if field_name is not None:
        attrs["xs.n"] = field_name
    return [element.tag, attrs, " ".join((element.text or "").split()),
            [semantic(cmo, child) for child in element]]


def mesh_data(cmo):
    result = {}
    for mesh in cmo.objects("CArtMeshSource"):
        result[cmo.name(mesh)] = {
            "editable_mesh": semantic(cmo, next(mesh.iter("GEditableMesh2"), None)),
            "triangle_indices": semantic(cmo, cmo.field(mesh, "indices")),
        }
    return result


def main():
    before, after = [Cmo(BASE / name) for name in ("Ren_base4.cmo3", "Ren_base5.cmo3")]
    a, b = before.summarize(), after.summarize()
    expected = {}
    for side in ("L", "R"):
        for axis in ("Y", "X", "Angle", "Form"):
            expected[f"Brow_{side}_{axis}"] = f"ParamBrow{side}{axis}"
    old = {x["name"]: x for x in a["meshes"] + a["deformers"]}
    new = {x["name"]: x for x in b["meshes"] + b["deformers"]}
    checks = {
        "base4_matches_protected_backup": before.data == (HERE / "Ren_base4_before_brows.cmo3").read_bytes(),
        "base4_matches_recorded_hash": digest(before.data) == json.loads((HERE / "baseline.json").read_text(encoding="utf-8"))["sha256"],
        "all_parameter_definitions_unchanged": a["parameters"] == b["parameters"],
        "all_48_meshes_retained": set(x["name"] for x in a["meshes"]) == set(x["name"] for x in b["meshes"]) and len(b["meshes"]) == 48,
        "only_eight_expected_deformers_added": set(new) - set(old) == set(expected) and set(old) <= set(new),
        "all_editable_mesh_and_triangle_data_unchanged": mesh_data(before) == mesh_data(after),
        "active_images_rgba_and_placement_unchanged": all(old[x["name"]]["image"] == x["image"] for x in b["meshes"]),
        "all_original_visibility_restored": all(old[n]["visible"] == new[n]["visible"] for n in old),
        "physics_inventory_unchanged": a["physics"] == b["physics"],
        "atlas_count_unchanged": a["atlas_count"] == b["atlas_count"],
    }
    changes = {}
    for name, original in old.items():
        changes[name] = [k for k in original if k != "editable_mesh_sha256" and original[k] != new[name][k]]
    changes = {k: v for k, v in changes.items() if v}
    checks["only_brow_parent_and_local_keyform_data_changed"] = set(changes) == {"brow_L", "brow_R"} and all(set(v) <= {"parent", "forms"} for v in changes.values())
    checks["all_previous_deformer_fields_unchanged"] = all(old[x["name"]] == new[x["name"]] for x in a["deformers"])
    brow_checks = {}
    for name, parameter in expected.items():
        obj = new[name]
        side, axis = name.split("_")[1:]
        parent = {"Angle": "Face_Warp", "X": f"Brow_{side}_Angle", "Y": f"Brow_{side}_X", "Form": f"Brow_{side}_Y"}[axis]
        form_map = {f["guid"]: f for f in obj["forms"]}
        by_key = {g["keys"][0][1]: form_map[g["form"]] for g in obj["grid"]}
        payload = [json.dumps({k: v for k, v in by_key[key].items() if k != "guid"}, sort_keys=True) for key in (-1, 0, 1)]
        row = {
            "parameter": parameter, "parent": obj["parent"], "object_id": obj["id"],
            "correct_parent": obj["parent"] == parent,
            "three_key_binding": obj["bindings"] == [{"parameter": parameter, "keys": [-1.0, 0.0, 1.0]}],
            "three_distinct_forms": len(obj["forms"]) == 3 and len(set(payload)) == 3,
        }
        if axis == "Angle":
            row["angles_at_minus_zero_plus"] = [float(by_key[k]["form_attributes"]["angle"]) for k in (-1, 0, 1)]
            row["correct_angles"] = row["angles_at_minus_zero_plus"] == ([-12, 0, 12] if side == "L" else [12, 0, -12])
        brow_checks[name] = row
    checks["all_brow_deformers_valid"] = all(all(v for v in row.values() if isinstance(v, bool)) for row in brow_checks.values())
    checks["brow_meshes_under_form_deformers"] = all(new[f"brow_{s}"]["parent"] == f"Brow_{s}_Form" for s in ("L", "R"))
    grid_errors = []
    for name, obj in new.items():
        bindings = obj["bindings"]
        expected_keys = set(itertools.product(*(x["keys"] for x in bindings)))
        actual = [tuple(dict(g["keys"])[x["parameter"]] for x in bindings) for g in obj["grid"]]
        forms = {f["guid"] for f in obj["forms"]}
        if set(actual) != expected_keys or len(actual) != len(set(actual)) or any(g["form"] not in forms for g in obj["grid"]):
            grid_errors.append(name)
    checks["all_object_key_grids_complete_unique_resolved"] = not grid_errors
    checks["source_files_unchanged_during_read"] = all(c.data == c.path.read_bytes() for c in (before, after))
    usage = {p: [] for p in b["parameters"]}
    for obj in new.values():
        for bind in obj["bindings"]:
            usage[bind["parameter"]].append(obj["name"])
    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Read-only saved CMO3 structure and active image comparison, not Cubism SDK or runtime acceptance.",
        "before": {"file": str(before.path), "sha256": digest(before.data), "bytes": len(before.data)},
        "after": {"file": str(after.path), "sha256": digest(after.data), "bytes": len(after.data)},
        "counts": {"meshes": len(b["meshes"]), "deformers_before": len(a["deformers"]), "deformers_after": len(b["deformers"]), "parameters": len(b["parameters"]), "key_grid_entries": sum(len(o["grid"]) for o in new.values())},
        "checks": checks, "all_static_checks_pass": all(checks.values()),
        "existing_object_changes": changes, "new_brow_deformers": brow_checks,
        "grid_errors": grid_errors, "parameter_usage": usage,
        "serializer_note": "GEditableMesh2 raw XML hashes for face_underfill and eyelash_closed_L differ due to xs.ref/xs.id/xs.idx renumbering. Resolved semantic mesh data and triangle indices are compared for all 48 meshes.",
        "runtime_export_or_app_test": False,
    }
    (HERE / "after_inventory.json").write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"all_static_checks_pass": result["all_static_checks_pass"], "checks": checks, "counts": result["counts"], "after": result["after"], "existing_object_changes": changes, "grid_errors": grid_errors}, ensure_ascii=False, indent=2))
    if not result["all_static_checks_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
