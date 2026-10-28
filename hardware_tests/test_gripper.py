from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException
import time

#need to find a port that works, not sure if it is consistent for all runs
PORT = "COM10"
BAUDRATE = 115200
SLAVE_ID = 1

class InspireGripper:
    def __init__(self):
        self.client = ModbusSerialClient(
            port=PORT,
            baudrate=BAUDRATE,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=1,
        )
    #connection functions
    def connect(self):
        if not self.client.connect():
            raise RuntimeError("Could not connect")
        print(f"Connected to gripper on {PORT}")

    def disconnect(self):
        self.client.close()

    #low level modbus
    def read_register(self, address):
        result = self.client.read_holding_registers(
            address=address,
            count=1,
            device_id=SLAVE_ID
        )
        if result.isError():
            print("Read error:", result)
            return None

        return result.registers[0]

    def write_register(self, address, value):
        result = self.client.write_register(
            address=address,
            value=value,
            device_id=SLAVE_ID
        )

        if result.isError():
            print("Write error:", result)
            return False

        print(f"Register {address} <- {value}")
        return True

    #raw feedback
    #for 10-1000
    def read_position(self):
        return self.read_register(61)

    def read_status(self):
        return self.read_register(65)

    def read_error(self):
        return self.read_register(64)

    #physical feedback
    #for 0-70mm handling
    def read_width_mm(self):
        raw = self.read_position()
        return raw / 1000.0 * 70.0

    def read_status_text(self):
        status_code = self.read_status()
        status_texts = {
            1: "Fully Open",
            2: "Fully Closed",
            3: "Stopped",
            4: "Closing/Grasping",
            5: "Opening",
            6: "Object Grasped",
        }
        return status_texts.get(status_code, "Unknown")

    #raw commands
    def write_position(self, value):
        value = max(0, min(1000, value))
        return self.write_register(10, value)

    def write_speed(self, value):
        value = max(10, min(1000, value))
        return self.write_register(11, value)

    def write_force(self, value):
        value = max(100, min(1000, value))
        return self.write_register(12, value)

    #physical/ convenience commands
    def write_width_mm(self, width_mm):
        width_mm = max(0, min(70, width_mm))
        raw = round(width_mm / 70.0 * 1000)
        return self.write_position(raw)

    def open(self):
        return self.write_position(1000)

    def close(self):
        return self.write_position(0)

    #safety /modes
    def estop(self):
        return self.write_register(6, 1)

    def clear_fault(self):
        return self.write_register(7, 1)

    def grasp_mode(self, continuous=False):
        if continuous:
            return self.write_register(5, 1)
        else:
            return self.write_register(5, 0)

    def save_settings(self):
        return self.write_register(1, 1)

import time

gripper = InspireGripper()

gripper.connect()

print("\n=== BASIC READ TEST ===")
print("Raw position:", gripper.read_position())
print("Width (mm):", gripper.read_width_mm())
print("Status:", gripper.read_status())
print("Status text:", gripper.read_status_text())
print("Error:", gripper.read_error())


print("\n=== OPEN TEST ===")
gripper.open()

for i in range(20):
    print(
        "Position:", gripper.read_position(),
        "| Width:", round(gripper.read_width_mm(), 1),
        "| Status:", gripper.read_status_text()
    )
    time.sleep(0.1)


print("\n=== PARTIAL WIDTH TEST ===")
gripper.write_width_mm(35)

for i in range(20):
    print(
        "Position:", gripper.read_position(),
        "| Width:", round(gripper.read_width_mm(), 1),
        "| Status:", gripper.read_status_text()
    )
    time.sleep(0.1)


print("\n=== SPEED TEST ===")
print("Slow movement")
gripper.write_speed(100)
gripper.open()
time.sleep(2)

gripper.close()
time.sleep(2)

print("Faster movement")
gripper.write_speed(600)
gripper.open()
time.sleep(2)


print("\n=== FORCE TEST ===")
print("Set low force")
gripper.write_force(150)

input("Place a soft object between the jaws and press Enter...")

gripper.close()

for i in range(30):
    print(
        "Position:", gripper.read_position(),
        "| Status:", gripper.read_status_text()
    )
    time.sleep(0.1)


print("\n=== ONE-GRASP MODE TEST ===")
gripper.open()
time.sleep(2)

gripper.grasp_mode(False)

input("Place the soft object back between the jaws and press Enter...")

gripper.close()

for i in range(30):
    print(
        "Position:", gripper.read_position(),
        "| Status:", gripper.read_status_text()
    )
    time.sleep(0.1)


print("\n=== CONTINUOUS-GRASP MODE TEST ===")
gripper.open()
time.sleep(2)

gripper.grasp_mode(True)

input("Place the soft object between the jaws and press Enter...")

gripper.close()

for i in range(50):
    print(
        "Position:", gripper.read_position(),
        "| Status:", gripper.read_status_text()
    )
    time.sleep(0.1)


print("\n=== EMERGENCY STOP TEST ===")
gripper.open()
time.sleep(2)

gripper.write_speed(100)
gripper.close()

time.sleep(0.3)

print("Sending emergency stop")
gripper.estop()

print(
    "Position:", gripper.read_position(),
    "| Status:", gripper.read_status_text()
)

time.sleep(1)


print("\n=== CLEAR FAULT TEST ===")
gripper.clear_fault()
print("Error after clear:", gripper.read_error())


print("\n=== RETURN TO SAFE OPEN POSITION ===")
gripper.open()
time.sleep(2)

print("Final position:", gripper.read_position())
print("Final width:", gripper.read_width_mm())
print("Final status:", gripper.read_status_text())

gripper.disconnect()