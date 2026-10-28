#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.spatial.transform import Rotation as R


@dataclass
class PoseRecord:
    position_m: np.ndarray
    orientation_xyzw: np.ndarray
    frame_name: str
    source: str
    metadata: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        data = dict(self.metadata)
        data.update(
            {
                "position": self.position_m.tolist(),
                "orientation": self.orientation_xyzw.tolist(),
                "position_units": "meters",
                "quaternion_format": "xyzw",
                "frame_name": self.frame_name,
                "pose_source": self.source,
            }
        )
        return data


def ensure_xyzw(quaternion: list[float] | np.ndarray, quaternion_format: str) -> np.ndarray:
    quat = np.asarray(quaternion, dtype=np.float64)
    if quat.shape != (4,):
        raise ValueError(f"Quaternion must have shape (4,), got {quat.shape}")
    fmt = quaternion_format.lower()
    if fmt == "xyzw":
        return quat
    if fmt == "wxyz":
        return np.array([quat[1], quat[2], quat[3], quat[0]], dtype=np.float64)
    raise ValueError(f"Unsupported quaternion format: {quaternion_format}")


def xyzw_to_wxyz(quaternion_xyzw: np.ndarray) -> np.ndarray:
    quaternion_xyzw = np.asarray(quaternion_xyzw, dtype=np.float64)
    return np.array(
        [
            quaternion_xyzw[3],
            quaternion_xyzw[0],
            quaternion_xyzw[1],
            quaternion_xyzw[2],
        ],
        dtype=np.float64,
    )


def pose_to_matrix(position_m: list[float] | np.ndarray, quaternion_xyzw: list[float] | np.ndarray) -> np.ndarray:
    transform = np.eye(4, dtype=np.float64)
    transform[:3, :3] = R.from_quat(np.asarray(quaternion_xyzw, dtype=np.float64)).as_matrix()
    transform[:3, 3] = np.asarray(position_m, dtype=np.float64)
    return transform


def invert_transform(transform: np.ndarray) -> np.ndarray:
    rotation = transform[:3, :3]
    translation = transform[:3, 3]
    inverse = np.eye(4, dtype=np.float64)
    inverse[:3, :3] = rotation.T
    inverse[:3, 3] = -rotation.T @ translation
    return inverse


def matrix_to_pose(transform: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    transform = np.asarray(transform, dtype=np.float64)
    translation = transform[:3, 3]
    quaternion_xyzw = R.from_matrix(transform[:3, :3]).as_quat()
    return translation, quaternion_xyzw
