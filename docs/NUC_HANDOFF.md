# NUC handoff: UMI-3D handheld (HCU) bring-up

**Written:** 10 Nov 2026, from the Claude session on the NUC.
**For:** a Claude session (or a person) on another laptop who is continuing this work.
**Sources:** the three earlier Claude sessions on this NUC (26 Oct, 28 Oct, 8–9 Nov), the shell history, `docs/NUC_TODO.md`, and the git state of both repos as of today.

> **If you are a Claude session reading this:** this file covers everything done on the NUC so far. Read it, then `docs/NUC_TODO.md` in the same folder. The NUC is a Windows 11 PC running WSL2, not native Linux. Most of the strange problems below come from that. Don't suggest anything that needs native Linux without saying so.

---

## 1. TL;DR

| Area | Status |
|---|---|
| WSL2 Ubuntu 20.04.6 + ROS Noetic desktop-full | ✅ Installed, working |
| `hcu_setup` repo (`clean-setup` branch) built in `~/fyp/UMI-3D/ros_ws` | ✅ Builds |
| Livox MID-360S LiDAR live in ROS | ✅ Works. ⚠️ ~4–7% packet loss into WSL; link dropped once (hardware/cable) |
| UMI-3D mapping on live LiDAR (`mapping_mid360_180_min.launch`) | ✅ `/cloud_registered` ~20 Hz. RViz movement check **not done** |
| Hikrobot MV-CB013 camera via usbipd | ✅ Streams at 20 fps (capped). ⚠️ `0x80000007` "no data" errors came back on 9 Nov |
| Inspire gripper (CH340 serial) via usbipd | ✅ Read-only check passes. Not commanded to move yet |
| All 3 devices together (`hcu_bringup`) | ❌ **Never passed.** First try failed at the USB attach step |
| Upstream `hku-mars/UMI-3D` in a pixi workspace (`~/UMI-3D/umi_3d_slam_ws`) | ✅ Builds and launches. Tested on a recorded bag only |
| New code committed / pushed | ❌ **Nothing new is committed.** See §7 |

---

## 2. The machine

- **Hardware:** ASUS NUC 12 Pro (NUC12WSH), 12th-gen Intel, 64 GB RAM, 500 GB Kingston SSD, Intel I225-V Ethernet. Intel graphics only, no NVIDIA GPU, so **policy training can't run on this PC**.
- **OS:** Windows 11 + **WSL2 Ubuntu 20.04.6**, user `nuc` (sudo), systemd on. Hostname `DESKTOP-H4L7SGU`. No dual-boot. Dual-boot was discussed and put off; WSL was chosen "for now".
- **WSL networking:** mirrored mode, in `C:\Users\nuc\.wslconfig`:
  ```ini
  [wsl2]
  networkingMode=mirrored
  ```
- **Windows network:** the "Ethernet" adapter (I225-V) has a static **192.168.1.50/24**. The LiDAR is **192.168.1.135**.
- **Windows firewall rules** (added by the user as admin):
  ```powershell
  New-NetFirewallRule -DisplayName "Livox-MID360S-UDP" -Direction Inbound -Protocol UDP -RemoteAddress 192.168.1.135 -LocalPort 56000-56501 -Action Allow
  New-NetFirewallHyperVRule -Name "Livox-MID360S-WSL" -DisplayName "Livox-MID360S-WSL" -Direction Inbound -VMCreatorId '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' -Protocol UDP -RemoteAddresses 192.168.1.135 -LocalPorts 56000-56501 -Action Allow
  ```
- **usbipd-win 5.3.0** (installed with winget), used to pass the USB devices through to WSL.

---

## 3. Software installed in WSL

