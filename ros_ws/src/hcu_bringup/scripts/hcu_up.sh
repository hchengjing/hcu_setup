#!/bin/bash
# Bring up the whole rig from WSL: attach USB devices, start the ROS master, launch hcu.launch.
# Extra arguments go to roslaunch, e.g.  hcu_up.sh mapping:=true camera_frame_rate:=15
set -e

USBIPD="/mnt/c/Program Files/usbipd-win/usbipd.exe"
DEVICES="2bdf:0001 1a86:7523"   # Hikrobot camera, Inspire gripper CH340

source /opt/ros/noetic/setup.bash
source ~/fyp/UMI-3D/ros_ws/devel/setup.bash

# 1) USB devices. After a WSL restart usbipd can still list them as attached to the old VM,
#    so detach and attach again when Linux cannot see them.
for hwid in $DEVICES; do
  if lsusb -d "$hwid" > /dev/null; then
    echo "[usb] $hwid present"
    continue
  fi
  "$USBIPD" detach --hardware-id "$hwid" > /dev/null 2>&1 || true
  "$USBIPD" attach --wsl --hardware-id "$hwid"
  sleep 2
  lsusb -d "$hwid" > /dev/null && echo "[usb] $hwid attached" || { echo "[usb] $hwid NOT visible; is it plugged in and bound (usbipd bind)?"; exit 1; }
done

# 2) LiDAR link
ping -c 1 -W 2 192.168.1.135 > /dev/null && echo "[lidar] 192.168.1.135 reachable" || { echo "[lidar] no reply from 192.168.1.135"; exit 1; }

# 3) ROS master. roscore hangs here (its "master already running?" probe never gets a
#    refusal under mirrored networking), so check the port locally and start rosmaster directly.
if ss -ltn | grep -q ':11311 '; then
  echo "[ros] master already running"
else
  mkdir -p ~/.ros/log
  rosmaster --core > ~/.ros/log/rosmaster.out 2>&1 &
  until ss -ltn | grep -q ':11311 '; do sleep 0.5; done
  rosrun rosout rosout > /dev/null 2>&1 &
  echo "[ros] master started"
fi

# 4) Devices
exec roslaunch hcu_bringup hcu.launch "$@"
