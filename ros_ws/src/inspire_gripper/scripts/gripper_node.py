#!/usr/bin/env python3

import threading

import rospy
from std_msgs.msg import Int32
from pymodbus.client import ModbusSerialClient

SLAVE_ID = 1

client = None

# Command callbacks run on a different thread than the read loop; one bus, one request at a time
bus_lock = threading.Lock()

def write_position(value):
    value = max(0, min(1000, value))

    with bus_lock:
        result = client.write_register(
            address=10,
            value=value,
            slave=SLAVE_ID
        )

    if result.isError():
        rospy.logerr("Write error: %s", result)
        return False

    rospy.loginfo("Position command sent: %d", value)
    return True


def read_position():
    with bus_lock:
        result = client.read_holding_registers(
            address=61,
            count=1,
            slave=SLAVE_ID
        )

    if result.isError():
        rospy.logerr("Read error: %s", result)
        return None

    return result.registers[0]


def command_callback(msg):
    write_position(msg.data)


def main():
    global client, SLAVE_ID

    rospy.init_node("inspire_gripper_node")

    # udev alias from /etc/udev/rules.d/99-inspire-gripper.rules
    port = rospy.get_param("~port", "/dev/inspire_gripper")
    baudrate = rospy.get_param("~baudrate", 115200)
    SLAVE_ID = rospy.get_param("~slave_id", 1)
    rate_hz = rospy.get_param("~rate", 10)

    client = ModbusSerialClient(
        port=port,
        baudrate=baudrate,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=1
    )

    if not client.connect():
        rospy.logerr("Could not connect to gripper on %s", port)
        return

    rospy.loginfo("Connected to gripper on %s", port)

    rospy.Subscriber(
        "/gripper/command",
        Int32,
        command_callback
    )

    position_pub = rospy.Publisher(
        "/gripper/position",
        Int32,
        queue_size=10
    )

    rate = rospy.Rate(rate_hz)

    while not rospy.is_shutdown():

        position = read_position()

        if position is not None:
            position_pub.publish(position)

        rate.sleep()

    client.close()


if __name__ == "__main__":
    main()