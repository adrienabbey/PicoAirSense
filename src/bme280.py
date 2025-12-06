# bme280.py - A simple MicroPython driver for the BME280 sensor.
# Adrien Abbey, Nov. 2025
#
# Assumes the use of the I2C interface
# 1. Reads the calibration registers
# 2. Configures the device
# 3. Reads the raw sensor data
# 4. Applies formulas as supplied by the data sheet
# 5. Returns human-readable temperature, humidity and pressure values.
#
# Control Registers:
#   ID          0xD0    Chip ID             Should return 0x60 for BME280
#   RESET       0xE0    Soft Reset          Write 0xB6 to initiate a full reset
#   CTRL_HUM    0xF2    Humidity Control    Controls oversampling for humidity.
#                                           Must be written before CTRL_MEAS to take effect.
#   STATUS      0xF3    Status              Bit 3 (measuring) is '1' when conversion is running.
#                                           Bit 0 (im_update) is '1'f when NVM memory is copying.
#   CTRL_MEAS   0xF4    Measurement Control Controls pressure/temp oversampling and power mode.
#                                           (Sleep=00, Forced=01, Normal=11)
#   CONFIG      0xF5    Configuration       Controls standby time (in Normal mode) and IIR filter
#                                           settings.
#
# Data Registers:
#   NOTE: It's recommended to perform a burst read of all registers (0xF7 to 0xFE) in one operation
#       to ensure these values all belong to the same measurement instance.
#
#   Pressure: 0xF7 (MSB), 0xF8 (LSB), 0xF9 (XLSB - bits 7:4)
#   Temperature: 0xFA (MSB), 0xFB (LSB), 0xFC (XLSB - bits 7:4)
#   Humidity: 0xFD (MSB), 0xFE (LSB)
#
#   NOTE: XLSB: Extended Least-Significant Byte.  Standard registers are 8-bits, but the sensors
#       provide 20-bits of precision.  Thus this extends an additional 4-bits into the the XLSB
#       registers (bits 7:4).


from machine import I2C  # type: ignore


class BME280:
    def __init__(self, i2c: I2C, address: int = 0x76) -> None:
        self.i2c = i2c
        self.addr = address  # Note: this is 0x76 by default for the BME280 sensor
