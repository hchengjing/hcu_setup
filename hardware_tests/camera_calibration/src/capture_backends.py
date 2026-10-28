#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from scipy.spatial.transform import Rotation as R

from pose_utils import PoseRecord, ensure_xyzw


def _ensure_resolved_string(value: Any, field_name: str) -> Any:
    if isinstance(value, str) and "${" in value:
        raise ValueError(f"Configuration value '{field_name}' still contains an unresolved environment variable: {value}")
    return value


@dataclass
class CameraCapture:
    color_bgr: np.ndarray
    depth: np.ndarray | None
    metadata: dict[str, Any]


class CameraBackend:
    backend_name = "camera"

    def __init__(self, name: str):
        self.name = name

    def capture(self) -> CameraCapture:
        raise NotImplementedError

    def close(self) -> None:
        return None


class RobotBackend:
    backend_name = "robot"

    def __init__(self, frame_name: str):
        self.frame_name = frame_name

    def get_pose(self) -> PoseRecord:
        raise NotImplementedError

    def close(self) -> None:
        return None


class URRTDERobotBackend(RobotBackend):
    backend_name = "ur_rtde"

    def __init__(self, frame_name: str, options: dict[str, Any]):
        super().__init__(frame_name=frame_name)
        try:
            from rtde_receive import RTDEReceiveInterface
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "ur-rtde is not installed. Run 'uv sync --extra hardware' to enable the local UR backend."
            ) from exc

        robot_ip = options.get("robot_ip") or os.environ.get("UR_ROBOT_IP") or os.environ.get(
            "UNIVERSAL_ROBOTS_ROBOT_IP_ADDRESS"
        )
        robot_ip = _ensure_resolved_string(robot_ip, "robot.options.robot_ip")
        if not robot_ip:
            raise ValueError("No UR robot IP was provided. Set UR_ROBOT_IP in .env or robot.options.robot_ip.")

        frequency = options.get("frequency")
        if frequency is None:
            self.receiver = RTDEReceiveInterface(robot_ip)
        else:
            self.receiver = RTDEReceiveInterface(robot_ip, float(frequency))
        self.robot_ip = robot_ip

    def get_pose(self) -> PoseRecord:
        tcp_pose = np.asarray(self.receiver.getActualTCPPose(), dtype=np.float64)
        if tcp_pose.shape != (6,):
            raise RuntimeError(f"Unexpected UR TCP pose shape: {tcp_pose.shape}")
        position = tcp_pose[:3]
        orientation = R.from_rotvec(tcp_pose[3:]).as_quat()
        return PoseRecord(
            position_m=position,
            orientation_xyzw=orientation,
            frame_name=self.frame_name,
            source=self.backend_name,
            metadata={
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "robot_ip": self.robot_ip,
                "ur_pose_representation": "tcp_pose_xyz_rotvec",
            },
        )

    def close(self) -> None:
        disconnect = getattr(self.receiver, "disconnect", None)
        if callable(disconnect):
            disconnect()


