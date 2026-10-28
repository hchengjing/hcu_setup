# FYP / UMI-3D — project context and AI handoff

Updated: 28 October 2026, Asia/Singapore. Original project audit: 26 October 2026; later additions are dated below.

## Update — 28 October 2026: long-term battery power system

The user requested a future task to design a battery-powered electrical system for the HCU/ASUS NUC, Inspire gripper (24 V, user specified), camera, LiDAR, and synchronizer. This has been added to the FYP to-do list. Define exact device supply requirements and peak loads, target battery runtime/weight, regulated power rails, battery/BMS/charging, distribution/protection/wiring, and shutdown behavior. Deliver a power diagram, BOM, and staged simultaneous-load/runtime validation. No architecture or hardware selection has been completed; this is a long-term task alongside the immediate software integration work. Other status sections retain the original audit context unless explicitly updated.

## Read this first

### Workspace clarification — 28 October 2026

Further user-pasted source confirms `gripper_node.py` ends with the indented `main()` call. UMI's supplied CMake requires the legacy `livox_ros_driver`, `vikit_common`, `vikit_ros`, Eigen, PCL, OpenCV, Sophus and Boost thread, alongside standard ROS dependencies. It also requests `eigen_conversions`, absent from the supplied package.xml dependency list. Keep the Driver2 acquisition stack AND the legacy driver needed by the existing mapping build. The build uses `-march=native`; rebuild on the NUC. `assemble_hcu_setup.py` was prepared to copy selected source packages, SDK2, Sophus and custom tests into a separate destination; it has not yet been run against the user's WSL source or validated by a clean build. No repository cleanup/deletion or replacement push has been performed.

Latest node inspection (user-pasted source, 28 October): `~/catkin_ws/src/inspire_gripper/scripts/gripper_node.py` IS a real ROS wrapper. It initializes `inspire_gripper_node`, subscribes to `/gripper/command` (`std_msgs/Int32`), clamps commands to 0–1000 and writes register 10, reads register 61, and publishes successful raw position reads on `/gripper/position` (`std_msgs/Int32`) in a target 10 Hz loop. Hardcoded serial settings: `/dev/ttyUSB0`, 115200 baud, 8N1, ID 1, timeout 1 s; PyModbus calls use `slave=`. This supersedes earlier uncertainty about whether a ROS node exists. Source inspection establishes implementation, not a new runtime success or achieved feedback rate.

The pasted text ends at `if __name__ == "__main__":`; confirm the actual file contains an indented `main()` below it. Do not infer a syntax error from a possibly incomplete paste. No automatic movement command appears in the shown startup path. Remaining improvements: ROS serial parameters; dependency/version pinning; a lock for shared serial access between callback and polling loop; bounded command queue; exception-safe cleanup; and timestamped measured feedback if required for recording. The existing Int32 position message carries neither a timestamp nor units/status. Preserve the existing interface until consumers and tests are identified. Prior descriptions of `/gripper/command` as only proposed are now historical: that topic is implemented in this separate Catkin package; `/gripper/state` is still only proposed.

Package listing/build-file inspection from the user's pasted output: `inspire_gripper` contains `package.xml`, `CMakeLists.txt`, and `scripts/gripper_node.py`. Package/build dependencies currently declare `rospy` and `std_msgs`; the Python node's actual imports and behavior remain unread. `catkin_install_python(...)` is commented out, so there is no active Catkin install rule for the node. This does not by itself prove the script cannot run from a source/devel workspace. Package metadata still has placeholder maintainer contact and `<license>TODO</license>`; resolve the intended license rather than inventing one. No launch/config files were shown by the supplied listing. Inspect the existing node and any external module dependencies before packaging or refactoring.

