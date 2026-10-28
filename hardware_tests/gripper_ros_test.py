from pymodbus.client import ModbusSerialClient
import time

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

if not client.connect():
    raise RuntimeError("Could not connect to gripper")

print("Connected to gripper")

def write_position(value):
    value = max(0, min(1000, value))

    result = client.write_register(
        address=10,
        value=value,
        slave=SLAVE_ID
    )

    if result.isError():
        print("Write error:", result)
        return False

    print(f"Position command sent: {value}")
    return True


print("\n=== FULL OPEN ===")
write_position(1000)
time.sleep(2)

print("\n=== MIDWAY ===")
write_position(500)
time.sleep(2)

print("\n=== FULL CLOSE ===")
write_position(0)
time.sleep(2)

client.close()

print("\nTest complete")