| Item | Where | Notes |
|---|---|---|
| ROS Noetic desktop-full | `/opt/ros/noetic` | roscpp 1.17.4, same as the laptop. Sourced in `~/.bashrc`; rosdep set up |
| Build tools, Eigen, PCL, OpenCV, `libosmesa6-dev`, `libgl1-mesa-glx`, `libglfw3`, `patchelf` | apt | Needed by the UMI data pipeline |
| Sophus (bitcat-tech fork) | `~/fyp/deps/Sophus` | Installed to `/usr/local`. There's also a second build, `build-pixi/`, made with the pixi toolchain (see §5) |
| Livox SDK2 | reinstalled from `hcu_setup/third_party/Livox-SDK2` | Same version as the laptop |
| Original Livox SDK (v1) | built from `ros_ws/src/livox_ros_driver/Livox-SDK` | Without it, the driver's CMake deletes that folder and clones it again |
| Miniforge | `~/miniforge3` | `auto_activate_base: false`, so it doesn't break catkin |
| Hikrobot MVS SDK 5.1.1 (Linux x86_64 `.deb`) | `/opt/MVS` | The Windows zip `MVS_Win_STD_5.1.1_261015.zip` is also in Downloads |
| pixi + `pixi-ros` | `~/.pixi` | Only for the upstream workspace in §5 |
| udev rule | `/etc/udev/rules.d/99-inspire-gripper.rules` | Gripper CH340 → `/dev/inspire_gripper` |

---

## 4. Main workspace: `~/fyp/UMI-3D` (the `hcu_setup` repo)

- Remote: `https://github.com/hchengjing/hcu_setup.git`, branch **`clean-setup`** at `fc9428a` ("Assemble clean HCU setup with sensor drivers and peripheral tests"). That's the same commit as `origin`.
- The catkin workspace is **`~/fyp/UMI-3D/ros_ws`**, not `umi_3d_slam_ws` as in the older laptop handoff:
  ```bash
  source ~/fyp/UMI-3D/ros_ws/devel/setup.bash
  ```
- Built with `catkin_make -DROS_EDITION=ROS1`, after copying `livox_ros_driver2/package_ROS1.xml` to `package.xml` (that file is in `.gitignore`).
- Packages: `livox_ros_driver`, `livox_ros_driver2`, `umi_3d_slam`, `inspire_gripper`, `vikit_common`, `vikit_ros`, plus two **new, uncommitted** packages, `hik_camera` and `hcu_bringup`.
- `MID360s_config.json`: `host_ip 192.168.1.50`, LiDAR `192.168.1.135`.
- The CustomMsg fingerprint `e4d6829b…` is the same for livox_ros_driver and driver2, so UMI reads driver2 messages directly.

### 4.1 New package `hik_camera` (uncommitted)
- Node `hik_camera_node.py` uses the MVS Python API (the same approach as `camera_test.py`).
- Publishes `/left_camera/image` (the topic UMI reads) and `/left_camera/camera_info` (image size only, **no intrinsics yet**).
- Default frame-rate cap is **20 fps**. Override with `frame_rate:=N`. Choose a camera by serial or take the first one found. Each frame is copied out of the SDK buffer before it's released, and the node warns when the camera's frame counter shows dropped frames.
- Camera: **MV-CB013-A0UC-S**, serial `DB2638512`, 1280×1024, BayerGB8 → `bayer_gbrg8`, converted to `bgr8` the same way UMI does.
- Timestamps are the time the NUC **receives** each frame, not the exposure time.
- Launch: `roslaunch hik_camera hik_camera.launch [frame_rate:=10]`

### 4.2 New package `hcu_bringup` (uncommitted)
- `hcu.launch`: LiDAR + camera + gripper, with optional `mapping:=true` and `gripper:=false`.
- `hcu_up.sh`: re-attaches the USB devices with `usbipd.exe` (called from WSL), pings the LiDAR, starts the ROS master the way that works on this WSL (`rosmaster --core` + `rosout`; see §6.2), then launches.
- `hcu_record.sh [name] [seconds]`: records all topics to `~/fyp/bags`. That's about 1.5 GB/min with the camera at 20 Hz.

