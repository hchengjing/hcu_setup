#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from pose_utils import ensure_xyzw, invert_transform, matrix_to_pose, pose_to_matrix, xyzw_to_wxyz


_HAND_EYE_METHODS = {
    "tsai": cv2.CALIB_HAND_EYE_TSAI,
    "park": cv2.CALIB_HAND_EYE_PARK,
    "horaud": cv2.CALIB_HAND_EYE_HORAUD,
    "andreff": cv2.CALIB_HAND_EYE_ANDREFF,
    "daniilidis": cv2.CALIB_HAND_EYE_DANIILIDIS,
}


def load_session(dataset_dir: str | Path) -> dict[str, Any]:
    dataset_dir = Path(dataset_dir)
    session_path = dataset_dir / "session.json"
    if session_path.exists():
        return json.loads(session_path.read_text(encoding="utf-8"))
    return {}


def _infer_single_camera_name(dataset_dir: Path, session: dict[str, Any]) -> str:
    cameras = session.get("cameras", [])
    if len(cameras) == 1:
        return cameras[0]["name"]

    color_dirs = [path.parent.name for path in dataset_dir.glob("*/color")]
    if len(color_dirs) == 1:
        return color_dirs[0]
    raise ValueError("Camera name is ambiguous. Please pass --camera-name explicitly.")


def collect_samples(dataset_dir: str | Path, camera_name: str | None = None) -> list[dict[str, Any]]:
    dataset_dir = Path(dataset_dir)
    session = load_session(dataset_dir)

    if camera_name is None:
        camera_name = _infer_single_camera_name(dataset_dir, session)

    pose_dir = dataset_dir / "poses"
    color_dir = dataset_dir / camera_name / "color"
    depth_dir = dataset_dir / camera_name / "depth"

    samples: list[dict[str, Any]] = []

    if pose_dir.exists() and color_dir.exists():
        pose_paths = sorted(pose_dir.glob("*.json"))
        for pose_path in pose_paths:
            sample_id = pose_path.stem
            color_path = color_dir / f"{sample_id}.png"
            if not color_path.exists():
                jpg_path = color_dir / f"{sample_id}.jpg"
                color_path = jpg_path if jpg_path.exists() else color_path
            if not color_path.exists():
                continue
            pose = json.loads(pose_path.read_text(encoding="utf-8"))
            sample = {
                "sample_id": sample_id,
                "pose": pose,
                "color_path": color_path,
                "depth_path": depth_dir / f"{sample_id}.png" if depth_dir.exists() else None,
            }
            samples.append(sample)
        return samples
    return samples


def detect_board_pose(
    image_bgr: np.ndarray,
    board_cfg: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray] | None:
    board_type = str(board_cfg.get("type", "chessboard")).lower()

    if board_type == "chessboard":
        pattern_size = tuple(int(v) for v in board_cfg["pattern_size"])
        square_size = float(board_cfg["square_length_m"])
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        success, corners, _meta = cv2.findChessboardCornersSBWithMeta(gray, pattern_size, flags=0)
        if not success or corners is None:
            return None
        object_points = np.zeros((pattern_size[0] * pattern_size[1], 3), dtype=np.float32)
        object_points[:, :2] = np.mgrid[0 : pattern_size[0], 0 : pattern_size[1]].T.reshape(-1, 2)
        object_points *= square_size
        return object_points, corners.astype(np.float32)

    raise ValueError(f"Unsupported board type: {board_type}")


def _extract_robot_poses(accepted_samples: list[dict[str, Any]]) -> tuple[list[np.ndarray], list[np.ndarray]]:
    r_list = []
    t_list = []
    for sample in accepted_samples:
        pose = sample["pose"]
        quaternion_format = pose.get("quaternion_format", "xyzw")
        position_units = pose.get("position_units", "meters").lower()
        position = np.asarray(pose["position"], dtype=np.float64)
        if position_units in {"millimeters", "mm"}:
            position = position / 1000.0
        orientation_xyzw = ensure_xyzw(pose["orientation"], quaternion_format)
        transform = pose_to_matrix(position, orientation_xyzw)
        r_list.append(transform[:3, :3])
        t_list.append(transform[:3, 3].reshape(3, 1))
    return r_list, t_list