Follow-up user output confirms `~/catkin_ws/src/inspire_gripper/package.xml` exists. The source directory contains the `inspire_gripper` folder and a Catkin `CMakeLists.txt` symlink to `/opt/ros/noetic/share/catkin/cmake/toplevel.cmake`. No nested `.git` entries were found by the supplied search. This establishes an existing ROS package outside the earlier audit scope; its node implementation, interfaces, dependencies, and runtime results still need inspection. Earlier statements about no ROS wrapper being found applied only to the inspected Windows tests/UMI paths and must not be read as proof that no gripper package exists. Reuse and inspect this package before writing a new wrapper.

The user confirmed another existing Catkin workspace at `/home/haoch/catkin_ws`, containing `build`, `devel`, and `src`. Their custom peripheral tests are at `C:\Users\haoch\Projects\fyp_tests`. The home directory also contains `Sophus`, `fyp`, and `ros_learning`.

Treat `~/catkin_ws/src` as a source location to inspect for the clean `hcu_setup` assembly. Its package contents and relationship to the previously tested `~/fyp/UMI-3D/umi_3d_slam_ws` have not yet been established; do not assume the two workspaces are interchangeable or that one supersedes the other. Preserve both working directories. Exclude generated `build/` and `devel/` from source packaging and rebuild on the NUC. This update records folder locations, not proof of a new build or hardware test.

This is a consolidated handoff for another AI helping Haoch continue a UMI-3D final-year project. It combines the user's latest updates, accessible project conversations, inspected Windows source files, and the existing LiDAR debugging/integration notes. Read the current-status sections before acting on older instructions.

The immediate goal is a portable ASUS NUC computer integrating a Livox MID-360S LiDAR/IMU, a Hikrobot/Hikvision RGB camera, and an Inspire gripper, with ROS Noetic acquisition, combined recording, calibration, and eventual UMI-3D processing. Do not assume that the original upstream gripper/camera interfaces match this hardware.

**Latest user updates take priority:**

1. The current gripper is Inspire. The user describes the change as “the arm is now the inspire gripper”; this identifies the gripper/end-effector, not a verified robot-arm model. USB and serial/TTY connectivity have been set up and tested on the current PC. The user wrote “usb and ttyl”; interpret this as serial/TTY context, but verify the actual adapter/interface. Linking the gripper to the NUC still needs doing.
2. LiDAR works in the existing laptop WSL instance. Native Ubuntu testing has not been established; the user is unsure whether it is needed as further proof.
3. Camera hardware has been tested and is fine. A complete operating/acquisition script is still needed. A one-frame SDK test exists; that is not a continuous ROS camera driver.
4. The NUC runs Windows, its desktop is set up, and its display now works. The user chose a fresh installation rather than exporting the laptop WSL environment. Installation instructions were supplied, but completion was NOT reported.

Do not reinstall or rewrite the working laptop LiDAR stack simply because a new AI cannot access it. Do not mark NUC deployment, full camera/gripper ROS integration, calibration, or synchronized collection as completed.

## Evidence and coverage

- **User-confirmed:** latest hardware progress and runtime outputs pasted into the LiDAR conversation.
- **Inspected source:** files under `C:\Users\haoch\Projects\fyp_tests`, the nearby CAD asset directory, and prior saved audits.
- **Prior inspection:** WSL source/configuration details come from the earlier LiDAR audit; WSL source was not re-inspected successfully while generating this README.
- **Planned:** interfaces, refactors, NUC installation commands, and integration tasks below are proposals unless explicitly marked complete.
- Some ChatGPT conversation assistant replies were returned only as `::chatgpt-content-reference` placeholders, and image contents were not available in those thread reads. This document does not claim to contain every historical FYP chat or project attachment.
- No hardware script was executed, no actuator was moved, and no device configuration was changed to prepare this handoff.

## Machines and environments

