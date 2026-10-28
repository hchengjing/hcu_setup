from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException

PORT = "COM10"

BAUDRATES = [
    115200,
    57600,
    19200,
]

SLAVE_IDS = range(1, 11)

# We only need a register that is likely to exist.
# Try several likely holding-register addresses.
TEST_REGISTERS = [
    1003,
    1004,
    1010,
    1061,
    1065,
]

print("Starting read-only Modbus scan.")
print("This script will NOT send write commands.\n")

found = []

for baudrate in BAUDRATES:

    print("=" * 50)
    print(f"Testing baud rate: {baudrate}")

    client = ModbusSerialClient(
        port=PORT,
        baudrate=baudrate,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=0.4,
        retries=0,
    )

    if not client.connect():
        print(f"Could not open {PORT}")
        continue

    for slave_id in SLAVE_IDS:

        for address in TEST_REGISTERS:

            try:
                result = client.read_holding_registers(
                    address=address,
                    count=1,
                    device_id=slave_id,
                )

                if not result.isError():

                    value = result.registers[0]

                    print(
                        f"\n*** RESPONSE FOUND ***\n"
                        f"Baud:     {baudrate}\n"
                        f"Slave ID: {slave_id}\n"
                        f"Register: {address}\n"
                        f"Value:    {value}\n"
                    )

                    found.append(
                        (baudrate, slave_id, address, value)
                    )

                    # Once this slave responds,
                    # don't hammer it with every test register.
                    break

            except (ModbusIOException, Exception):
                pass

        if found and found[-1][0] == baudrate and found[-1][1] == slave_id:
            # We already found this slave.
            continue

    client.close()


print("\n" + "=" * 50)

if found:
    print("SCAN COMPLETE - responses detected:\n")

    for baudrate, slave_id, address, value in found:
        print(
            f"Baud={baudrate}, "
            f"Slave={slave_id}, "
            f"Register={address}, "
            f"Value={value}"
        )

else:
    print("SCAN COMPLETE - no Modbus response detected.")