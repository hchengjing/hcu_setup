#!/usr/bin/env python3

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from capture_backends import CameraCapture
from config_utils import dumpable_config
from pose_utils import PoseRecord


def ensure_session_layout(dataset_dir: str | Path, config: dict[str, Any]) -> Path:
    dataset_dir = Path(dataset_dir)
    dataset_dir.mkdir(parents=True, exist_ok=True)
    (dataset_dir / "poses").mkdir(exist_ok=True)
    for camera_cfg in config["cameras"]:
        color_dir = dataset_dir / camera_cfg["name"] / "color"
        color_dir.mkdir(parents=True, exist_ok=True)
        if camera_cfg.get("save_depth", False):
            (dataset_dir / camera_cfg["name"] / "depth").mkdir(parents=True, exist_ok=True)
    return dataset_dir


def write_session_file(dataset_dir: Path, config: dict[str, Any]) -> None:
    session_path = dataset_dir / "session.json"
    if session_path.exists():
        return

    payload = {
        "created_utc": datetime.now(UTC).isoformat(),
        "config": dumpable_config(config),
        "cameras": [
            {
                "name": camera_cfg["name"],
                "backend": camera_cfg["backend"],
                "save_depth": bool(camera_cfg.get("save_depth", False)),
                "calibration_type": camera_cfg.get("calibration_type", "eye_in_hand"),
            }
            for camera_cfg in config["cameras"]
        ],
        "robot": {
            "backend": config["robot"]["backend"],
            "frame_name": config["robot"].get("frame_name", "tool"),
        },
    }
    session_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _existing_ids_from_paths(paths: list[Path]) -> list[int]:
    ids = []
    for path in paths:
        try:
            ids.append(int(path.stem))
        except ValueError:
            continue
    return sorted(ids)


def next_capture_index(dataset_dir: str | Path) -> int:
    dataset_dir = Path(dataset_dir)
    pose_paths = list((dataset_dir / "poses").glob("*.json"))
    if pose_paths:
        ids = _existing_ids_from_paths(pose_paths)
        return ids[-1] + 1 if ids else 0

    return 0


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_capture(
    dataset_dir: str | Path,
    capture_id: int,
    pose: PoseRecord,
    camera_captures: dict[str, CameraCapture],
    config: dict[str, Any],
) -> None:
    dataset_dir = Path(dataset_dir)
    image_format = config["dataset"].get("image_format", "png").lstrip(".")
    capture_key = f"{capture_id:04d}"

    pose_payload = pose.to_json()
    pose_payload["capture_id"] = capture_key
    pose_payload["captured_at_utc"] = datetime.now(UTC).isoformat()
    pose_payload["cameras"] = {}

    for camera_cfg in config["cameras"]:
        name = camera_cfg["name"]
        capture = camera_captures[name]
        color_rel_path = Path(name) / "color" / f"{capture_key}.{image_format}"
        color_abs_path = dataset_dir / color_rel_path
        if not cv2.imwrite(str(color_abs_path), capture.color_bgr):
            raise RuntimeError(f"Failed to save image: {color_abs_path}")

        depth_rel_path = None
        if capture.depth is not None:
            depth_rel_path = Path(name) / "depth" / f"{capture_key}.png"
            depth_abs_path = dataset_dir / depth_rel_path
            depth_image = np.asarray(capture.depth)
            if depth_image.dtype != np.uint16:
                depth_image = depth_image.astype(np.uint16)
            if not cv2.imwrite(str(depth_abs_path), depth_image):
                raise RuntimeError(f"Failed to save depth image: {depth_abs_path}")

        pose_payload["cameras"][name] = {
            "color_path": str(color_rel_path),
            "depth_path": str(depth_rel_path) if depth_rel_path is not None else None,
            "metadata": capture.metadata,
        }

    pose_path = dataset_dir / "poses" / f"{capture_key}.json"
    _write_json(pose_path, pose_payload)