class ABBRwsRobotBackend(RobotBackend):
    backend_name = "abb_rws"

    def __init__(self, frame_name: str, options: dict[str, Any]):
        super().__init__(frame_name=frame_name)
        try:
            from abb_robot_client.rws import RWS
        except ImportError as exc:  # pragma: no cover - import depends on optional extra
            raise RuntimeError(
                "abb-robot-client is not installed. Run 'uv sync --extra hardware' to enable the ABB RWS backend."
            ) from exc

        base_url = _ensure_resolved_string(options["base_url"], "robot.options.base_url")
        username = _ensure_resolved_string(options.get("username", "Default User"), "robot.options.username")
        password = _ensure_resolved_string(options.get("password", "robotics"), "robot.options.password")
        self.mechunit = options.get("mechunit", "ROB_1")
        self.tool = options.get("tool", "tool0")
        self.wobj = options.get("wobj", "wobj0")
        self.request_timeout_s = float(options.get("request_timeout_s", 5.0))
        self.rws = RWS(base_url=base_url, username=username, password=password)
        auth_type = str(options.get("auth", "basic")).strip().lower()
        self.auth_type = auth_type
        if auth_type == "basic":
            import requests

            self.rws.auth = requests.auth.HTTPBasicAuth(username, password)
            self.rws._session.headers.update(
                {
                    "Accept": "application/hal+json;v=2.0",
                    "Content-Type": "application/x-www-form-urlencoded;v=2.0",
                }
            )
        elif auth_type != "digest":
            raise ValueError("Unsupported ABB RWS auth type. Use 'basic' or 'digest'.")

        verify_ssl = options.get("verify_ssl", False)
        if isinstance(verify_ssl, str):
            verify_ssl = verify_ssl.strip().lower() not in {"0", "false", "no", "off"}
        verify_ssl = bool(verify_ssl)
        self.rws._session.verify = verify_ssl
        if not verify_ssl:
            try:
                import urllib3

                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except Exception:
                pass

    def get_pose(self) -> PoseRecord:
        if self.auth_type == "basic":
            state = self._get_robtarget_state_basic()
            position_m = np.asarray([state["x"], state["y"], state["z"]], dtype=np.float64) / 1000.0
            orientation_xyzw = ensure_xyzw([state["q1"], state["q2"], state["q3"], state["q4"]], "wxyz")
        else:
            robtarget = self.rws.get_robtarget(mechunit=self.mechunit, tool=self.tool, wobj=self.wobj)
            position_m = np.asarray(robtarget.trans, dtype=np.float64) / 1000.0
            orientation_xyzw = ensure_xyzw(robtarget.rot, "wxyz")
        return PoseRecord(
            position_m=position_m,
            orientation_xyzw=orientation_xyzw,
            frame_name=self.frame_name,
            source=self.backend_name,
            metadata={
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "mechunit": self.mechunit,
                "tool": self.tool,
                "wobj": self.wobj,
                "abb_rotation_format": "wxyz",
                "abb_translation_units": "millimeters",
            },
        )

    def _get_robtarget_state_basic(self) -> dict[str, float]:
        url = (
            f"{self.rws.base_url}/rw/motionsystem/mechunits/{self.mechunit}/robtarget"
            f"?tool={self.tool}&wobj={self.wobj}&coordinate=Base&json=1"
        )
        response = self.rws._session.get(url, auth=self.rws.auth, timeout=self.request_timeout_s)
        response.raise_for_status()
        payload = response.json()

        embedded = payload.get("_embedded", {})
        state_entries = payload.get("state") or embedded.get("_state") or embedded.get("state")
        if not state_entries:
            raise RuntimeError("ABB RWS response did not contain robtarget state.")

        state = state_entries[0]
        return {
            "x": float(state["x"]),
            "y": float(state["y"]),
            "z": float(state["z"]),
            "q1": float(state["q1"]),
            "q2": float(state["q2"]),
            "q3": float(state["q3"]),
            "q4": float(state["q4"]),
        }


class CommandRobotBackend(RobotBackend):
    backend_name = "command"

    def __init__(self, frame_name: str, options: dict[str, Any]):
        super().__init__(frame_name=frame_name)
        self.command = _ensure_resolved_string(options["command"], "robot.options.command")
        self.timeout_s = float(options.get("timeout_s", 5.0))
        self.position_units = options.get("position_units", "meters")
        self.quaternion_format = options.get("quaternion_format", "xyzw")
        self.cwd = options.get("cwd")

    def get_pose(self) -> PoseRecord:
        completed = subprocess.run(
            self.command,
            shell=isinstance(self.command, str),
            capture_output=True,
            text=True,
            timeout=self.timeout_s,
            cwd=self.cwd,
            check=True,
        )
        payload = json.loads(completed.stdout)
        position = np.asarray(payload["position"], dtype=np.float64)
        if self.position_units.lower() in {"millimeters", "mm"}:
            position = position / 1000.0
        orientation_xyzw = ensure_xyzw(payload["orientation"], self.quaternion_format)
        metadata = payload.get("metadata", {})
        metadata["timestamp_utc"] = datetime.now(UTC).isoformat()
        return PoseRecord(
            position_m=position,
            orientation_xyzw=orientation_xyzw,
            frame_name=payload.get("frame_name", self.frame_name),
            source=self.backend_name,
            metadata=metadata,
        )


