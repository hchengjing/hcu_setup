#!/usr/bin/env python3

import rospy
from std_msgs.msg import Int32
from pymodbus.client import ModbusSerialClient

PORT = "/dev/ttyUSB0"
BAUDRATE = 115200
SLAVE_ID = 1

client = ModbusSerialClient(
    port=PORT,
    baudrate=BAUDRATE,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=1
)

def write_position(value):
    value = max(0, min(1000, value))

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
    rospy.init_node("inspire_gripper_node")

    if not client.connect():
        rospy.logerr("Could not connect to gripper")
        return

    rospy.loginfo("Connected to gripper on %s", PORT)

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

    rate = rospy.Rate(10)

    while not rospy.is_shutdown():

        position = read_position()

        if position is not None:
            position_pub.publish(position)

        rate.sleep()

    client.close()


if __name__ == "__main__":
    main()