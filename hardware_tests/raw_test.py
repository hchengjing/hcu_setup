import serial
import time

PORT = "COM10"
BAUDRATE = 115200

ser = serial.Serial(
    port=PORT,
    baudrate=BAUDRATE,
    bytesize=8,
    parity=serial.PARITY_NONE,
    stopbits=1,
    timeout=1
)

# This is the EXACT read frame from Inspire's manual:
# Device 1
# Function 03
# Start register 1061 = 0x0425
# Read 4 registers
# CRC = 86 21

request = bytes.fromhex("01 03 04 25 00 04 86 21")

print("TX:", request.hex(" "))

ser.reset_input_buffer()
ser.write(request)
ser.flush()

time.sleep(0.1)

response = ser.read(100)

print("RX:", response.hex(" "))

ser.close()