class LocalRealSenseCameraBackend(CameraBackend):
    backend_name = "realsense_local"

    def __init__(self, name: str, options: dict[str, Any], save_depth: bool):
        super().__init__(name=name)
        try:
            import pyrealsense2 as rs
        except ImportError as exc:  # pragma: no cover - import depends on optional extra
            raise RuntimeError(
                "pyrealsense2 is not installed. Run 'uv sync --extra hardware' to enable the local RealSense backend."
            ) from exc

        self.rs = rs
        self.save_depth = save_depth
        self.width = int(options.get("width", 1280))
        self.height = int(options.get("height", 720))
        self.fps = int(options.get("fps", 15))
        self.exposure = options.get("exposure")
        self.align_to_color = bool(options.get("align_to_color", True))
        color_format_name = str(options.get("color_format", "bgr8")).lower()
        requested_color_format, requested_is_rgb = self._resolve_color_format(color_format_name)

        serial = _ensure_resolved_string(options.get("serial"), "camera.options.serial")
        self.color_is_rgb = requested_is_rgb
        try:
            self.profile, self.align = self._start_pipeline(serial=serial, color_format=requested_color_format)
        except RuntimeError as exc:
            if requested_color_format == rs.format.bgr8:
                print(
                    f"[warn] Camera '{self.name}' failed to start with color format bgr8; "
                    "retrying with rgb8."
                )
                self.color_is_rgb = True
                self.profile, self.align = self._start_pipeline(serial=serial, color_format=rs.format.rgb8)
            else:
                raise exc

        if self.exposure is not None:
            # Some devices (for example D405) may not expose an RGB sensor object.
            # In that case, keep device defaults instead of forcing exposure on a non-RGB sensor.
            sensor = self._select_exposure_sensor()
            if sensor is None:
                print(
                    f"[warn] Camera '{self.name}' does not expose an RGB sensor with manual exposure control; "
                    "skipping exposure setting."
                )
            else:
                if sensor.supports(rs.option.enable_auto_exposure):
                    sensor.set_option(rs.option.enable_auto_exposure, 0)
                sensor.set_option(rs.option.exposure, float(self.exposure))

        for _ in range(10):
            self.pipeline.wait_for_frames()

    def capture(self) -> CameraCapture:
        frames = self.pipeline.wait_for_frames()
        if self.align is not None:
            frames = self.align.process(frames)
        color_frame = frames.get_color_frame()
        if not color_frame:
            raise RuntimeError("Failed to read a color frame from the local RealSense camera.")
        color_raw = np.asanyarray(color_frame.get_data())
        color_bgr = cv2.cvtColor(color_raw, cv2.COLOR_RGB2BGR) if self.color_is_rgb else color_raw
        depth = None
        if self.save_depth:
            depth_frame = frames.get_depth_frame()
            if not depth_frame:
                raise RuntimeError("Failed to read a depth frame from the local RealSense camera.")
            depth = np.asanyarray(depth_frame.get_data())
        return CameraCapture(
            color_bgr=color_bgr,
            depth=depth,
            metadata={"timestamp_utc": datetime.now(UTC).isoformat()},
        )

    def close(self) -> None:
        self.pipeline.stop()

    def _select_exposure_sensor(self):
        try:
            sensor = self.profile.get_device().first_color_sensor()
            if sensor.supports(self.rs.option.exposure):
                return sensor
        except RuntimeError:
            pass

        # D405 may expose color stream under Stereo Module only.
        for sensor in self.profile.get_device().query_sensors():
            try:
                if sensor.supports(self.rs.option.exposure):
                    return sensor
            except Exception:
                continue
        return None

    def _resolve_color_format(self, color_format_name: str):
        if color_format_name == "bgr8":
            return self.rs.format.bgr8, False
        if color_format_name == "rgb8":
            return self.rs.format.rgb8, True
        raise ValueError(f"Unsupported RealSense color format: {color_format_name}. Use 'bgr8' or 'rgb8'.")

    def _start_pipeline(self, serial: str | None, color_format):
        self.pipeline = self.rs.pipeline()
        config = self.rs.config()
        if serial:
            config.enable_device(str(serial))
        config.enable_stream(self.rs.stream.color, self.width, self.height, color_format, self.fps)
        if self.save_depth:
            config.enable_stream(self.rs.stream.depth, self.width, self.height, self.rs.format.z16, self.fps)

        profile = self.pipeline.start(config)
        align = self.rs.align(self.rs.stream.color) if self.save_depth and self.align_to_color else None
        for _ in range(10):
            self.pipeline.wait_for_frames()
        return profile, align