| Instance | Established state | Limits / next verification |
|---|---|---|
| Current laptop/PC, Windows | Windows tests at `C:\Users\haoch\Projects\fyp_tests`; gripper USB/TTY tested; camera tested | Current device model numbers, serial IDs, SDK paths, and dependency versions still need inventory |
| Laptop WSL2 | Distro `Ubuntu-20.04`; Ubuntu 20.04.6; ROS Noetic; shell shown as `haoch@chengjing`; working LiDAR/UMI baseline | Do not confuse this with native Ubuntu |
| ASUS NUC, Windows | Windows desktop and display working; intended portable acquisition PC | Fresh WSL/Ubuntu/ROS installation was requested and instructions supplied; execution/completion unconfirmed |
| Native Ubuntu on NUC | Mentioned as the intended target in the LiDAR integration chat | Conflicts with this chat's later Windows/WSL installation discussion; final OS decision unconfirmed |

Previously recorded laptop versions: WSL 3.0.3.0, kernel `6.18.54.1-microsoft-standard-WSL2`, WSLg 1.0.79, Windows build `10.0.26200.9711`, ROS version 1.17.4, Livox ROS Driver2 1.2.7. These are historical observations, not a fresh environment check.

Existing Ubuntu project root: `/home/haoch/fyp`.

Existing UMI checkout: `/home/haoch/fyp/UMI-3D`.

Existing ROS workspace: `/home/haoch/fyp/UMI-3D/umi_3d_slam_ws`.

The earlier assistant could inspect WSL files through `\\wsl.localhost\Ubuntu-20.04\home\haoch\fyp`, but direct `wsl.exe` execution returned `WSL/E_ACCESSDENIED`. In this README session, the UNC path could not be found. That is an access/availability limitation, not evidence that the user's project has disappeared. Linux runtime results below came from user-run commands.

## Current completion overview

| Component | Completed | Outstanding |
|---|---|---|
| Mechanical work | User reported mount CAD completed, printed, then re-CAD work for printing; local models exist | Assembly status, latest revision/fit, and final printed configuration unconfirmed |
| Inspire gripper | User confirms USB/TTY setup and testing; direct Modbus scripts exist | Portable driver, NUC serial setup, actual ROS node, measured-state recording, dataset integration |
| LiDAR/IMU | Windows Viewer, WSL live streams, two bags, playback/RViz, UMI subscriber and processed clouds; user reports clean overlap | NUC reproduction, timestamp/calibration checks, simultaneous sensor load test |
| Hikrobot camera | User confirms hardware works; SDK one-frame test exists | Continuous capture, conversion, timestamps, ROS Image/CameraInfo, NUC SDK setup |
| Calibration | Separate calibration source exists | No verified calibration dataset/results for this assembled rig established |
| Synchronization | Discussed; LiDAR/camera hardware synchronizer considered | Hardware trigger/clock setup and measured time alignment not established |
| Combined system | Integration audit and backlog exist | No demonstrated three-device bringup, combined bag, calibrated RGB fusion, or training-ready dataset |

## Inspire gripper: existing work and findings

Primary folder: `C:\Users\haoch\Projects\fyp_tests`.

| File | What the inspected code does |
|---|---|
| `test_gripper.py` | Defines `InspireGripper`, then connects and performs a long movement/test sequence at module scope. Best starting point for extracting a reusable driver. |
| `gripper_ros_test.py` | Direct Linux serial Modbus open/mid/close test. Despite the filename, it has no `rospy` initialization, ROS publishers/subscribers/services, or ROS connection test. |
| `minimal_test.py` | Windows Modbus connection and holding-register 1003 read using `device_id=`. |
| `raw_test.py` | PySerial raw request/response experiment, transmitting `01 03 04 25 00 04 86 21`. Comments identify it as an Inspire manual read frame; that claim was not independently verified here. |
| `scan_gripper.py` | Read-only Modbus scan of baud rates 115200/57600/19200, device IDs 1–10, and candidate registers 1003/1004/1010/1061/1065. |

Observed settings in code: Windows `COM10`, Linux `/dev/ttyUSB0`, 115200 baud, device ID 1, 8 data bits, no parity, one stop bit. These are reference values; a NUC can enumerate the adapter differently.