### 4.3 Edited `inspire_gripper/scripts/gripper_node.py` (uncommitted)
- Port, baud rate, ID and polling rate are now ROS params. The default port is `/dev/inspire_gripper` instead of the hard-coded `/dev/ttyUSB0`.
- A lock makes serial reads and commands take turns so they can't collide. The file is now executable.

---

## 5. Second workspace: upstream `hku-mars/UMI-3D` in pixi (`~/UMI-3D/umi_3d_slam_ws`)

Session of 8–9 Nov. This is a separate clone of the upstream repo (`origin = hku-mars/UMI-3D`, **not** the user's fork), built with **pixi + RoboStack Noetic** instead of system ROS. Its purpose is running UMI-3D's own SLAM from a clean environment.

**`pixi.toml` (new, untracked):** RoboStack noetic channels. Key changes from the defaults:
- added `ros-noetic-eigen-conversions` (CMake couldn't find it)
- pinned `empy = "==3.3.4"` (empy 4.x breaks message generation with a `RAW_OPT` error)
- `cmake = "<4"`
- added `ros-noetic-rviz`, `ros-noetic-compressed-image-transport`, `ros-noetic-topic-tools`
- build task: `catkin_make -DSophus_DIR=/home/nuc/fyp/deps/Sophus/build-pixi`. Sophus was rebuilt with the pixi compiler because the system build wouldn't link.

**Source patches (uncommitted, 6 files)**, needed because pixi's Boost and PCL 1.15 require C++14 or later:
- `livox_ros_driver/CMakeLists.txt`: C++11 → C++17, added `/usr/local/include`, links `${LIVOX_SDK_LIBRARY}` by its full path
- `livox_ros_driver/timesync/timesync.h`: added `#include <memory>`
- `livox_ros_driver/livox_ros_driver/lddc.cpp` lines ~353/357: publish `*cloud`, because PCL 1.15 uses `std::shared_ptr`
- `rpg_vikit-master/vikit_common` and `vikit_ros` CMakeLists: `-std=c++0x/c++11` → `-std=c++17`
- `umi_3d_slam/launch/mapping_mid360_180.launch`: `csv_path` → `$(find umi_3d_slam)/output/camera_trajectory.csv` (it used to point at a laptop path, `~/A_LIVO_UMI/...`)

**Result:** `pixi run build` succeeds and produces `fastlivo_mapping` and `save_camera_trajectory`. `roslaunch umi_3d_slam mapping_mid360_180.launch rviz:=true` starts every node cleanly. Tested only by replaying `~/fyp/bags/nuc_mid360s_custom_test.bag` (LiDAR + IMU, no images; `img_en: 0`).

**Warning:** PCL was built without AVX, but the code is built with `-march=native`, which turns AVX on. If the nodes segfault, remove `-march=native` from `umi_3d_slam/CMakeLists.txt` first.

**Important rule:** **never run the system-ROS workspace (`~/fyp/UMI-3D/ros_ws`) from inside `pixi shell`.** You can tell you're in pixi when the prompt starts with `(umi_3d_slam_ws)`. Mixing the two breaks `roslaunch`, because pixi's Python 3.12 packages get loaded into the system's Python 3.8. Live sensors use the system-ROS workspace in a plain terminal.

---

## 6. Test results and known problems

### 6.1 LiDAR, 28 Oct live test (`msg_MID360s.launch`, CustomMsg)

| Check | NUC | Laptop |
|---|---|---|
| Ping 192.168.1.135 | ~2 ms from Windows and WSL | — |
| `/livox/lidar` | 10.04 Hz | ~10.0 Hz |
| `/livox/imu` | **185–191 Hz** ⚠️ | ~200.4 Hz |
| Points per scan | **18.7k–19.1k mean** ⚠️ | 19968 |
| 30 s bag | 298 scans, 5564 IMU msgs, 102.9 MB | 298 scans, 5982 IMU msgs |
| Mapping `/cloud_registered` | 20.07 Hz, frame `camera_init` | ~20 Hz |

On 9 Nov, with the PointCloud2 launch (`rviz_MID360s.launch`, `xfer_format=0`), `/livox/lidar` came in at about **7 Hz**, with gaps of up to 5 s.

### 6.2 Problems still open
1. **LiDAR/IMU packet loss of about 4–7%.** WSL shows no UDP errors, so the packets are lost before they reach WSL: in Windows, in mirrored networking, or at the I225-V card. Ideas to try: the I225-V receive buffers and interrupt moderation, and checking whether Windows itself gets the full rate.
2. **`roscore` hangs on this WSL.** In mirrored mode, connecting to a *closed* port on 127.0.0.1 times out instead of being refused straight away, so roscore's "is a master already running?" check never returns. Workaround: `rosmaster --core &` then `rosrun rosout rosout`. On 9 Nov the user ran plain `roscore` in their own terminal and it worked, so this seems to come and go.
3. **Two `roslaunch` commands started at once** each start their own master, collide (`RLException: run_id ... does not match`), and both die. Fix: start `roscore` first and wait for "started core service".
4. **"bind failed" in livox_ros_driver2** means port 56000 is taken (close Livox Viewer on Windows) **or** 192.168.1.50 has disappeared because the Ethernet link is down. In mirrored mode WSL only has that IP while the Windows adapter is connected.
5. **The Ethernet link dropped on 9 Nov:** Windows showed "Disconnected / 0 bps" for a long time. That was a power or cable problem at the LiDAR end. It came back as Up at 100 Mbps after the hardware was replugged. Quick check:
   ```bash
   ip -4 addr | grep 192.168.1.50 && ping -c2 192.168.1.135
   ```
6. **Camera `GetImageBuffer failed: 0x80000007` (no data).** usbipd can't carry the camera at full rate. It was fine at 20 fps on 28 Oct, then failed again on 9 Nov. Next step: try `frame_rate:=5` and a longer `timeout_ms`. That param isn't exposed in the launch file yet, so it has to be set with `rosparam set /hik_camera/timeout_ms 3000` before launching. If it still fails, test the camera in Windows MVS to separate a camera problem from a passthrough problem.
7. **Camera image is blurry and dark.** Adjust the lens focus and aperture. The node doesn't set exposure or gain yet.
8. **Calibration not done:** camera intrinsics, camera–LiDAR extrinsics and the time offset. This is needed before `img_en: 1`. The LiDAR time sync is "No Sync".
9. **"imu loop back" burst** (about 4 s, 913 errors) just after mapping starts, then clean. Probably the WSL clock jumping.
10. **Gripper registers:** position(61)=993, command(10)=0, speed(11)=500, force(12)=100, error(64)=0, status(65)=3. Check them against the Inspire manual before commanding motion. `/gripper/position` is `std_msgs/Int32` with no timestamp.
11. **`mapping_mid360_180.launch` in `hcu_setup`** still writes to `$(env HOME)/A_LIVO_UMI/...`. The same fix was applied in the pixi workspace (§5) but not here.

---

## 7. What is NOT saved anywhere off this NUC

None of this has been pushed. The other laptop **can't see** any of it unless it's committed:

| Change | Repo | State |
|---|---|---|
| `ros_ws/src/hik_camera/` | hcu_setup | untracked |
| `ros_ws/src/hcu_bringup/` | hcu_setup | untracked |
| `inspire_gripper/scripts/gripper_node.py` | hcu_setup | modified |
| `docs/NUC_TODO.md`, `docs/NUC_HANDOFF.md` (this file) | hcu_setup | untracked |
| pixi workspace: `pixi.toml`, `pixi.lock`, `README_PIXI.md`, 6 source patches | `~/UMI-3D` (upstream hku-mars clone, no push access) | uncommitted. Needs a fork or a copy into hcu_setup |
| `/etc/udev/rules.d/99-inspire-gripper.rules`, `C:\Users\nuc\.wslconfig`, Windows IP and firewall | system config | documented above only |

---

## 8. Daily run commands (NUC)

Use **plain terminals, not `pixi shell`**:

```powershell
# Windows PowerShell, once after reboot or replug (bind already done; attach needs no admin)
usbipd list
usbipd attach --wsl --busid 1-15   # camera (on 9 Nov it showed as 2-3 / 2-7, so check usbipd list)
usbipd attach --wsl --busid 1-2    # gripper CH340 (COM3)
```

```bash
# T1
roscore            # if it hangs: rosmaster --core &  then  rosrun rosout rosout
# T2: LiDAR + RViz (PointCloud2)
source ~/fyp/UMI-3D/ros_ws/devel/setup.bash && roslaunch livox_ros_driver2 rviz_MID360s.launch
# T3: camera
source ~/fyp/UMI-3D/ros_ws/devel/setup.bash && roslaunch hik_camera hik_camera.launch frame_rate:=10
# In RViz: Fixed Frame = livox_frame; Add → By topic → /left_camera/image → Image
```

All in one (not passed yet):
```bash
rosrun hcu_bringup hcu_up.sh
rosrun hcu_bringup hcu_record.sh test 30
```

Live SLAM: `roslaunch hcu_bringup hcu.launch gripper:=false mapping:=true` (sends CustomMsg, which RViz can't draw raw).

Upstream SLAM on a bag (pixi workspace):
```bash
cd ~/UMI-3D/umi_3d_slam_ws && pixi shell
roslaunch umi_3d_slam mapping_mid360_180.launch rviz:=true
# 2nd terminal
pixi run rosbag play /home/nuc/fyp/bags/nuc_mid360s_custom_test.bag
```

---

## 9. Power design notes (28 Oct session, design only, nothing built)

- **Budget:** NUC 30 W typical / 65 W peak, gripper (24 V) 10 W / 72 W, Livox 6.5 W / ~14 W at startup, camera 3–5 W, sync board + buttons 1–2 W. **Total about 50 W typical, about 155–160 W peak.**
- UMI-3D's stock "12V DC Battery" (¥79) is likely a 2–3 A barrel-jack pack. That's **not enough** for the NUC plus the gripper.
- **Option 1:** one 12.8 V LiFePO4 4S pack, about 10 Ah (128 Wh, under the 160 Wh airline limit), 15–20 A battery management, XT60. Use a 19 V rail for the NUC (check its input range) and a 24 V boost for the gripper. About 2–2.5 h at typical load.
- **Option 2 (cleaner):** keep the stock 12 V pack for the Livox and sync board, and add a second high-current pack for the NUC and gripper. Tie the two grounds together.
- **Rules:** put the E-stop on the gripper's 24 V converter only; use a common ground for the PPS signal (Livox PPS is 3.3 V); fuse every branch (10 A main); add ≥470 µF at the Livox; wire buttons to the sync board's GPIO so they're timestamped on the PPS clock; consider ideal-diode dual inputs so packs can be hot-swapped.

---

## 10. Suggested next steps (in order)

1. Make the camera stream reliably again (lower fps / timeout, check the USB 3 port, test in Windows MVS).
2. Run `hcu_up.sh` and check all rates with everything running together: lidar ~10 Hz, imu ~200, image ~20, gripper ~10.
3. **Commit and push** the new `hcu_setup` work (§7). Decide where the pixi workspace and patches go.
4. Do the RViz movement check of live mapping.
5. Look into the packet loss, or decide that native Ubuntu (dual-boot) is the real fix for the LiDAR, the USB3 camera and CAN.
6. Calibrate the camera (intrinsics, extrinsics, time offset), then try `img_en: 1`.