def _detect_and_calibrate_intrinsics(
    samples: list[dict[str, Any]],
    board_cfg: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[np.ndarray], list[np.ndarray], tuple[int, int], float, np.ndarray, np.ndarray, list[np.ndarray], list[np.ndarray]]:
    object_points_list = []
    image_points_list = []
    accepted_samples = []
    image_size = None

    for sample in samples:
        image_bgr = cv2.imread(str(sample["color_path"]), cv2.IMREAD_COLOR)
        if image_bgr is None:
            continue
        detection = detect_board_pose(image_bgr=image_bgr, board_cfg=board_cfg)
        if detection is None:
            continue
        object_points, image_points = detection
        image_size = (image_bgr.shape[1], image_bgr.shape[0])
        object_points_list.append(object_points)
        image_points_list.append(image_points)
        accepted_samples.append(sample)

    if len(accepted_samples) < 3:
        raise RuntimeError(f"Only {len(accepted_samples)} usable calibration samples found.")

    rms, camera_matrix, distortion_coefficients, rvecs, tvecs = cv2.calibrateCamera(
        object_points_list,
        image_points_list,
        image_size,
        None,
        None,
    )

    r_target2cam = [cv2.Rodrigues(rvec)[0] for rvec in rvecs]
    t_target2cam = [np.asarray(tvec, dtype=np.float64).reshape(3, 1) for tvec in tvecs]

    return accepted_samples, object_points_list, image_points_list, image_size, rms, camera_matrix, distortion_coefficients, r_target2cam, t_target2cam