`test_gripper.py` uses reads at registers 61 (position), 65 (status), and 64 (error); writes at 10 (position), 11 (speed), and 12 (force); helper writes at 5/6/7/1 for modes/stop/fault/settings. It assumes raw position 0–1000 maps linearly to 0–70 mm. Treat these as implemented assumptions, not a verified manufacturer register map. Earlier diagnostic scripts use 1000-series read addresses, so reconcile the difference against the actual model/manual and known successful outputs.

The class includes open/close, width, speed, force, status text, grasp mode, software stop, and fault clearing. The existence of those methods does not prove every function was tested successfully. User confirmation establishes gripper connectivity/testing in general; per-function results were not supplied here.

Known code issues and next work:

- `test_gripper.py` and `gripper_ros_test.py` perform movement at module scope. Extract an import-safe hardware library and put explicit exercises in a separate CLI/main entry point.
- `test_gripper.py` uses PyModbus `device_id=`, while `gripper_ros_test.py` uses `slave=`. Check and pin the actual installed version before standardizing the API.
- `read_width_mm()` can divide `None` after a failed read; handle errors before numeric conversion.
- Parameterize port, baud, ID, timeout, stroke mapping, and limits; serialize serial access and close it reliably.
- Implement a real ROS node with command handling and timestamped measured feedback. Proposed `/gripper/command` and `/gripper/state` are NOT existing interfaces.
- Define units, valid/stale state, fault reporting, and explicit startup/shutdown behavior. The existing `estop()` name describes a Modbus register write, not a verified safety-rated emergency stop.

NUC connection options to evaluate:

1. Physically connect the existing USB serial adapter to the NUC and discover its new COM/TTY identity.
2. Under native Ubuntu, verify permissions and prefer `/dev/serial/by-id` or a device-specific udev alias over assuming `/dev/ttyUSB0`.
3. Under WSL2, configure and verify USB forwarding for the adapter; Ethernet mirrored networking does not forward USB serial devices. Repeat a connection/read-only check before movement tests.

No new cable/protocol architecture has been selected. Confirm whether the user means moving the existing adapter or leaving it attached to another PC and controlling remotely.

## Livox MID-360S: successful baseline

### Hardware and networking

- Sensor: **MID-360S**, not an assumed identical MID-360 setup.
- Previously recorded serial: `ARMCP8H0037535`; firmware: `35.01.01.08`.
- Sensor IP: `192.168.1.135`.
- Laptop dedicated Ethernet / intended driver host: `192.168.1.50/24`.
- Connection: Livox 1-to-3 splitter, Ethernet to laptop, external bench DC power. Earlier user report was 12 V / 0.5 A; whether 0.5 A was draw or current limit was unresolved.
- Windows Viewer worked after using a MID-360S-compatible version; the exact successful Viewer version was not recorded.
- Laptop WSL uses mirrored networking. Previously verified Ethernet address in WSL: `192.168.1.50/24`.
- Viewer showed IMU enabled and **Time Sync: No Sync**. Hardware synchronization has not been established.

Known config:

`/home/haoch/fyp/UMI-3D/umi_3d_slam_ws/src/livox_ros_driver2/config/MID360s_config.json`

Changes recorded on 23 October:

```text
Mid360s.host_net_info[0].host_ip: 192.168.1.5 -> 192.168.1.50
lidar_configs[0].ip:            192.168.1.12 -> 192.168.1.135
```

Backup: `MID360s_config.json.before-lidar-setup-20261023-182127.bak` beside that JSON. Recorded values include `lidar_type: 8`, `pcl_data_type: 1`, `pattern_mode: 0`, zero SDK extrinsics, host UDP ports 56101/56201/56301/56401/56501, discovery 56000. Zero SDK extrinsics do not establish calibrated rig extrinsics.

### What was actually verified on 26 October

