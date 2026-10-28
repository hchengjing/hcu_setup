#!/usr/bin/env python3

from __future__ import annotations

import argparse
import math
import os
import time
from pathlib import Path

import cv2
import numpy as np

from capture_backends import create_camera_backend, create_robot_backend
from config_utils import load_config
from dataset_io import ensure_session_layout, next_capture_index, save_capture, write_session_file


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect calibration images and robot poses.")
    parser.add_argument(
        "--config",
        default="configs/abb_gofa_d405.yaml",
        help="Path to a YAML configuration file.",
    )
    parser.add_argument(
        "--dataset-dir",
        default=None,
        help="Override the dataset output directory from the configuration file.",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Override the sample count from the configuration file.",
    )
    return parser


def _to_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off"}
    return bool(value)


def _can_use_preview() -> bool:
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return False
    try:
        cv2.namedWindow("__preview_test__", cv2.WINDOW_NORMAL)
        cv2.destroyWindow("__preview_test__")
    except cv2.error:
        return False
    return True


def _as_bgr_uint8(frame: np.ndarray) -> np.ndarray:
    if frame.ndim == 2:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    if frame.dtype == np.uint8:
        return frame
    if frame.dtype == np.uint16:
        frame = np.clip(frame / 256.0, 0, 255).astype(np.uint8)
        return frame
    return np.clip(frame, 0, 255).astype(np.uint8)


def _build_preview_mosaic(camera_captures: dict[str, object], capture_index: int, max_samples: int) -> np.ndarray:
    tile_w = 640
    tile_h = 360
    cols = 1 if len(camera_captures) <= 1 else 2
    rows = max(1, math.ceil(len(camera_captures) / cols))

    canvas = np.zeros((rows * tile_h, cols * tile_w, 3), dtype=np.uint8)

    for idx, (name, capture) in enumerate(camera_captures.items()):
        frame = _as_bgr_uint8(capture.color_bgr)
        src_h, src_w = frame.shape[:2]
        scale = min(tile_w / max(src_w, 1), tile_h / max(src_h, 1))
        resized = cv2.resize(frame, (max(1, int(src_w * scale)), max(1, int(src_h * scale))), interpolation=cv2.INTER_AREA)

        row = idx // cols
        col = idx % cols
        y0 = row * tile_h + (tile_h - resized.shape[0]) // 2
        x0 = col * tile_w + (tile_w - resized.shape[1]) // 2
        canvas[y0 : y0 + resized.shape[0], x0 : x0 + resized.shape[1]] = resized

        label_y = max(row * tile_h + 24, 24)
        label_x = col * tile_w + 12
        cv2.putText(canvas, name, (label_x, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)

    status = f"[{capture_index:04d}/{max_samples:04d}] y/space: capture, q/esc: quit"
    cv2.putText(canvas, status, (12, canvas.shape[0] - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 255, 80), 2, cv2.LINE_AA)
    return canvas


def _run_preview_loop(cameras, robot, dataset_dir: Path, config: dict, capture_index: int, max_samples: int, wait_after_prompt_s: float) -> int:
    window_name = "Calibration Preview"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1400, 900)
    print("Preview controls: press 'y' or space to capture, 'q' or ESC to quit.")

    while capture_index < max_samples:
        camera_captures = {camera.name: camera.capture() for camera in cameras}
        preview = _build_preview_mosaic(camera_captures, capture_index, max_samples)
        cv2.imshow(window_name, preview)
        key = cv2.waitKey(1) & 0xFF

        if key in (ord("q"), 27):  # q or ESC
            break
        if key not in (ord("y"), ord(" "), 13):
            continue

        if wait_after_prompt_s > 0.0:
            time.sleep(wait_after_prompt_s)

        camera_captures = {camera.name: camera.capture() for camera in cameras}
        pose = robot.get_pose()
        save_capture(dataset_dir, capture_index, pose, camera_captures, config)
        print(f"Saved sample {capture_index:04d}")
        capture_index += 1

    cv2.destroyWindow(window_name)
    return capture_index


def main() -> int:
    args = build_arg_parser().parse_args()
    config = load_config(args.config)

    if args.dataset_dir is not None:
        config["dataset"]["path"] = str(Path(args.dataset_dir).expanduser().resolve())
    if args.max_samples is not None:
        config["capture"]["max_samples"] = args.max_samples

    dataset_dir = ensure_session_layout(config["dataset"]["path"], config)
    write_session_file(dataset_dir, config)

    robot = create_robot_backend(config["robot"])
    cameras = [create_camera_backend(camera_cfg) for camera_cfg in config["cameras"]]

    capture_index = next_capture_index(dataset_dir)
    max_samples = int(config["capture"]["max_samples"])
    wait_after_prompt_s = float(config["capture"].get("wait_after_prompt_s", 0.0))
    preview_enabled = _to_bool(config["capture"].get("show_preview"), default=True)

    print(f"Dataset directory: {dataset_dir}")
    print(f"Starting capture index: {capture_index:04d}")
    print(f"Configured cameras: {', '.join(camera.name for camera in cameras)}")
    print(f"Robot backend: {config['robot']['backend']}")

    try:
        if preview_enabled and _can_use_preview():
            capture_index = _run_preview_loop(
                cameras=cameras,
                robot=robot,
                dataset_dir=dataset_dir,
                config=config,
                capture_index=capture_index,
                max_samples=max_samples,
                wait_after_prompt_s=wait_after_prompt_s,
            )
        else:
            if preview_enabled:
                print("[note] Preview requested but no GUI display is available. Falling back to terminal prompts.")
            print("Press 'y' to capture. Type 'q' to quit.")
            while capture_index < max_samples:
                command = input(f"[{capture_index:04d}/{max_samples:04d}] Capture sample? (y/q) ").strip().lower()
                if command == "q":
                    break
                if command != "y":
                    print("Skipped.")
                    continue

                if wait_after_prompt_s > 0.0:
                    time.sleep(wait_after_prompt_s)

                camera_captures = {camera.name: camera.capture() for camera in cameras}
                pose = robot.get_pose()
                save_capture(dataset_dir, capture_index, pose, camera_captures, config)
                print(f"Saved sample {capture_index:04d}")
                capture_index += 1
    finally:
        try:
            cv2.destroyAllWindows()
        except cv2.error:
            pass
        robot.close()
        for camera in cameras:
            camera.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