class OpenCVCameraBackend(CameraBackend):
    backend_name = "opencv_uvc"

    def __init__(self, name: str, options: dict[str, Any], save_depth: bool):
        super().__init__(name=name)
        if save_depth:
            raise ValueError("The OpenCV UVC backend does not support depth capture.")

        device = _ensure_resolved_string(options.get("device", 0), "camera.options.device")
        if isinstance(device, str) and device.isdigit():
            device = int(device)
        self.device = device

        self.backend_name = str(options.get("capture_backend", "CAP_V4L2"))
        backend = getattr(cv2, self.backend_name, cv2.CAP_ANY)
        self.cap = cv2.VideoCapture(device, backend)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera device '{device}' with backend {self.backend_name}.")

        self.width = options.get("width")
        self.height = options.get("height")
        self.fps = options.get("fps")
        self.fourcc = str(options.get("fourcc")) if options.get("fourcc") else None
        self.read_retries = int(options.get("read_retries", 3))
        self.read_retry_sleep_s = float(options.get("read_retry_sleep_s", 0.02))

        self._apply_capture_settings(self.fourcc)

        warmup_frames = int(options.get("warmup_frames", 5))
        if not self._warmup(warmup_frames):
            if self.fourcc and self.fourcc.upper() == "MJPG":
                print(
                    f"[warn] Camera '{self.name}' failed warmup with MJPG; retrying with YUYV."
                )
                self._reopen_capture()
                self.fourcc = "YUYV"
                self._apply_capture_settings(self.fourcc)
                if not self._warmup(warmup_frames):
                    raise RuntimeError(
                        f"Failed to read stable warmup frames from camera '{self.name}' "
                        f"using both MJPG and YUYV."
                    )
            else:
                raise RuntimeError(f"Failed to read stable warmup frames from camera '{self.name}'.")

    def capture(self) -> CameraCapture:
        success, frame = self._safe_read_frame()
        if not success:
            raise RuntimeError(f"Failed to capture a frame from camera '{self.name}'.")
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        return CameraCapture(
            color_bgr=frame,
            depth=None,
            metadata={"timestamp_utc": datetime.now(UTC).isoformat()},
        )

    def close(self) -> None:
        self.cap.release()

    def _apply_capture_settings(self, fourcc: str | None) -> None:
        if self.width is not None:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(self.width))
        if self.height is not None:
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(self.height))
        if self.fps is not None:
            self.cap.set(cv2.CAP_PROP_FPS, int(self.fps))
        if fourcc:
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*str(fourcc)))

    def _reopen_capture(self) -> None:
        backend = getattr(cv2, self.backend_name, cv2.CAP_ANY)
        self.cap.release()
        self.cap = cv2.VideoCapture(self.device, backend)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to reopen camera device '{self.device}' with backend {self.backend_name}.")

    def _safe_read_frame(self) -> tuple[bool, np.ndarray | None]:
        for _ in range(max(1, self.read_retries)):
            try:
                success, frame = self.cap.read()
                if success and frame is not None:
                    return True, frame
            except cv2.error:
                pass
            time.sleep(self.read_retry_sleep_s)
        return False, None

    def _warmup(self, warmup_frames: int) -> bool:
        for _ in range(warmup_frames):
            success, _frame = self._safe_read_frame()
            if not success:
                return False
            time.sleep(0.02)
        return True


