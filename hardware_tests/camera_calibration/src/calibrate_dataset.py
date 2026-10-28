#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from calibration_core import calibrate_camera_and_handeye, load_session, save_calibration_result
from config_utils import load_config


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run camera intrinsics and hand-eye calibration on a dataset.")
    parser.add_argument("--dataset-dir", required=True, help="Dataset directory created by collect_calibration_data.py")
    parser.add_argument("--camera-name", default=None, help="Camera name to calibrate. Optional for single-camera datasets.")
    parser.add_argument("--config", default=None, help="Optional YAML config file. Board settings are loaded from here when provided.")
    parser.add_argument("--output-path", default=None, help="Optional output path for the calibration JSON.")
    parser.add_argument(
        "--hand-eye-method",
        default="tsai",
        choices=["tsai", "park", "horaud", "andreff", "daniilidis"],
        help="OpenCV hand-eye method.",
    )
    parser.add_argument(
        "--calibration-type",
        default="eye_in_hand",
        choices=["eye_in_hand", "eye_to_hand"],
        help="eye_in_hand for wrist-mounted cameras, eye_to_hand for fixed cameras.",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    dataset_dir = Path(args.dataset_dir).expanduser().resolve()

    calibration_type = args.calibration_type
    inferred_camera_name = args.camera_name

    if args.config is not None:
        loaded_config = load_config(args.config)
        board_cfg = loaded_config["board"]
        if inferred_camera_name is None and len(loaded_config["cameras"]) == 1:
            inferred_camera_name = loaded_config["cameras"][0]["name"]
        # Auto-detect calibration_type from config if not explicitly overridden
        if inferred_camera_name is not None and calibration_type == "eye_in_hand":
            for cam_cfg in loaded_config["cameras"]:
                if cam_cfg["name"] == inferred_camera_name:
                    calibration_type = cam_cfg.get("calibration_type", "eye_in_hand")
                    break
    else:
        session = load_session(dataset_dir)
        board_cfg = session.get("config", {}).get("board")
        if board_cfg is None:
            raise RuntimeError("No board configuration found in session.json. Pass --config explicitly.")
        # Auto-detect calibration_type from session
        if inferred_camera_name is not None and calibration_type == "eye_in_hand":
            for cam_cfg in session.get("config", {}).get("cameras", []):
                if cam_cfg["name"] == inferred_camera_name:
                    calibration_type = cam_cfg.get("calibration_type", "eye_in_hand")
                    break

    result = calibrate_camera_and_handeye(
        dataset_dir=dataset_dir,
        camera_name=inferred_camera_name,
        board_cfg=board_cfg,
        hand_eye_method=args.hand_eye_method,
        calibration_type=calibration_type,
    )
    output_path = save_calibration_result(dataset_dir, result, output_path=args.output_path)

    print(f"Calibration type: {calibration_type}")
    print(json.dumps(result, indent=2))
    print(f"Saved calibration result to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
