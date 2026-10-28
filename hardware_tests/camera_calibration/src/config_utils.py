#!/usr/bin/env python3

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml


def _expand_env_in_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _expand_env_in_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_env_in_value(item) for item in value]
    if isinstance(value, str):
        return os.path.expandvars(value)
    return value


def load_config(config_path: str | Path) -> dict[str, Any]:
    config_path = Path(config_path).expanduser().resolve()
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError(f"Invalid configuration file: {config_path}")

    config = _expand_env_in_value(config)
    config["_config_path"] = str(config_path)
    config["_config_dir"] = str(config_path.parent)

    dataset_cfg = config.setdefault("dataset", {})
    dataset_path = dataset_cfg.get("path", "./dataset")
    dataset_path = Path(dataset_path)
    if not dataset_path.is_absolute():
        dataset_path = (config_path.parent / dataset_path).resolve()
    dataset_cfg["path"] = str(dataset_path)
    dataset_cfg.setdefault("image_format", "png")


    capture_cfg = config.setdefault("capture", {})
    capture_cfg.setdefault("interactive", True)
    capture_cfg.setdefault("show_preview", True)
    capture_cfg.setdefault("max_samples", 40)
    capture_cfg.setdefault("wait_after_prompt_s", 0.0)

    cameras = config.get("cameras", [])
    if not cameras:
        raise ValueError("Configuration must define at least one camera in 'cameras'.")

    names = set()
    for camera_cfg in cameras:
        name = camera_cfg.get("name")
        if not name:
            raise ValueError("Each camera entry must define 'name'.")
        if name in names:
            raise ValueError(f"Duplicate camera name: {name}")
        names.add(name)
        camera_cfg.setdefault("save_depth", False)
        camera_cfg.setdefault("options", {})

    robot_cfg = config.get("robot", {})
    if not robot_cfg:
        raise ValueError("Configuration must define a 'robot' section.")
    robot_cfg.setdefault("frame_name", "tool")
    robot_cfg.setdefault("options", {})

    board_cfg = config.setdefault("board", {})
    board_cfg.setdefault("type", "chessboard")
    board_cfg.setdefault("square_length_m", 0.040)
    board_cfg.setdefault("pattern_size", [11, 8])

    return config


def dumpable_config(config: dict[str, Any]) -> dict[str, Any]:
    config = copy.deepcopy(config)
    config.pop("_config_path", None)
    config.pop("_config_dir", None)
    return config