- `/livox/lidar` PointCloud2 at approximately 10.001–10.020 Hz.
- `/livox/imu` `sensor_msgs/Imu` settling around 200.4 Hz.
- A received raw cloud header used frame `livox_frame`.
- Recorded `~/fyp/bags/mid360s_test.bag`: 29.8 s, 150.2 MB, 298 PointCloud2 messages and 5,960 Imu messages.
- Bag replay displayed successfully in RViz with Fixed Frame `livox_frame`.
- Switched to the existing CustomMsg launch; received `point_num: 19968`.
- Recorded `~/fyp/bags/mid360s_custom_test.bag`: 29.8 s, 110.6 MB, 298 CustomMsg messages and 5,982 Imu messages.
- `rostopic info /livox/lidar` showed publisher `/livox_lidar_publisher2` and subscriber `/laserMapping`.
- UMI published `/cloud_registered` at approximately 20 Hz; header frame `camera_init`.
- User reported that surfaces overlap cleanly in the qualitative movement test.

This is successful WSL transport, recording/playback, and LiDAR/IMU processing evidence. It is not a quantitative trajectory-accuracy, extrinsic-calibration, synchronization, or camera-fusion result. Native Ubuntu is not required to retroactively make this WSL test valid; the NUC still needs its own deployment test under whichever OS is chosen.

### Message compatibility finding

Both mapping launch variants load `mid360_180.yaml`. `lidar_type: 1` selects AVIA=1 and UMI's `livox_ros_driver::CustomMsg` callback, which uses per-point `offset_time`.

The live publisher reports `livox_ros_driver2/CustomMsg`. The inspected generated driver1/driver2 CustomMsg definitions have the same MD5, `e4d6829bdfe657cb6c21a746c86b21a6`, and the runtime subscription succeeded. Different package names alone did not prevent this tested connection. Preserve the exact proven definitions/configuration and recheck after updates.

PointCloud2 is valid and remains useful. The reason for selecting CustomMsg was the configured UMI input callback, not defective LiDAR output or an inherent inability of PointCloud2 to carry per-point timing. Renaming a topic does not convert a message schema. Keep both original bags.

UMI currently has `common/img_en: 0`, `lidar_en: 1`, and `cut_frame_num: 2`. Splitting 10 Hz input scans explains the approximately 20 Hz processed output. Successful mapping here was **LiDAR/IMU only**.

### Working laptop commands / operational notes

Source Noetic and the built workspace in each appropriate terminal:

```bash
source /opt/ros/noetic/setup.bash
source ~/fyp/UMI-3D/umi_3d_slam_ws/devel/setup.bash
```

Existing PointCloud2 launch:

```bash
roslaunch livox_ros_driver2 rviz_MID360s.launch rviz_enable:=false
```

Existing CustomMsg launch for the tested UMI path:

```bash
roslaunch livox_ros_driver2 msg_MID360s.launch
```

Run only the intended live driver, and close Windows Viewer when running ROS acquisition. Do not mix live publication and bag playback on the same topics unintentionally.

With the ROS master running, set `/use_sim_time` to false for live acquisition. For clocked replay, use true and `rosbag play --clock`. RViz playback used `LIBGL_ALWAYS_SOFTWARE=1 rviz`; the exact rendering backend was not independently checked. A dedicated GPU was not established as necessary for the successful visualization.

The tested mapping variant is `mapping_mid360_180_min.launch`, used with RViz disabled and a temporary trajectory CSV. Inspect its actual launch arguments before reconstructing the command. The full launch has an inherited `$(env HOME)/A_LIVO_UMI/...` CSV path and image relay/republish assumptions that should be parameterized before NUC use.

### Resolved / historical debugging

