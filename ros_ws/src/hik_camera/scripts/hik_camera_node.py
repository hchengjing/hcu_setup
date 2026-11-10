#!/usr/bin/env python3

import ctypes
import sys

import rospy
from sensor_msgs.msg import CameraInfo, Image

# MVS Python bindings are not a pip package; the Linux SDK installs them here
MVIMPORT_PATH = rospy.get_param("/hik_camera/mvimport_path", "/opt/MVS/Samples/64/Python/MvImport")
sys.path.append(MVIMPORT_PATH)

from MvCameraControl_class import *  # noqa: E402,F401,F403
from CameraParams_const import *  # noqa: E402,F401,F403
from CameraParams_header import *  # noqa: E402,F401,F403
from MvErrorDefine_const import *  # noqa: E402,F401,F403
from PixelType_header import *  # noqa: E402,F401,F403

# Pixel formats published as-is; cv_bridge converts these to bgr8 for UMI
ENCODINGS = {
    PixelType_Gvsp_Mono8: ("mono8", 1),
    PixelType_Gvsp_BayerRG8: ("bayer_rggb8", 1),
    PixelType_Gvsp_BayerBG8: ("bayer_bggr8", 1),
    PixelType_Gvsp_BayerGB8: ("bayer_gbrg8", 1),
    PixelType_Gvsp_BayerGR8: ("bayer_grbg8", 1),
    PixelType_Gvsp_RGB8_Packed: ("rgb8", 3),
    PixelType_Gvsp_BGR8_Packed: ("bgr8", 3),
}


def check_ret(name, ret):
    if ret == MV_OK:
        rospy.loginfo("%s: OK", name)
        return True

    rospy.logerr("%s: FAILED, error = 0x%08X", name, ret)
    return False


def device_serial(device_info):
    raw = device_info.SpecialInfo.stUsb3VInfo.chSerialNumber
    return bytes(raw).split(b"\0", 1)[0].decode(errors="replace")


def open_camera(serial, frame_rate):
    device_list = MV_CC_DEVICE_INFO_LIST()

    if not check_ret("Enumerate devices", MvCamera.MV_CC_EnumDevices(MV_USB_DEVICE, device_list)):
        return None

    rospy.loginfo("Found %d USB camera(s)", device_list.nDeviceNum)

    chosen = None
    for i in range(device_list.nDeviceNum):
        info = ctypes.cast(device_list.pDeviceInfo[i], ctypes.POINTER(MV_CC_DEVICE_INFO)).contents
        sn = device_serial(info)
        rospy.loginfo("  [%d] serial %s", i, sn)

        if chosen is None and (not serial or sn == serial):
            chosen = info

    if chosen is None:
        rospy.logerr("No camera matches serial '%s'", serial)
        return None

    cam = MvCamera()

    if not check_ret("Create handle", cam.MV_CC_CreateHandle(chosen)):
        return None

    if not check_ret("Open device", cam.MV_CC_OpenDevice()):
        cam.MV_CC_DestroyHandle()
        return None

    check_ret("Set TriggerMode OFF", cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF))

    # Free-running full rate saturates usbipd and the stream stalls; cap it
    check_ret("Enable frame rate limit", cam.MV_CC_SetBoolValue("AcquisitionFrameRateEnable", True))
    check_ret("Set frame rate %.1f" % frame_rate, cam.MV_CC_SetFloatValue("AcquisitionFrameRate", frame_rate))

    return cam


def close_camera(cam):
    cam.MV_CC_StopGrabbing()
    cam.MV_CC_CloseDevice()
    cam.MV_CC_DestroyHandle()


def frame_to_msg(frame, frame_id, stamp):
    info = frame.stFrameInfo

    if info.enPixelType not in ENCODINGS:
        rospy.logerr_throttle(5, "Unsupported pixel type 0x%08X; set PixelFormat to Mono8/Bayer8/RGB8", info.enPixelType)
        return None

    encoding, channels = ENCODINGS[info.enPixelType]

    # Copy out of the SDK-owned buffer before it is freed
    data = ctypes.string_at(frame.pBufAddr, info.nFrameLen)

    msg = Image()
    msg.header.stamp = stamp
    msg.header.frame_id = frame_id
    msg.height = info.nHeight
    msg.width = info.nWidth
    msg.encoding = encoding
    msg.is_bigendian = 0
    msg.step = info.nWidth * channels
    msg.data = data[: msg.step * msg.height]
    return msg


def main():
    rospy.init_node("hik_camera")

    serial = rospy.get_param("~serial", "")
    frame_id = rospy.get_param("~frame_id", "camera")
    timeout_ms = rospy.get_param("~timeout_ms", 1000)
    frame_rate = rospy.get_param("~frame_rate", 20.0)

    if not check_ret("Initialize SDK", MvCamera.MV_CC_Initialize()):
        return

    cam = open_camera(serial, frame_rate)
    if cam is None:
        MvCamera.MV_CC_Finalize()
        return

    image_pub = rospy.Publisher("/left_camera/image", Image, queue_size=5)
    info_pub = rospy.Publisher("/left_camera/camera_info", CameraInfo, queue_size=5)

    if not check_ret("Start grabbing", cam.MV_CC_StartGrabbing()):
        close_camera(cam)
        MvCamera.MV_CC_Finalize()
        return

    frame = MV_FRAME_OUT()
    last_num = None
    dropped = 0

    while not rospy.is_shutdown():
        ret = cam.MV_CC_GetImageBuffer(frame, timeout_ms)

        if ret != MV_OK:
            rospy.logwarn_throttle(5, "GetImageBuffer failed: 0x%08X", ret)
            continue

        # Host receipt time, not exposure time; offset must be calibrated before fusion
        stamp = rospy.Time.now()
        info = frame.stFrameInfo

        if last_num is not None and info.nFrameNum > last_num + 1:
            dropped += info.nFrameNum - last_num - 1
            rospy.logwarn_throttle(5, "Camera frames dropped so far: %d", dropped)
        last_num = info.nFrameNum

        msg = frame_to_msg(frame, frame_id, stamp)
        cam.MV_CC_FreeImageBuffer(frame)

        if msg is None:
            continue

        # Uncalibrated: only size is filled until intrinsics are measured
        cam_info = CameraInfo()
        cam_info.header = msg.header
        cam_info.height = msg.height
        cam_info.width = msg.width

        image_pub.publish(msg)
        info_pub.publish(cam_info)

    close_camera(cam)
    MvCamera.MV_CC_Finalize()
    rospy.loginfo("Camera closed.")


if __name__ == "__main__":
    main()
