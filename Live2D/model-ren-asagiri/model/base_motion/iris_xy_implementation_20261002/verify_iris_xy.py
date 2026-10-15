"""Read-only saved CMO3 verification for Cubism-authored iris XY rigging.

Uses the repository CAFF reader, not the Cubism runtime. Never writes CMO3.
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
    return {cmo.name(m): {
        "editable_mesh": semantic(cmo, next(m.iter("GEditableMesh2"), None)),
        "triangles": semantic(cmo, cmo.field(m, "indices")),
    } for m in cmo.objects("CArtMeshSource")}


def main():
    before, after = [Cmo(BASE / n) for n in ("Ren_base5.cmo3", "Ren_base6.cmo3")]
    a, b = before.summarize(), after.summarize()
    old = {x["name"]: x for x in a["meshes"] + a["deformers"]}
    new = {x["name"]: x for x in b["meshes"] + b["deformers"]}
    expected = {f"Iris_{s}_{axis}": f"ParamEyeBall{axis}"
                for s in ("L", "R") for axis in ("X", "Y")}
    irises = {"ALT_iris_L_blue": "L", "ALT_iris_R_brown": "R"}
    changes = {n: [k for k in obj if k != "editable_mesh_sha256" and obj[k] != new[n][k]]
               for n, obj in old.items()}
    changes = {n: fields for n, fields in changes.items() if fields}
    checks = {
        "source_base5_matches_backup": before.data == (HERE / "Ren_base5_before_iris_xy.cmo3").read_bytes(),
        "source_base5_matches_baseline_hash": digest(before.data) == json.loads((HERE / "baseline.json").read_text(encoding="utf-8"))["sha256"],
        "all_parameter_definitions_unchanged": a["parameters"] == b["parameters"],
        "all_48_meshes_retained": {x["name"] for x in a["meshes"]} == {x["name"] for x in b["meshes"]} and len(b["meshes"]) == 48,
        "only_four_expected_deformers_added": set(new) - set(old) == set(expected) and set(old) <= set(new),
        "editable_meshes_and_triangles_unchanged": mesh_data(before) == mesh_data(after),
        "all_images_and_placement_unchanged": all(old[x["name"]]["image"] == x["image"] for x in b["meshes"]),
        "all_existing_visibility_unchanged": all(old[n]["visible"] == new[n]["visible"] for n in old),
        "all_original_deformers_unchanged": all(old[x["name"]] == new[x["name"]] for x in a["deformers"]),
        "only_iris_parent_and_local_coordinates_changed": set(changes) == set(irises) and all(set(v) == {"parent", "forms"} for v in changes.values()),
        "physics_unchanged": a["physics"] == b["physics"],
        "atlas_count_unchanged": a["atlas_count"] == b["atlas_count"],
    }
    iris_checks = {}
    for name, side in irises.items():
        x, y = old[name], new[name]
        iris_checks[name] = {
            "parent_is_y": y["parent"] == f"Iris_{side}_Y",
            "open_binding_unchanged": x["bindings"] == y["bindings"],
            "key_grid_unchanged": x["grid"] == y["grid"],
            "clips_unchanged": x["clips"] == y["clips"],
            "opacities_unchanged": [(f["guid"], f["opacity"]) for f in x["forms"]] == [(f["guid"], f["opacity"]) for f in y["forms"]],
        }
    checks["existing_iris_open_keys_opacities_clips_preserved"] = all(all(v.values()) for v in iris_checks.values())
    new_checks = {}
    for name, parameter in expected.items():
        obj = new[name]
        side, axis = name.split("_")[1:]
        parent = ("Left_Eye" if side == "L" else "Right_Eye") if axis == "X" else f"Iris_{side}_X"
        forms = {f["guid"]: f for f in obj["forms"]}
        by_key = {g["keys"][0][1]: forms[g["form"]] for g in obj["grid"]}
        row = {
            "parameter": parameter, "id": obj["id"], "parent": obj["parent"],
            "correct_parent": obj["parent"] == parent,
            "correct_three_key_binding": obj["bindings"] == [{"parameter": parameter, "keys": [-1.0, 0.0, 1.0]}],
            "three_distinct_forms": len(forms) == 3 and len({f["positions_sha256"] for f in forms.values()}) == 3,
            "full_opacity": all(f["opacity"] == 1 for f in forms.values()),
            "bbox_by_key": {str(k): by_key[k]["positions_bbox"] for k in (-1, 0, 1)},
        }
        # Local Y uses image coordinates (positive down); +ParamEyeBallY moves up.
        coord = 0 if axis == "X" else 1
        centers = [(by_key[k]["positions_bbox"][coord] + by_key[k]["positions_bbox"][coord + 2]) / 2 for k in (-1, 0, 1)]
        row["correct_axis_direction"] = bool(centers[0] < centers[1] < centers[2] if axis == "X" else centers[0] > centers[1] > centers[2])
        new_checks[name] = row
    checks["all_new_xy_deformers_valid"] = all(all(v for v in row.values() if isinstance(v, bool)) for row in new_checks.values())
    errors = []
    for name, obj in new.items():
        bindings = obj["bindings"]
        wanted = set(itertools.product(*(x["keys"] for x in bindings)))
        got = [tuple(dict(g["keys"])[x["parameter"]] for x in bindings) for g in obj["grid"]]
        if set(got) != wanted or len(got) != len(set(got)) or any(g["form"] not in {f["guid"] for f in obj["forms"]} for g in obj["grid"]):
            errors.append(name)
    checks["all_object_key_grids_complete_unique_resolved"] = not errors
    checks["files_unchanged_during_read"] = all(c.data == c.path.read_bytes() for c in (before, after))
    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Read-only saved CMO3 structure; Editor visual results documented separately. No runtime test.",
        "before": {"file": str(before.path), "bytes": len(before.data), "sha256": digest(before.data)},
        "after": {"file": str(after.path), "bytes": len(after.data), "sha256": digest(after.data)},
        "counts": {"meshes": len(b["meshes"]), "deformers_before": len(a["deformers"]), "deformers_after": len(b["deformers"]), "parameters": len(b["parameters"]), "key_grid_entries": sum(len(x["grid"]) for x in new.values())},
        "checks": checks, "all_static_checks_pass": all(checks.values()),
        "existing_object_changes": changes, "iris_checks": iris_checks,
        "new_deformers": new_checks, "grid_errors": errors,
        "runtime_export_or_app_test": False,
    }
    for filename, data in (("after_inventory.json", b), ("verification.json", result)):
        (HERE / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("all_static_checks_pass", "checks", "counts", "after", "existing_object_changes")}, ensure_ascii=False, indent=2))
    if not result["all_static_checks_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