- Original Windows Ethernet had a self-assigned `169.254.*` address; corrected to the sensor subnet.
- WSL originally used NAT and was changed to mirrored networking through Windows `.wslconfig`.
- Discovery/UDP initially failed even when ping worked. Successful reception followed instructions for sensor-scoped Windows and Hyper-V inbound UDP rules. Exact applied rule state and the causal firewall layer were not independently verified.
- Rule names in the earlier handoff: `Livox-MID360S-UDP` and `Livox-MID360S-WSL`; sensor scope `192.168.1.135`, ports 56000–56501 as individually listed above. Inspect existing rules before changing them.
- An earlier `bind failed` / SDK-init failure did not recur; its precise cause was not established.
- SDK initialization alone was insufficient proof; actual incoming messages/rates established success.

On native Ubuntu, Windows/Hyper-V firewall rules and `.wslconfig` do not apply. If retaining `192.168.1.50` for the NUC, avoid another host using that same address on the same sensor LAN.

## Hikrobot / Hikvision camera

User reports the camera is fine after testing. Exact camera model, serial, lens, firmware, and SDK version for this specific setup were not established by the inspected local test.

Existing `C:\Users\haoch\Projects\fyp_tests\camera_test.py`:

1. Imports Hikrobot MVS Python bindings (`MvCameraControl_class`, `CameraParams_*`, `MvErrorDefine_const`).
2. Initializes SDK and enumerates USB devices via `MV_USB_DEVICE`.
3. Opens the first device, checks connectivity, disables trigger mode.
4. Starts grabbing and requests one frame with a 1,000 ms timeout.
5. Prints width, height, frame number, pixel type, and frame length.
6. Frees the SDK image buffer and closes/finalizes the camera.

It is a useful hardware smoke test, but does not continuously acquire, convert/save/display images, publish ROS data, implement synchronized triggering, or provide a reusable camera API. The latest user statement that operating scripts are unwritten refers to that missing application/ROS layer.

Next implementation:

- Install/verify MVS SDK and bindings for the NUC's actual Linux environment; Windows SDK paths/binaries are not a Linux installation.
- Select the camera by stable identity rather than `pDeviceInfo[0]`.
- Extract independent connect/start/get_frame/stop/close functionality with reliable cleanup and explicit SDK errors.
- Convert the actual SDK pixel format; copy frame memory before releasing SDK-owned buffers.
- Implement continuous ROS `sensor_msgs/Image` publication and matching `CameraInfo`; UMI's audited input topic is `/left_camera/image` and its callback converts to `bgr8`.
- Preserve frame counter, device timestamp, and host receipt metadata. Raw device ticks are not automatically ROS epoch timestamps; receipt time is not exposure time.
- Choose and validate actual camera intrinsics, distortion model, camera–LiDAR extrinsics, image orientation, and time offset before enabling visual fusion.

Prior UMI audit findings: `camera_pinhole_mid360_180.yaml` actively selects `EquidistantCamera` with inherited 1280x1024 intrinsics despite its filename. `fisheye_to_pinhole_node.py` has different default K/D and publishes `/left_camera/image_pinhole`. An inherited `img_time_offset: 0.015` is not a measured offset for this rig. Avoid mixing models or undistorting twice. Keep `img_en: 0` until this is resolved.

## Separate camera-calibration code

Folder: `C:\Users\haoch\Projects\fyp_tests\camera_calibration`.

Inspected source inventory:

| File | Role |
|---|---|
| `run.sh` | Runs environment checks and capture; default config `configs/abb_gofa_d405.yaml`; optional `uv` bootstrap |
| `src/main.py` | Capture entry point |
| `src/collect_calibration_data.py` | Interactive image/robot-pose collection, preview or terminal capture, output sessions |
| `src/capture_backends.py` | Robot and camera abstractions; UR RTDE, ABB RWS, command robot backends; RealSense, OpenCV, Azure Kinect camera backends |
| `src/check_environment.py` | Core/hardware dependency checks |
| `src/config_utils.py` | YAML loading, defaults, environment expansion |
| `src/dataset_io.py` | Saves images/depth, pose JSON, and `session.json` |
| `src/calibration_core.py` | Chessboard intrinsics, eye-in-hand/eye-to-hand calibration and result transforms |
| `src/calibrate_dataset.py` | Dataset calibration CLI; selectable OpenCV hand-eye method |
| `src/pose_utils.py` | Pose records, quaternion order conversion, matrix transformations |

