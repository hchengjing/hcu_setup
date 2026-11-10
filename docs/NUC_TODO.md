# NUC bringup TODO

Updated 28 October 2026. NUC: Windows 11 + WSL2 Ubuntu 20.04.6, ROS Noetic, repo at `~/fyp/UMI-3D`.

## Resume here

1. **Combined run failed at the USB step.** `hcu_up.sh` stopped with
   `usbipd: error: No devices found with hardware-id '2bdf:0001'` — the camera was not visible.
   Check it appears in Windows (`usbipd list`, busid was 1-15), then:
   `rosrun hcu_bringup hcu_up.sh` and in a second terminal `rosrun hcu_bringup hcu_record.sh test 30`.
   Verify all four rates under simultaneous load: `/livox/lidar` ~10 Hz, `/livox/imu`, `/left_camera/image` ~20 Hz, `/gripper/position` ~10 Hz.
   If `--hardware-id` keeps failing, fall back to `--busid` in `hcu_up.sh`.
2. **Commit today's work to `hcu_setup` (`clean-setup`)** once the combined run passes:
   new `ros_ws/src/hik_camera`, new `ros_ws/src/hcu_bringup`, edited `ros_ws/src/inspire_gripper/scripts/gripper_node.py` (params + bus lock, now executable), this file.
   Not in git (system config): `/etc/udev/rules.d/99-inspire-gripper.rules`, `C:\Users\nuc\.wslconfig`.

## Open issues

- **LiDAR/IMU packet loss ~4–7%.** IMU 185–191 Hz (laptop 200.4), point_num mean 18.7k–19.1k (full 19968). 0 errors in WSL UDP stack, so packets are lost before WSL (Windows / mirrored networking / I225-V NIC). Ideas: I225-V receive buffers and interrupt moderation, check whether Windows itself sees the full rate, compare with the laptop bag using the same analysis.
- **`roscore` hangs.** Under mirrored networking, connects to *closed* 127.0.0.1 ports time out instead of being refused (loopback is routed via `loopback0` to Windows), so roscore's "master already running?" probe never returns. Started mid-day 28 Oct; WSL restart did not fix it; Hyper-V firewall settings look normal. Workaround in `hcu_up.sh`: `rosmaster --core` + `rosrun rosout rosout`. Side effect to watch: anything connecting to a dead node port also hangs until timeout.
- **"imu loop back" burst in mapping.** One ~4 s backwards IMU jump (913 errors) shortly after mapping starts, then clean. Camera node logs also showed out-of-order wall-clock timestamps. Suspect WSL clock steps; LiDAR Time Sync is "No Sync".
- **Camera image blurry and dark.** Adjust lens focus/aperture; exposure/gain not yet set by the node.
- **Camera bandwidth over usbipd.** Full rate stalls the stream (`0x80000007`); node caps `AcquisitionFrameRate` at 20 Hz (22 MB/s). Higher rates untested.
- **Camera timestamps** are host receipt time, not exposure time; `CameraInfo` has size only (no intrinsics). Calibrate intrinsics, camera–LiDAR extrinsics and time offset before setting `img_en: 1`.
- **Gripper register mismatch.** Read-only check: position(61)=993, command(10)=0, speed(11)=500, force(12)=100, error(64)=0, status(65)=3. Confirm register meanings against the Inspire manual before commanding motion from ROS. `/gripper/position` is `std_msgs/Int32` with no header stamp.
- **Full mapping launch** `mapping_mid360_180.launch` still writes to `$(env HOME)/A_LIVO_UMI/...`; the minimal launch is fine.
- **Movement check in RViz** of live mapping on the NUC not done yet.

## After a reboot / WSL restart

- Devices stay bound; `hcu_up.sh` re-attaches them. Manually: `usbipd detach --busid 1-15` then `usbipd attach --wsl --busid 1-15` (camera); busid 1-2 is the gripper CH340.
- Close Livox Viewer before running the ROS driver.
