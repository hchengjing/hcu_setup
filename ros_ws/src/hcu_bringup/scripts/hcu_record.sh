#!/bin/bash
# Record all rig topics into one bag:  hcu_record.sh [name] [duration_s]
# Camera at 20 Hz is ~22 MB/s, LiDAR+IMU ~3.5 MB/s: about 1.5 GB per minute.
source /opt/ros/noetic/setup.bash

NAME=${1:-hcu}
BAG=~/fyp/bags/${NAME}_$(date +%Y%m%d-%H%M%S).bag
mkdir -p ~/fyp/bags

TOPICS="/livox/lidar /livox/imu /left_camera/image /left_camera/camera_info /gripper/position /gripper/command"

ARGS=(-O "$BAG" --buffsize=2048)
[ -n "$2" ] && ARGS+=(--duration="$2")

echo "Recording to $BAG (Ctrl-C to stop)"
rosbag record "${ARGS[@]}" $TOPICS
rosbag info "$BAG"