Also present: `.python-version`, `uv.lock`, `.env.example`, `.venv`, `.git`, and `data_collection.egg-info`.

Important qualifications:

- `.python-version` specifies **3.12**, and source uses `datetime.UTC`. Keep it separate from ROS Noetic's usual Ubuntu 20.04 Python 3.8 runtime.
- No Hikrobot MVS backend was found in the inspected backend implementation.
- Default capture target ABB GoFa/D405 does not establish that this is the current FYP arm/camera configuration.
- No `configs/` directory or `pyproject.toml` was visible in this inspected folder. The launcher references configuration files and `uv sync`, so treat the local snapshot as incomplete until its expected files/dependencies are located.
- No captured calibration dataset or successful calibration result was established from this folder inventory.
- Core code uses `cv2.calibrateCamera`; do not assume its pinhole calibration is appropriate for the UMI fisheye lens/model without checking.

## Mechanical / CAD progress and other context

Accessible FYP chat user updates reported the gripper mount finished and printed, with assembly planned, followed by re-CAD work for printing. Final assembly/fit was not confirmed.

Local asset folder `C:\Users\haoch\Projects\umi_gripper` contains:

- `EG2-4CX.STEP` and an `EG2-4CX_...` folder/archive. This is a model-name clue, not confirmation of the physically installed gripper model.
- `gripper_fixed.stl`, `grippercradle.stl`, `gripperholder.stl`, `sensorholder.stl`.
- `mid-360S.stp`.
- UMI-3D STL assets for battery, bottom plate, left/right finger holders, fisheye lens, left/right gears, grip, handle, linkage, and top cover.

Previous discussions included a LiDAR/camera synchronizer, a 3-way LiDAR splitter, a DC lead still to be made/bought, and potential GPIO signal wiring. No synchronizer compatibility or completed wiring can be concluded from inaccessible image-only discussions. Jetson was an earlier research direction; the current portable-PC work concerns the ASUS NUC. Do not assume Jetson deployment happened.

## NUC setup status and implementation order

This chat supplied a fresh WSL2/Ubuntu 20.04/ROS Noetic installation procedure, including basic packages, ROS apt setup, UMI checkout, Sophus, rosdep, and catkin build. **Those were instructions, not executed/verified results.** Do not assume the NUC has Noetic, a compiled workspace, Miniforge, sensor SDKs, or transferred source.

The fresh-install example used `~/projects/UMI-3D`; the established laptop checkout uses `~/fyp/UMI-3D`. Choose the real NUC path and parameterize it rather than mixing them. A fresh upstream clone will not necessarily reproduce local MID-360S launch/config changes, SDK versions, or the minimal mapping launch.

Recommended next sequence:

1. Establish the NUC's chosen runtime: Windows + WSL2 Ubuntu 20.04, or native Ubuntu 20.04. Preserve the working laptop baseline as evidence.
2. Inventory source revisions/local modifications, SDK versions, device IDs, dependencies, and calibration artifacts. Copy source/configuration deliberately; rebuild instead of copying `build/`, `devel/`, binaries, or virtual environments as a portable install.
3. Reproduce the proven MID-360S CustomMsg/IMU path on the NUC: verify actual rates, record/replay a fresh short bag, then verify UMI mapping output.
4. Connect the Inspire USB/TTY adapter on the NUC; test reads, extract the driver, then implement timestamped ROS feedback and explicit commands.
5. Implement Hikrobot continuous acquisition and ROS images/calibration headers, initially with visual mapping disabled.
6. Add one configurable bringup entry point and a combined recording workflow. Proposed gripper topics/types still require implementation.
7. Record/replay LiDAR, IMU, camera, CameraInfo, measured gripper state, commands as needed, and relevant TF/TF static. Check rates, message contents, timestamp domains, drops, storage, CPU, and USB bandwidth under simultaneous load.
8. Calibrate intrinsics, rig extrinsics, and temporal alignment; implement hardware sync if required and verify it. Enable calibrated RGB fusion only afterward.
9. Adapt measured Inspire feedback into the intended dataset pipeline. A topic being present in a rosbag does not make upstream UMI dataset scripts consume it automatically.

