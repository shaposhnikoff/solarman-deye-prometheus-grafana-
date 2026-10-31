from __future__ import annotations

from pathlib import Path

import yaml


def sample_profile() -> dict:
    return {
        "requests": [{"start": 1, "end": 2, "mb_functioncode": 3}],
        "parameters": [
            {
                "group": "test",
                "items": [
                    {
                        "name": "Grid Power",
                        "uom": "W",
                        "rule": 2,
                        "registers": [1],
                    },
                    {
                        "name": "Total Production",
                        "uom": "kWh",
                        "rule": 1,
                        "registers": [2],
                    },
                    {
                        "name": "Battery SOC",
                        "uom": "%",
                        "rule": 1,
                        "registers": [2],
                    },
                    {
                        "name": "Battery Status",
                        "uom": "",
                        "rule": 1,
                        "registers": [1],
                        "isstr": True,
                        "lookup": [{"key": 65535, "value": "Charge"}],
                    },
                    {
                        "name": "Grid-connected Status",
                        "uom": "",
                        "rule": 1,
                        "registers": [2],
                        "isstr": True,
                        "lookup": [
                            {"key": 0, "value": "Off-Grid"},
                            {"key": 1, "value": "On-Grid"},
                        ],
                    },
                ],
            }
        ],
    }


def write_profile(path: Path, profile: dict) -> Path:
    path.write_text(yaml.safe_dump(profile), encoding="utf-8")
    return path
