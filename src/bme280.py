# bme280.py - A simple MicroPython driver for the BME280 sensor.
# Adrien Abbey, Nov. 2025
#
# Assumes the use of the I2C interface
# 1. Reads the calibration registers
# 2. Configures the device
# 3. Reads the raw sensor data
# 4. Applies formulas as supplied by the data sheet
# 5. Returns human-readable temperatuure, humidity and pressure values.


from machine import I2C  # type: ignore


class BME280:
    def __init__(self, i2c: I2C, address: int = 0x76) -> None:
        self.i2c = i2c
        self.addr = address
