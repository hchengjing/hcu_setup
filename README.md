# HCU setup

Selected source snapshot for Haoch's portable ASUS NUC UMI-3D system.
Assembled from the working laptop sources; source copying is not a fresh build or hardware test.

## Layout

- `ros_ws/src/inspire_gripper`: existing custom ROS gripper wrapper.
- `ros_ws/src/umi_3d_slam`: UMI mapping source, local launch files and configuration.
- `ros_ws/src/livox_ros_driver`: retained because UMI compiles against its CustomMsg.
- `ros_ws/src/livox_ros_driver2`: MID-360S acquisition driver and configuration.
- `ros_ws/src/rpg_vikit-master`: Vikit packages required by the mapping build.
- `third_party/Livox-SDK2`: Driver2 SDK source; deliberately outside Catkin package discovery.
- `third_party/Sophus`: laptop Sophus source snapshot.
- `hardware_tests`: custom Windows/Linux peripheral tests and separate calibration tooling.
- `docs`: source provenance, copied-file hashes, handoff, and upstream attribution.

## Existing gripper interface

`/gripper/command` (`std_msgs/Int32`) writes position register 10 after clamping to 0–1000.
`/gripper/position` (`std_msgs/Int32`) publishes register 61 reads at a target 10 Hz.
The existing code hardcodes `/dev/ttyUSB0`, 115200 baud, ID 1, and PyModbus `slave=`.
Runtime validation and portable configuration are still required on the NUC.
Several hardware test files perform movement at module scope: inspect rather than import/run casually.

## Build/deployment status

Target dependency baseline: Ubuntu 20.04 and ROS Noetic. UMI requires Eigen, PCL,
OpenCV, Sophus, Boost thread and its Catkin dependencies. Its CMake also requests
`eigen_conversions`, which the supplied package.xml does not declare.
SDKs must be built/installed deliberately before dependent ROS packages.
Retain the older Livox SDK source inside its driver if present; do not replace it with SDK2.
Check driver build files for any paths that assumed SDK2 lived in the old workspace.
The mapping build uses `-march=native`, so rebuild on the target NUC.

No build/devel/install directories, inherited Git metadata, recordings or root training
pipeline are copied. Package source and existing configuration are preserved without refactoring.
Regenerate the Catkin workspace top-level CMakeLists.txt on the target.
The gripper Python installation rule and dependency/version declarations still need review.
The separate calibration tooling targets Python 3.12; keep it isolated from Noetic Python.

Before publishing, review the file inventory and licenses, confirm the MID360s JSON and
minimal mapping launch exist, then initialize a new Git repository in this folder.
Do not delete or alter the working source workspaces or the remote repository during assembly.
