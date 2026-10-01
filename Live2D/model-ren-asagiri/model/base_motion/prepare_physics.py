"""Build a four-group Cubism physics file without modifying a CMO3 model.

The first two groups come from the Cubism-exported training runtime. The side
and back hair groups come from the previously accepted head/neck/hair model.
Only setting IDs and aggregate metadata are regenerated.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
DEFAULT_CURRENT = (
    PROJECT
    / "Live2D/Traning/Lesson10_RuntimeExport/runtime/"
    / "Ren_training_L10_deformer01.physics3.json"
)
DEFAULT_LEGACY = HERE.parent / "head_neck_hair/Ren_hair.physics3.json"
DEFAULT_OUTPUT = HERE / "Ren_base_4groups.physics3.json"

CURRENT_NAMES = (
    "Physics_HairFrontC_Practice",
    "Physics_Hair_ahoge_practice",
)
LEGACY_NAMES = ("Side hair", "Back hair")
EXPECTED_OUTPUT_PARAMETERS = (
    "ParamHairFront",
    "Param",
    "ParamHairSide",
    "ParamHairBack",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def settings_by_name(document: dict) -> dict[str, dict]:
    dictionaries = document["Meta"]["PhysicsDictionary"]
    names_by_id = {item["Id"]: item["Name"] for item in dictionaries}
    settings = document["PhysicsSettings"]
    if set(names_by_id) != {item["Id"] for item in settings}:
        raise ValueError("PhysicsDictionary and PhysicsSettings IDs do not match")
    return {names_by_id[item["Id"]]: item for item in settings}


def select(document: dict, names: tuple[str, ...]) -> list[tuple[str, dict]]:
    available = settings_by_name(document)
    missing = [name for name in names if name not in available]
    if missing:
        raise ValueError(f"Missing physics groups: {missing}")
    return [(name, deepcopy(available[name])) for name in names]


def destination_parameter(setting: dict) -> str:
    outputs = setting["Output"]
    if len(outputs) != 1:
        raise ValueError(f"Expected one output in {setting['Id']}")
    return outputs[0]["Destination"]["Id"]


def validate_group(name: str, setting: dict, output_parameter: str) -> None:
    inputs = setting["Input"]
    if len(inputs) != 1 or inputs[0]["Source"]["Id"] != "ParamAngleZ":
        raise ValueError(f"{name} must have one ParamAngleZ input")
    if destination_parameter(setting) != output_parameter:
        raise ValueError(
            f"{name} output is {destination_parameter(setting)}, "
            f"expected {output_parameter}"
        )


def build(current: dict, legacy: dict) -> dict:
    groups = select(current, CURRENT_NAMES) + select(legacy, LEGACY_NAMES)
    for (name, setting), parameter in zip(
        groups, EXPECTED_OUTPUT_PARAMETERS, strict=True
    ):
        validate_group(name, setting, parameter)

    settings = []
    dictionary = []
    for index, (name, setting) in enumerate(groups, start=1):
        setting_id = f"PhysicsSetting{index}"
        setting["Id"] = setting_id
        settings.append(setting)
        dictionary.append({"Id": setting_id, "Name": name})

    meta = deepcopy(current["Meta"])
    meta.update(
        {
            "PhysicsSettingCount": len(settings),
            "TotalInputCount": sum(len(item["Input"]) for item in settings),
            "TotalOutputCount": sum(len(item["Output"]) for item in settings),
            "VertexCount": sum(len(item["Vertices"]) for item in settings),
            "PhysicsDictionary": dictionary,
        }
    )
    return {
        "Version": current["Version"],
        "Meta": meta,
        "PhysicsSettings": settings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", type=Path, default=DEFAULT_CURRENT)
    parser.add_argument("--legacy", type=Path, default=DEFAULT_LEGACY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    current = args.current.resolve()
    legacy = args.legacy.resolve()
    output = args.output.resolve()
    if output in {current, legacy}:
        raise ValueError("Output must not overwrite either source file")

    document = build(load_json(current), load_json(legacy))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, ensure_ascii=False, indent="\t") + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "output_sha256": sha256(output),
                "current_source_sha256": sha256(current),
                "legacy_source_sha256": sha256(legacy),
                "groups": [
                    {
                        "name": item["Name"],
                        "output": destination_parameter(setting),
                    }
                    for item, setting in zip(
                        document["Meta"]["PhysicsDictionary"],
                        document["PhysicsSettings"],
                        strict=True,
                    )
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
