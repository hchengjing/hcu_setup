# FYP to-do

Updated: 28 October 2026 (Singapore time).

## Long-term plan: battery power and electrical system

Added 28 October 2026 at the user's request. This is a future design task; no power architecture or components have been selected.

- [ ] Design a battery-powered electrical system for the complete HCU setup: HCU/ASUS NUC, Inspire gripper (24 V, user specified), Hikrobot camera, Livox LiDAR, and synchronizer.
- [ ] Inventory each device's actual input voltage range, connector/polarity, normal and peak/startup current, and power/data interface. Verify the camera's USB power path and the exact HCU/NUC supply requirements rather than assuming all devices use the same voltage.
- [ ] Define target operating time, portability/weight, and measured total power budget, including conversion losses and peak loads.
- [ ] Develop the battery and power-distribution architecture: battery/BMS/charger, required regulated rails and DC-DC converters, branch protection, wiring/connectors, grounding/noise control, and power switching/shutdown behavior.
- [ ] Produce a wiring/block diagram, component shortlist/BOM, and staged validation plan for simultaneous operation, gripper load transients, runtime, temperatures, and low-battery shutdown.

Completion target: a documented and tested portable battery system that powers all five subsystems reliably. Keep this separate from the immediate software/NUC migration tasks.

## NUC integration priorities

- [ ] Preserve/refine the inspected existing ROS node: `/gripper/command` Int32 -> register 10 (clamped 0–1000); register 61 -> `/gripper/position` Int32 at a target 10 Hz. Confirm the final `main()` call because the pasted source ended at its guard. Parameterize hardcoded serial settings, pin the PyModbus API (`slave=`), serialize callback/polling Modbus access, add exception-safe cleanup, and define timestamped feedback for recordings. Do not replace this existing wrapper with a duplicate. No new runtime test is established by this code inspection.

- [ ] Review `inspire_gripper/scripts/gripper_node.py` before refactoring: actual imports, commands, feedback, register handling, serial parameters, and startup/shutdown behavior are not yet inspected. The existing CMake has no active `catkin_install_python` rule; add portable script installation when preparing the clean package. Resolve placeholder license/maintainer metadata and declare actual runtime dependencies after reading the node. No launch/config files were shown in the package listing.

- [ ] Inspect and reuse the existing `~/catkin_ws/src/inspire_gripper` ROS package (confirmed by user output on 28 October). Determine its nodes, interfaces, dependencies, and tested behavior before proposing a new gripper wrapper. No nested Git metadata was found in this workspace source. The top-level Catkin CMakeLists.txt is a system symlink and should be regenerated on the NUC rather than copied as custom source.

- [ ] Inspect the user-confirmed `~/catkin_ws/src` and reconcile its packages with `~/fyp/UMI-3D/umi_3d_slam_ws/src` before assembling the clean `hcu_setup`. Custom peripheral tests are at `C:\Users\haoch\Projects\fyp_tests`. Include required source/configuration and licenses; exclude generated build/devel files. Neither workspace should be deleted during assembly.

Target confirmed: native Ubuntu 20.04 + ROS Noetic; source currently on laptop. Full source audit and acceptance criteria: `NUC_Three_Device_Integration_Audit.md` alongside this file.

1. [ ] Port/rebuild the working CustomMsg LiDAR setup on NUC; parameterize host networking/startup, then repeat the known-good capture/mapping tests. Do not rewrite the Livox driver or carry WSL firewall/config steps onto native Ubuntu.
2. [ ] Build a continuous Hikrobot RGB acquisition library and thin ROS Image/CameraInfo node from `C:\Users\haoch\Projects\fyp_tests\camera_test.py`. It currently captures one frame only. Validate pixel conversion, owned buffers, timestamps, lens model/intrinsics and rig extrinsics before changing `img_en` from 0. Separate Python 3.12 calibration tooling from Noetic runtime.
3. [ ] Refactor the Inspire gripper class/test into reusable hardware API, explicit CLI tests and ROS command/measured-state interfaces. Existing UMI WSG/UVC scripts are not drivers for this hardware. Define the gripper dataset adapter explicitly.

- [ ] Add common NUC bringup/configuration, stable USB device selection, timestamp policy and a combined recording test for all three devices.

## Gripper: modular Python driver and ROS Noetic interface

- [ ] Rewrite/refactor the existing gripper scripts into a reusable Python hardware driver, a separate manual test script, and a thin ROS Noetic node. This is a planned task; no gripper code was changed or executed during this inspection.

### Located source files

Actual Windows folder: `C:\Users\haoch\Projects\fyp_tests` (the requested `Projects/fyp` folder was not found).