def calibrate_camera_and_handeye(
    dataset_dir: str | Path,
    camera_name: str | None,
    board_cfg: dict[str, Any],
    hand_eye_method: str = "tsai",
    calibration_type: str = "eye_in_hand",
) -> dict[str, Any]:
    session = load_session(dataset_dir)
    effective_camera_name = camera_name
    if effective_camera_name is None:
        cameras = session.get("cameras", [])
        if len(cameras) == 1:
            effective_camera_name = cameras[0]["name"]
        else:
            effective_camera_name = "camera"

    samples = collect_samples(dataset_dir=dataset_dir, camera_name=camera_name)
    if not samples:
        raise RuntimeError(f"No samples found for camera '{effective_camera_name}'.")

    accepted_samples, _obj_pts, _img_pts, image_size, rms, camera_matrix, distortion_coefficients, r_target2cam, t_target2cam = \
        _detect_and_calibrate_intrinsics(samples, board_cfg)

    method_key = hand_eye_method.lower()
    if method_key not in _HAND_EYE_METHODS:
        raise ValueError(f"Unsupported hand-eye method: {hand_eye_method}")

    r_gripper2base, t_gripper2base = _extract_robot_poses(accepted_samples)

    if calibration_type == "eye_in_hand":
        # Wrist-mounted camera: solve for T_camera_to_tool
        r_cam2tool, t_cam2tool = cv2.calibrateHandEye(
            r_gripper2base,
            t_gripper2base,
            r_target2cam,
            t_target2cam,
            method=_HAND_EYE_METHODS[method_key],
        )

        camera_to_tool = np.eye(4, dtype=np.float64)
        camera_to_tool[:3, :3] = r_cam2tool
        camera_to_tool[:3, 3] = t_cam2tool.reshape(3)

        tool_to_camera = invert_transform(camera_to_tool)
        tool_to_camera_position, tool_to_camera_xyzw = matrix_to_pose(tool_to_camera)
        camera_to_tool_position, camera_to_tool_xyzw = matrix_to_pose(camera_to_tool)

        return {
            "camera_name": effective_camera_name,
            "calibration_type": "eye_in_hand",
            "board": board_cfg,
            "image_size": list(image_size),
            "accepted_sample_ids": [s["sample_id"] for s in accepted_samples],
            "num_total_samples": len(samples),
            "num_accepted_samples": len(accepted_samples),
            "reprojection_rms": float(rms),
            "camera_matrix": np.asarray(camera_matrix).tolist(),
            "distortion_coefficients": np.asarray(distortion_coefficients).tolist(),
            "hand_eye_method": method_key,
            "camera_to_tool": {
                "matrix4x4": camera_to_tool.tolist(),
                "translation_m": camera_to_tool_position.tolist(),
                "quaternion_xyzw": camera_to_tool_xyzw.tolist(),
                "quaternion_wxyz": xyzw_to_wxyz(camera_to_tool_xyzw).tolist(),
            },
            "tool_to_camera": {
                "matrix4x4": tool_to_camera.tolist(),
                "translation_m": tool_to_camera_position.tolist(),
                "quaternion_xyzw": tool_to_camera_xyzw.tolist(),
                "quaternion_wxyz": xyzw_to_wxyz(tool_to_camera_xyzw).tolist(),
            },
            "robot_pose_frame_name": accepted_samples[0]["pose"].get("frame_name", "tool"),
        }

    if calibration_type == "eye_to_hand":
        # Fixed camera: board attached to end-effector, solve for T_camera_to_base
        # For eye-to-hand, we invert the robot poses before passing to calibrateHandEye
        r_base2gripper = []
        t_base2gripper = []
        for r, t in zip(r_gripper2base, t_gripper2base):
            inv = invert_transform(np.vstack([np.hstack([r, t]), [0, 0, 0, 1]]))
            r_base2gripper.append(inv[:3, :3])
            t_base2gripper.append(inv[:3, 3].reshape(3, 1))

        r_cam2base, t_cam2base = cv2.calibrateHandEye(
            r_base2gripper,
            t_base2gripper,
            r_target2cam,
            t_target2cam,
            method=_HAND_EYE_METHODS[method_key],
        )

        camera_to_base = np.eye(4, dtype=np.float64)
        camera_to_base[:3, :3] = r_cam2base
        camera_to_base[:3, 3] = t_cam2base.reshape(3)

        base_to_camera = invert_transform(camera_to_base)
        base_to_camera_position, base_to_camera_xyzw = matrix_to_pose(base_to_camera)
        camera_to_base_position, camera_to_base_xyzw = matrix_to_pose(camera_to_base)

        return {
            "camera_name": effective_camera_name,
            "calibration_type": "eye_to_hand",
            "board": board_cfg,
            "image_size": list(image_size),
            "accepted_sample_ids": [s["sample_id"] for s in accepted_samples],
            "num_total_samples": len(samples),
            "num_accepted_samples": len(accepted_samples),
            "reprojection_rms": float(rms),
            "camera_matrix": np.asarray(camera_matrix).tolist(),
            "distortion_coefficients": np.asarray(distortion_coefficients).tolist(),
            "hand_eye_method": method_key,
            "camera_to_base": {
                "matrix4x4": camera_to_base.tolist(),
                "translation_m": camera_to_base_position.tolist(),
                "quaternion_xyzw": camera_to_base_xyzw.tolist(),
                "quaternion_wxyz": xyzw_to_wxyz(camera_to_base_xyzw).tolist(),
            },
            "base_to_camera": {
                "matrix4x4": base_to_camera.tolist(),
                "translation_m": base_to_camera_position.tolist(),
                "quaternion_xyzw": base_to_camera_xyzw.tolist(),
                "quaternion_wxyz": xyzw_to_wxyz(base_to_camera_xyzw).tolist(),
            },
            "robot_pose_frame_name": accepted_samples[0]["pose"].get("frame_name", "tool"),
        }

    raise ValueError(f"Unsupported calibration_type: {calibration_type}. Use 'eye_in_hand' or 'eye_to_hand'.")


def save_calibration_result(dataset_dir: str | Path, result: dict[str, Any], output_path: str | Path | None = None) -> Path:
    dataset_dir = Path(dataset_dir)
    if output_path is None:
        output_dir = dataset_dir / "calibration"
        output_dir.mkdir(parents=True, exist_ok=True)
        cal_type = result.get("calibration_type", "eye_in_hand")
        suffix = "handeye" if cal_type == "eye_in_hand" else "eye_to_hand"
        output_path = output_dir / f"{result['camera_name']}_{suffix}.json"
    else:
        output_path = Path(output_path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return output_path