Existing upstream UVC camera and `WSGController`/network-gripper scripts target different hardware. The audited gripper range path uses visual tags; gripper latency tooling uses WSG. Neither is a ready Inspire serial driver. Define the adapter rather than substituting device names blindly.

No successful complete dataset packaging, policy training, robot deployment, or combined three-device demonstration has been established in the available evidence.

## Sources and continuation notes

Upstream references (requirements, not proof of this rig's installation):

- [UMI-3D processing/SLAM](https://github.com/hku-mars/UMI-3D)
- [UMI-3D hardware](https://github.com/Physical-Intelligence-Laboratory/UMI-3D-Hardware)
- [Livox ROS Driver2](https://github.com/Livox-SDK/livox_ros_driver2)
- [Livox SDK2](https://github.com/Livox-SDK/Livox-SDK2)
- [WSL networking](https://learn.microsoft.com/en-us/windows/wsl/networking)
- [WSL USB forwarding](https://learn.microsoft.com/en-us/windows/wsl/connect-usb)

Local historical documents read for this handoff:

```text
C:\Users\haoch\Documents\Codex\2026-10-23\b\outputs\FYP_TODO.md
C:\Users\haoch\Documents\Codex\2026-10-23\b\outputs\MID360S_ROS_Noetic_Debugging_Handoff.md
C:\Users\haoch\Documents\Codex\2026-10-23\b\outputs\NUC_Three_Device_Integration_Audit.md
```

The older LiDAR handoff retains historical “not yet tested” paragraphs after subsequent successes. This README's current-status/evidence sections consolidate the later results. Do not regress completed tests because of those historical paragraphs.

Accessible conversations consulted:

- `Set up ASUS NUC Pro display` — current chat; Windows NUC, fresh install request, latest hardware updates.
- `Test Livox Mid-360 lidar` — `01a16833-967b-7c90-a8f7-47c1400e3b79`; detailed successful runtime outputs and integration audit.
- `FYP update planning` — `6adb3abc-9c04-83ec-841c-385f67327e49`; CAD/printing and earlier Jetson research direction.
- `FYP Gripper And LiDAR Agenda` — `6adadb04-3ec4-83ec-8532-de7a3426b3b1`; printed mount, assembly plan, bench-power/Ethernet context.
- `Umi Synchroniser Compatibility` — `6adb0d22-f17c-83ec-9fad-51955b695873`; images/replies insufficient to establish compatibility.

Paths above are provenance on the original PC; they will not automatically exist on the NUC. This README is intended to remain useful when uploaded alone to another AI.

### Update format for future work

For each new result record: date/time, machine/OS/distro, source revision/config change, exact command, observed message types/rates/outputs, evidence file/bag/log path, pass/fail, and remaining uncertainty. Keep proposed commands separate from completed tests, and record measured feedback separately from commanded values.

### Suggested prompt for the next AI

> Read this README before proposing changes. Continue my UMI-3D FYP using the tested laptop WSL LiDAR baseline, Inspire gripper USB/TTY tests, and Hikrobot one-frame SDK test. Help me establish the actual NUC runtime and integrate the three devices in stages. Do not treat supplied installation instructions as completed work, do not assume native Ubuntu testing or synchronized RGB fusion has happened, and do not run gripper motion scripts merely to inspect them. Start with the unresolved NUC OS/setup and the device/source inventory, then work toward reproducible combined acquisition and calibrated processing.
