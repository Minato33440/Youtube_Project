"""Verify the saved Base Motion CMO3, exported runtime, and preview artifacts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
MODEL_PROJECT = ROOT.parents[1]
ART = MODEL_PROJECT / "art"
CMO = ROOT / "Ren_base.cmo3"
RUNTIME = ROOT / "runtime"
MODEL_JSON = RUNTIME / "Ren_base.model3.json"
OUT = ROOT / "preview"
PRISTINE = ROOT / "archive/before_foundation_20260930/Ren_deformer1.cmo3"
PRISTINE_SHA256 = "b0fd5db8b604262a4111e3c2213d6c29ab47d6fbb5bb2c6b53fd15f11998eae5"
AUDIT_MODULE = ROOT.parent / "training_base_audit/audit_cmo3.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgba_sha256(path: Path) -> str:
    with Image.open(path) as image:
        return hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()


def load_audit_module():
    spec = importlib.util.spec_from_file_location("ren_cmo_audit", AUDIT_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def children(summary: dict, parent: str) -> list[str]:
    return sorted(
        item["name"]
        for item in summary["meshes"] + summary["deformers"]
        if item["parent"] == parent
    )


def editable_mesh_contents(cmo) -> dict[str, list[tuple]]:
    """Compare real editable-mesh content while ignoring CAFF ref table indices."""
    contents = {}
    for item in cmo.objects("CArtMeshSource"):
        editable = next(item.iter("GEditableMesh2"))
        contents[cmo.name(item)] = [
            (
                node.tag,
                node.get("xs.n"),
                {key: value for key, value in node.attrib.items() if key != "xs.ref"},
                (node.text or "").strip(),
            )
            for node in editable.iter()
        ]
    return contents


def main() -> None:
    required = (CMO, MODEL_JSON, OUT / "render_verification.json")
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Export and render before verification: {missing}")

    audit = load_audit_module()
    cmo = audit.Cmo(CMO)
    summary = cmo.summarize()
    assert sha256(PRISTINE) == PRISTINE_SHA256
    assert len(summary["meshes"]) == 46
    assert set(("ParamHairFront", "Param", "ParamHairSide", "ParamHairBack")) <= set(summary["parameters"])
    assert summary["atlas_count"] == 0, "Editor checkpoint must remain atlas-free until final 4096 export"
    cmo_physics = [
        {
            "name": setting["name"],
            "inputs": [item["parameter"] for item in setting["inputs"]],
            "outputs": [item["parameter"] for item in setting["outputs"]],
        }
        for setting in summary["physics"]
    ]
    assert cmo_physics == [
        {"name": "Physics_HairFrontC_Practice", "inputs": ["ParamAngleZ"], "outputs": ["ParamHairFront"]},
        {"name": "Physics_Hair_ahoge_practice", "inputs": ["ParamAngleZ"], "outputs": ["Param"]},
        {"name": "Side hair", "inputs": ["ParamAngleZ"], "outputs": ["ParamHairSide"]},
        {"name": "Back hair", "inputs": ["ParamAngleZ"], "outputs": ["ParamHairBack"]},
    ]

    guid_names = {
        cmo.val(item.find("ACDrawableSource"), "guid"): cmo.name(item)
        for item in cmo.objects("CArtMeshSource")
    }
    clips = {
        item["name"]: [guid_names.get(guid, guid) for guid in item["clips"]]
        for item in summary["meshes"]
        if item["clips"]
    }
    assert clips == {
        "ALT_iris_L_blue": ["FILL_eye_white_L"],
        "ALT_iris_R_brown": ["FILL_eye_white_R"],
        "mouth_tongue": ["mouth_cavity"],
        "mouth_teeth_upper": ["mouth_cavity"],
    }
    assert children(summary, "Face_Rotation_Practice") == ["Head_XY_Base"]
    assert children(summary, "Head_XY_Base") == ["Face_Warp", "Hair_Base_Warp", "Mouth_Warp"]
    assert children(summary, "Jaw_Open") == ["face_underfill"]

    jaw = next(item for item in summary["deformers"] if item["name"] == "Jaw_Open")
    assert jaw["bindings"] == [{"parameter": "ParamMouthOpenY", "keys": [0.0, 1.0]}]
    rotation = next(
        item for item in summary["deformers"] if item["name"] == "Face_Rotation_Practice"
    )
    angles = []
    for grid_item in rotation["grid"]:
        form = next(item for item in rotation["forms"] if item["guid"] == grid_item["form"])
        angles.append((grid_item["keys"], float(form["form_attributes"]["angle"])))
    assert angles == [
        ([["ParamAngleZ", -30.0]], -15.0),
        ([["ParamAngleZ", 0.0]], 0.0),
        ([["ParamAngleZ", 30.0]], 15.0),
    ]

    parameter_usage = {parameter: [] for parameter in summary["parameters"]}
    for item in summary["meshes"] + summary["deformers"]:
        for binding in item["bindings"]:
            parameter_usage[binding["parameter"]].append(item["name"])
    assert parameter_usage["ParamHairSide"], "ParamHairSide has no deforming object"
    assert parameter_usage["ParamHairBack"], "ParamHairBack has no deforming object"

    motion_expectations = {
        "Neck_Follow": {
            "id": "Warp10", "parent": "ROOT", "parameter": "ParamAngleZ",
            "keys": [-30.0, 0.0, 30.0], "children": ["neck-clavicle"],
        },
        "Hair_Side_L_Sway": {
            "id": "Warp11", "parent": "Hair_Base_Warp", "parameter": "ParamHairSide",
            "keys": [-1.0, 0.0, 1.0], "children": ["hair_side_L"],
        },
        "Hair_Side_R_Sway": {
            "id": "Warp12", "parent": "Hair_Base_Warp", "parameter": "ParamHairSide",
            "keys": [-1.0, 0.0, 1.0], "children": ["hair_side_R"],
        },
        "Hair_Back_Sway": {
            "id": "Warp13", "parent": "Hair_Base_Warp", "parameter": "ParamHairBack",
            "keys": [-1.0, 0.0, 1.0], "children": ["hair_back"],
        },
    }
    for name, expected in motion_expectations.items():
        item = next(deformer for deformer in summary["deformers"] if deformer["name"] == name)
        assert item["id"] == expected["id"]
        assert item["parent"] == expected["parent"]
        assert item["bindings"] == [
            {"parameter": expected["parameter"], "keys": expected["keys"]}
        ]
        assert children(summary, name) == expected["children"]

    pristine_cmo = audit.Cmo(PRISTINE)
    current_meshes = editable_mesh_contents(cmo)
    pristine_meshes = editable_mesh_contents(pristine_cmo)
    changed_editable_meshes = sorted(
        name for name in current_meshes if current_meshes[name] != pristine_meshes[name]
    )
    assert changed_editable_meshes == ["hair_back", "neck-clavicle"]
    mesh_by_name = {item["name"]: item for item in summary["meshes"]}
    assert (mesh_by_name["hair_back"]["vertices"], mesh_by_name["hair_back"]["triangles"]) == (52, 70)
    assert (mesh_by_name["neck-clavicle"]["vertices"], mesh_by_name["neck-clavicle"]["triangles"]) == (65, 103)

    input_inventory = json.loads((ROOT / "input_inventory.json").read_text(encoding="utf-8"))
    expected_images = {
        item["name"]: item["image"]["rgba_sha256"]
        for item in input_inventory["meshes"]
    }
    assert set(expected_images) == {item["name"] for item in summary["meshes"]}
    manifest = json.loads((ART / "psd_front/manifest.json").read_text(encoding="utf-8"))
    source_paths = {
        item["name"]: (ART / "psd_front" / item["path"]).resolve()
        for item in manifest["layers"]
    }
    source_checks = []
    for name, expected_rgba in expected_images.items():
        path = source_paths.get(name, ART / "expression_rig/parts" / f"{name}.png")
        actual_rgba = rgba_sha256(path)
        source_checks.append(
            {
                "mesh": name,
                "path": str(path),
                "rgba_sha256": actual_rgba,
                "unchanged": actual_rgba == expected_rgba,
            }
        )
    assert len(source_checks) == 46
    assert all(item["unchanged"] for item in source_checks)

    config = json.loads(MODEL_JSON.read_text(encoding="utf-8-sig"))
    refs = config["FileReferences"]
    reference_paths = [refs["Moc"], refs["Physics"], refs["DisplayInfo"], *refs["Textures"]]
    for relative_path in reference_paths:
        assert (RUNTIME / relative_path).is_file(), relative_path
    physics = json.loads((RUNTIME / refs["Physics"]).read_text(encoding="utf-8-sig"))
    assert physics["Meta"]["PhysicsSettingCount"] == 4
    assert physics["Meta"]["Fps"] == 60
    physics_names = [item["Name"] for item in physics["Meta"]["PhysicsDictionary"]]
    assert physics_names == [
        "Physics_HairFrontC_Practice",
        "Physics_Hair_ahoge_practice",
        "Side hair",
        "Back hair",
    ]
    destinations = [
        setting["Output"][0]["Destination"]["Id"]
        for setting in physics["PhysicsSettings"]
    ]
    assert destinations == ["ParamHairFront", "Param", "ParamHairSide", "ParamHairBack"]
    assert len(refs["Textures"]) == 1
    with Image.open(RUNTIME / refs["Textures"][0]) as texture:
        assert texture.size == (2048, 2048)

    render = json.loads((OUT / "render_verification.json").read_text(encoding="utf-8"))
    assert render["drawable_count"] == 46
    changed = {case["label"]: case["changed_pixels_over_8"] for case in render["cases"]}
    for label in (
        "Blink left", "Blink right", "Blink both", "Mouth / jaw 1.0",
        "Z -30", "Z +30", "Side hair -1", "Side hair +1",
        "Back hair -1", "Back hair +1",
    ):
        assert changed[label] > 0, label
    for parameter in ("ParamHairFront", "ParamHairSide", "ParamHairBack"):
        low, high = render["physics_ranges"][parameter]
        assert high - low > 0.05, (parameter, low, high)
    for relative_path, expected in render["runtime_hashes"].items():
        assert sha256(ROOT / relative_path) == expected, relative_path

    probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe", "-v", "error", "-show_streams", "-show_format",
                "-of", "json", str(OUT / "Ren_base_motion.mp4"),
            ],
            text=True,
        )
    )
    video = next(stream for stream in probe["streams"] if stream["codec_type"] == "video")
    assert (video["width"], video["height"], int(video["nb_frames"])) == (420, 608, 360)
    assert abs(float(probe["format"]["duration"]) - 12) < 0.01

    samples = [0, 16, 23, 38, 66, 83, 109, 128, 145, 164, 173, 179]
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
    filmstrip = Image.new("RGB", (420 * 4, 608 * 3), "#f4f1ec")
    with Image.open(OUT / "Ren_base_motion.gif") as gif:
        assert gif.n_frames == 180
        duration_ms = 0
        for frame_number in range(gif.n_frames):
            gif.seek(frame_number)
            duration_ms += gif.info["duration"]
        assert abs(duration_ms - 12000) <= 20
        for index, frame_number in enumerate(samples):
            gif.seek(frame_number)
            frame = gif.convert("RGB")
            ImageDraw.Draw(frame).text(
                (10, 36), f"{frame_number / 15:.2f} seconds", fill="#222222", font=font
            )
            filmstrip.paste(frame, (index % 4 * 420, index // 4 * 608))
    filmstrip.save(OUT / "animation_review.jpg", quality=95)

    report = {
        "passed": True,
        "editor_file_sha256": sha256(CMO),
        "pristine_archive_unchanged": True,
        "source_count": len(source_checks),
        "source_rgba_matches_input_inventory": True,
        "sources": source_checks,
        "mesh_count": len(summary["meshes"]),
        "deformer_count": len(summary["deformers"]),
        "editor_atlas_count_before_final_export": summary["atlas_count"],
        "editor_physics": cmo_physics,
        "foundation": {
            "clips": clips,
            "z_angles": angles,
            "head_xy_children": children(summary, "Head_XY_Base"),
            "jaw_children": children(summary, "Jaw_Open"),
        },
        "hair_parameter_usage": {
            parameter: parameter_usage[parameter]
            for parameter in ("ParamHairFront", "Param", "ParamHairSide", "ParamHairBack")
        },
        "motion_connections": motion_expectations,
        "intentional_editable_mesh_changes": changed_editable_meshes,
        "runtime_hashes": render["runtime_hashes"],
        "physics_ranges": render["physics_ranges"],
        "video": {"size": [420, 608], "frames": 360, "duration_seconds": 12},
        "limits": [
            "Ahoge Param and physics are preserved, but the current ahoge shape keyforms are a known no-op until Boss rebuilds them.",
            "The automated render checks pixels and parameter response; final motion naturalness requires Boss review.",
            "VTube Studio and nizima LIVE tracking are not tested here.",
        ],
    }
    (ROOT / "verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"passed": True, "physics_ranges": report["physics_ranges"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