def create_robot_backend(robot_cfg: dict[str, Any]) -> RobotBackend:
    backend = robot_cfg["backend"]
    options = robot_cfg.get("options", {})
    frame_name = robot_cfg.get("frame_name", "tool")

    if backend == "ur_rtde":
        return URRTDERobotBackend(frame_name=frame_name, options=options)
    if backend == "abb_rws":
        return ABBRwsRobotBackend(frame_name=frame_name, options=options)
    if backend == "command":
        return CommandRobotBackend(frame_name=frame_name, options=options)

    raise ValueError(f"Unsupported robot backend: {backend}")


class AzureKinectCameraBackend(CameraBackend):
    backend_name = "azure_kinect"

    def __init__(self, name: str, options: dict[str, Any], save_depth: bool):
        super().__init__(name=name)
        try:
            import pyk4a
            from pyk4a import Config, PyK4A
        except ImportError as exc:
            raise RuntimeError(
                "pyk4a is not installed. Run 'uv sync --extra hardware' to enable the Azure Kinect backend."
            ) from exc

        self.pyk4a = pyk4a
        self.save_depth = save_depth

        color_resolution_name = options.get("color_resolution", "RES_1080P")
        depth_mode_name = options.get("depth_mode", "NFOV_UNBINNED")
        fps_name = options.get("fps", "FPS_15")

        color_resolution = getattr(pyk4a.ColorResolution, color_resolution_name, pyk4a.ColorResolution.RES_1080P)
        depth_mode = getattr(pyk4a.DepthMode, depth_mode_name, pyk4a.DepthMode.NFOV_UNBINNED)
        camera_fps = getattr(pyk4a.FPS, fps_name, pyk4a.FPS.FPS_15)

        device_id = int(options.get("device_id", 0))
        self.k4a = PyK4A(
            Config(
                color_resolution=color_resolution,
                depth_mode=depth_mode if save_depth else pyk4a.DepthMode.OFF,
                camera_fps=camera_fps,
                synchronized_images_only=save_depth,
            ),
            device_id=device_id,
        )
        self.k4a.start()

        for _ in range(10):
            self.k4a.get_capture()

    def capture(self) -> CameraCapture:
        cap = self.k4a.get_capture()
        color_bgra = cap.color
        if color_bgra is None:
            raise RuntimeError("Failed to read a color frame from Azure Kinect.")
        color_bgr = color_bgra[:, :, :3]
        depth = None
        if self.save_depth:
            depth = cap.transformed_depth
            if depth is None:
                depth = cap.depth
        return CameraCapture(
            color_bgr=color_bgr,
            depth=depth,
            metadata={"timestamp_utc": datetime.now(UTC).isoformat()},
        )

    def close(self) -> None:
        self.k4a.stop()


def create_camera_backend(camera_cfg: dict[str, Any]) -> CameraBackend:
    backend = camera_cfg["backend"]
    name = camera_cfg["name"]
    options = camera_cfg.get("options", {})
    save_depth = bool(camera_cfg.get("save_depth", False))

    if backend == "realsense_local":
        return LocalRealSenseCameraBackend(name=name, options=options, save_depth=save_depth)
    if backend == "opencv_uvc":
        return OpenCVCameraBackend(name=name, options=options, save_depth=save_depth)
    if backend == "azure_kinect":
        return AzureKinectCameraBackend(name=name, options=options, save_depth=save_depth)

    raise ValueError(f"Unsupported camera backend: {backend}")
