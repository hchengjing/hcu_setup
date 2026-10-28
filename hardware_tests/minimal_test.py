from pymodbus.client import ModbusSerialClient

PORT = "COM10"
BAUDRATE = 115200
SLAVE_ID = 1

client = ModbusSerialClient(
    port=PORT,
    baudrate=BAUDRATE,
    bytesize=8,
    parity="N",
    stopbits=1,
    timeout=2
)

print("Connecting...")
print("Connected:", client.connect())

print("Reading register 1003...")

result = client.read_holding_registers(
    address=1003,
    count=1,
    device_id=SLAVE_ID
)

print("Raw result:", result)

if not result.isError():
    print("Register 1003 =", result.registers[0])
else:
    print("Modbus read failed:", result)

client.close()