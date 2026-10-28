from ctypes import *

from MvCameraControl_class import *
from CameraParams_const import *
from CameraParams_header import *
from MvErrorDefine_const import *


def check_ret(name, ret):
    if ret == MV_OK:
        print(f"{name}: OK")
        return True

    print(f"{name}: FAILED, error = 0x{ret:08X}")
    return False


# Initialize SDK
ret = MvCamera.MV_CC_Initialize()
if not check_ret("Initialize SDK", ret):
    exit()


device_list = MV_CC_DEVICE_INFO_LIST()

# Your camera is USB3
ret = MvCamera.MV_CC_EnumDevices(
    MV_USB_DEVICE,
    device_list
)

if not check_ret("Enumerate devices", ret):
    MvCamera.MV_CC_Finalize()
    exit()


print("Found", device_list.nDeviceNum, "camera(s)")


if device_list.nDeviceNum == 0:
    print("No USB camera found.")
    MvCamera.MV_CC_Finalize()
    exit()


# Get first camera
device_info = device_list.pDeviceInfo[0].contents

print(
    "Transport type:",
    hex(device_info.nTLayerType)
)


# Create camera
cam = MvCamera()


ret = cam.MV_CC_CreateHandle(device_info)

if not check_ret("Create handle", ret):
    MvCamera.MV_CC_Finalize()
    exit()


ret = cam.MV_CC_OpenDevice()

if not check_ret("Open device", ret):
    cam.MV_CC_DestroyHandle()
    MvCamera.MV_CC_Finalize()
    exit()


print(
    "Connected:",
    cam.MV_CC_IsDeviceConnected()
)


# Disable trigger mode for normal continuous testing
ret = cam.MV_CC_SetEnumValue(
    "TriggerMode",
    MV_TRIGGER_MODE_OFF
)

check_ret("Set TriggerMode OFF", ret)


# Start acquisition
ret = cam.MV_CC_StartGrabbing()

if not check_ret("Start grabbing", ret):
    cam.MV_CC_CloseDevice()
    cam.MV_CC_DestroyHandle()
    MvCamera.MV_CC_Finalize()
    exit()


# Retrieve one frame
frame = MV_FRAME_OUT()

ret = cam.MV_CC_GetImageBuffer(
    frame,
    1000
)

if ret == MV_OK:
    info = frame.stFrameInfo

    print("Frame received!")
    print("Width:", info.nWidth)
    print("Height:", info.nHeight)
    print("Frame number:", info.nFrameNum)
    print("Pixel type:", info.enPixelType)
    print("Frame length:", info.nFrameLen)

    # MUST release buffer after GetImageBuffer
    cam.MV_CC_FreeImageBuffer(frame)

else:
    print(
        f"GetImageBuffer failed: 0x{ret:08X}"
    )


# Cleanup
cam.MV_CC_StopGrabbing()
cam.MV_CC_CloseDevice()
cam.MV_CC_DestroyHandle()
MvCamera.MV_CC_Finalize()

print("Camera closed.")