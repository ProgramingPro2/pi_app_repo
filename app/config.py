"""
Persistent configuration helpers for the Raspberry Pi thermal viewer.
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
from typing import Optional


CONFIG_DIR = pathlib.Path.home() / ".config" / "libseek-pi"
CONFIG_PATH = CONFIG_DIR / "config.json"


@dataclasses.dataclass
class ConfigData:
    camera_type: str = "seekpro"
    palette_index: int = 2
    threshold_c: float = 30.0
    threshold_mode: str = ">"
    auto_exposure_lock: bool = False
    ffc_path: Optional[str] = None
    temperature_unit: str = "C"
    default_threshold_c: float = 30.0
    default_threshold_f: float = 86.0


def load_config() -> ConfigData:
    if not CONFIG_PATH.exists():
        return ConfigData()

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except (OSError, json.JSONDecodeError):
        return ConfigData()

    defaults = dataclasses.asdict(ConfigData())
    defaults.update(payload)
    return ConfigData(**defaults)


def save_config(config: ConfigData) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as fp:
        json.dump(dataclasses.asdict(config), fp, indent=2)

