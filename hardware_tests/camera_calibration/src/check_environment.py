#!/usr/bin/env python3

import argparse
import importlib
import platform
import sys
from importlib import metadata


CORE_IMPORTS = [
    ("numpy", "numpy"),
    ("scipy", "scipy"),
    ("yaml", "pyyaml"),
]

HARDWARE_IMPORTS = [
    ("abb_robot_client", "abb-robot-client"),
    ("pyk4a", "pyk4a"),
    ("pyrealsense2", "pyrealsense2"),
    ("rtde_receive", "ur-rtde"),
]

HARDWARE_PROFILES = {
    "abb": [
        ("abb_robot_client", "abb-robot-client"),
        ("pyrealsense2", "pyrealsense2"),
    ],
    "ur": [
        ("pyrealsense2", "pyrealsense2"),
        ("rtde_receive", "ur-rtde"),
    ],
    "ur-azure": [
        ("pyk4a", "pyk4a"),
        ("pyrealsense2", "pyrealsense2"),
        ("rtde_receive", "ur-rtde"),
    ],
}


def get_distribution_version(distribution_name):
    try:
        return metadata.version(distribution_name)
    except metadata.PackageNotFoundError:
        return None


def import_and_report(module_name, distribution_name):
    try:
        importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - diagnostic path
        print(f"[missing] {distribution_name}: {exc}")
        return False

    version = get_distribution_version(distribution_name) or "unknown"
    print(f"[ok] {distribution_name} {version}")
    return True


def check_import_group(imports):
    results = {}
    for module_name, distribution_name in imports:
        results[distribution_name] = import_and_report(module_name, distribution_name)
    return results


def check_opencv():
    try:
        cv2 = importlib.import_module("cv2")
    except Exception as exc:  # pragma: no cover - diagnostic path
        print(f"[missing] opencv: {exc}")
        return False

    version = getattr(cv2, "__version__", "unknown")
    print(f"[ok] opencv {version}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Validate the calibration Python environment.")
    parser.add_argument(
        "--require-hardware",
        action="store_true",
        help="Fail if optional hardware backends such as ABB RWS and local RealSense are missing.",
    )
    parser.add_argument(
        "--require-profile",
        choices=sorted(HARDWARE_PROFILES),
        help="Fail if the dependencies required for a specific workstation profile are missing.",
    )
    args = parser.parse_args()

    print(f"Python {platform.python_version()} ({sys.executable})")
    print(f"Platform: {platform.platform()}")

    ok = check_opencv()

    for module_name, distribution_name in CORE_IMPORTS:
        ok = import_and_report(module_name, distribution_name) and ok

    if args.require_profile:
        profile_results = check_import_group(HARDWARE_PROFILES[args.require_profile])
        ok = ok and all(profile_results.values())
    else:
        hardware_results = check_import_group(HARDWARE_IMPORTS)
        hardware_ok = all(hardware_results.values())

        if args.require_hardware:
            ok = hardware_ok and ok
        elif not hardware_ok:
            print("[note] Hardware backends are optional. Install only what your workstation needs.")
            print("[note] ABB GoFa: uv sync --extra abb --extra realsense")
            print("[note] UR5e + D405: uv sync --extra ur --extra realsense")
            print("[note] UR5e + Azure Kinect: install libk4a first, then run uv sync --extra ur --extra realsense --extra azure-kinect")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