- `gripper_ros_test.py`: Linux serial Modbus movement test using `/dev/ttyUSB0`, 115200 baud, slave ID 1. Writes register 10 with 1000, 500, then 0, with two-second pauses. Uses the `slave=` keyword. Despite its name, contains no rospy initialization, publishers, subscribers, services, or ROS connection verification. It opens the serial connection and runs movement commands at module top level.
- `test_gripper.py`: contains an `InspireGripper` class and a long hardware exercise at module top level. Uses Windows `COM10`, 115200 baud, ID 1, and `device_id=`. Covers position/width, speed, force, status/error, grasp mode, stop and fault clearing. This is the main starting point for extracting the driver.
- `minimal_test.py`: serial connection and register-read check.
- `raw_test.py`: low-level serial request/response check.
- `scan_gripper.py`: read-only Modbus scan over candidate baud rates, IDs, and register addresses.

No actual ROS gripper wrapper was identified in the inspected `fyp_tests` Python files. Ubuntu project files were not accessible through the attempted paths in this inspection, so an existing wrapper elsewhere has not been ruled out. Locate it before creating a duplicate package.

### Proposed structure and required work

- [ ] Extract `InspireGripper` into an importable module (for example `inspire_gripper.py`) with no connection or movement at import time. Keep Modbus details out of ROS callbacks and application code.
- [ ] Configure serial port, baud rate, device ID, timeout, and stroke calibration through constructor/configuration. Support both Windows and Ubuntu without source edits. Confirm WSL USB serial attachment and device permissions if operating from WSL; mirrored Ethernet alone does not expose USB serial hardware.
- [ ] Confirm installed PyModbus version and standardize its API (`slave=` versus `device_id=`) against that version. Pin compatible dependencies rather than mixing call conventions.
- [ ] Verify register addresses, value ranges, status meanings, and the assumed 0–70 mm width mapping against the actual gripper model/manual and hardware before relying on them. Existing comments/values are not validated specifications.
- [ ] Add consistent timeout/Modbus error reporting, handle failed reads before width conversion (`read_width_mm` currently divides a possible `None`), and ensure serial cleanup using try/finally or a context manager.
- [ ] Serialize hardware access if commands and polling run concurrently. Define bounded feedback polling and command behavior on disconnection/timeouts.
- [ ] Put manual exercises behind `if __name__ == "__main__":` in a separate script, with explicit selection of movement tests. A connection-only test should not automatically cycle the jaws.
- [ ] Build a thin ROS Noetic node around the driver. Expose configurable parameters, command interface, and timestamped measured feedback (width/position, status, fault). Choose topics/services/actions and units based on the FYP consumer's needs before coding them.
- [ ] Provide a launch file and a separate ROS connection test: confirm node registration, expected interfaces, and fresh measured feedback before explicitly commanded movement. Test transport failure and shutdown cleanup. Do not equate a ROS publisher existing with physical feedback arriving.
- [ ] Define shutdown/stop behavior explicitly; do not automatically close or open the gripper on startup/import/shutdown without a deliberate requirement. Existing `estop` is a Modbus stop command and should not be assumed to be a safety-rated emergency stop.

### Completion criteria

Importing the driver has no hardware side effects. The same hardware API is usable from a standalone script and ROS. Connection/status tests run without movement. Explicit commands produce measured feedback; errors are visible; port/configuration changes do not require source edits; shutdown releases the serial port. The existing UMI/gripper consumer can use the selected interface.

## LiDAR follow-up

- [x] Receive MID-360S PointCloud2 in ROS Noetic at about 10 Hz.
- [x] Receive IMU data at about 200 Hz.
- [x] Replay the recorded bag in RViz; user confirmed visualization works after setting Fixed Frame to `livox_frame`. CPU-rendering RViz instructions were used; exact renderer was not independently inspected.
- [x] Record and inspect a short LiDAR/IMU rosbag: `~/fyp/bags/mid360s_test.bag`, 29.8 s, 150.2 MB, 298 PointCloud2 and 5,960 Imu messages (user supplied rosbag info on 26 October). Visual inspection and content/timestamp validation remain outstanding.
- [x] Inspect UMI's expected topics/message types: both mapping launch files load `mid360_180.yaml`, selecting AVIA=1 and the `livox_ros_driver/CustomMsg` callback. Both installed generated CustomMsg MD5s match. Existing `msg_MID360s.launch` selects driver2 CustomMsg.
- [x] Verify live CustomMsg: topic type `livox_ros_driver2/CustomMsg`, received point count 19,968. Record `~/fyp/bags/mid360s_custom_test.bag`: 29.8 s, 110.6 MB, 298 CustomMsg messages and 5,982 Imu messages; CustomMsg MD5 matches UMI's generated type.
- [x] Verify UMI runtime integration: `/laserMapping` subscribes to `/livox/lidar` CustomMsg and `/cloud_registered` publishes at approximately 20 Hz (user output, 26 October). Configuration has `cut_frame_num: 2` for 10 Hz input. Successful processing/output is established; geometric accuracy and calibration remain unvalidated.
- [x] Visualize `/cloud_registered` in frame `camera_init`; user reports clean overlap during the qualitative movement check. This establishes a practical baseline, not a quantitative calibration result.
- [ ] Validate timestamps, gripper/camera/LiDAR calibration, and synchronization before sensor fusion.

Full LiDAR setup and debugging evidence: `MID360S_ROS_Noetic_Debugging_Handoff.md` alongside this file.
