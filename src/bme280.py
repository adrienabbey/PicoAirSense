# bme280.py - A simple MicroPython driver for the BME280 sensor.
# Adrien Abbey, Nov. 2025
#
# NOTE: Much of this is based on guidance from ChatGPT.  No code was copy/pasted, and all work
#   is done while being mindful of staying within academic integrity standards.
#
# Assumes the use of the I2C interface
# 1. Reads the calibration registers
# 2. Configures the device
#   - NOTE: This has 'weather station' defaults.  The user can specify these.
# 3. Reads the raw sensor data
# 4. Applies formulas as supplied by the data sheet
# 5. Returns human-readable temperature, humidity and pressure values.
#
# Most of this data comes from the official Bosch BME280 data sheet:
#   https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme280-ds002.pdf
#
# Control Registers:
#   ID          0xD0    Chip ID             Should return 0x60 for BME280
#   RESET       0xE0    Soft Reset          Write 0xB6 to initiate a full reset
#   CTRL_HUM    0xF2    Humidity Control    Controls oversampling for humidity.
#                                           Must be written before CTRL_MEAS to take effect.
#                                           '001' for oversampling x1
#   STATUS      0xF3    Status              Bit 3 (measuring) is '1' when conversion is running.
#                                           Bit 0 (im_update) is '1'f when NVM memory is copying.
#   CTRL_MEAS   0xF4    Measurement Control Controls pressure/temp oversampling and power mode.
#                                           '00100101' for temp x1, press x1, forced mode
#   CONFIG      0xF5    Configuration       Controls standby time (in Normal mode) and IIR filter
#                                           settings.  '11100000' for filter off
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
#   NOTE: If I'm using x1 oversampling with IIR filtering off, while my data is effectively 16-bit
#       (the XLSB bits have little value), I still need to treat it as a 20-bit value.
#
# Weather Monitoring Recommendations:
#   Sensor mode: forced mode, 1 sample / minute
#   Oversampling settings: pressure x1, temperature x1, humidity x1
#   IIR filter settings: filter off
#   NOTE: This is quite fine for my intended purposes.
#
# Compensation formulas:
#   This information can be found starting on page 25 of the official Bosch BME280 data sheet.
#   Trimming parameter registers for calibration are available on page 24.
#
# Bitwise functionality:
#   (e4 << 4) : This will do a bit-shift of e4 4-bits left.
#   (e5 & 0x0F) : Bitwise AND.  This will set the first four bits of e5 to zero.  0x0F = '0000 1111'
#   (e4 << 4) | (e5 & 0x0F) : This will bitwise OR the above two into a single 12-bit value.
#   if value & 0x800 : This will do a bitwise AND between the given value and the hex value 0x800
#       This translates to '1000 0000 0000' in binary.  In other words, if the 12th bit is 1,
#       this will return True (non-zero value).


from machine import I2C  # type: ignore


class BME280:

    # Define the addresses for the configuration values to be written to:
    CTRL_HUM = 0xF2
    CTRL_MEAS = 0xF4
    CONFIG = 0xF5

    def __init__(self, i2c: I2C, address: int = 0x76, spi3w_en: int = 0,
                 osrs_t: int = 0b001, osrs_p: int = 0b001, osrs_h: int = 0b001,
                 filter_coef: int = 0b000, t_sb: int = 0b000, mode: int = 0b00) -> None:
        self.i2c = i2c
        self.address = address          # Note: this is 0x76 by default for the BME280 sensor
        self.spi3w_en = spi3w_en        # If enabled, use 3-wire SPI, otherwise use I2C
        # Temperature oversampling value (0, x1, x2, x4, x8, x16):
        self.osrs_t = osrs_t
        # Pressure oversampling value (0, x1, x2, x4, x8, x16):
        self.osrs_p = osrs_p
        # Humidity oversampling value (0, x1, x2, x4, x8, x16):
        self.osrs_h = osrs_h
        # IIR filter coefficient (0, 2, 4, 8, 16):
        self.filter_coef = filter_coef
        self.t_sb = t_sb                # Standby time (for normal mode)
        self.mode = mode                # Mode (sleep, forced, normal)

        # Verify the chip ID
        chip_id = self._read_u8(0xD0)
        if chip_id not in (0x60,):
            raise RuntimeError(
                "The BME280 was not found, or wrong chip ID was given: 0x{:02X}".format(chip_id))

        # Read calibration data:
        self._read_calibration_data()

        # Configure oversampling / mode registers
        self._configure()

    def _read_u8(self, reg):
        """
        Reads one unsigned 8-bit value from the specified device register.

        :param reg: The register address on the device to read from.
        """
        return int.from_bytes(self.i2c.readfrom_mem(self.address, reg, 1), "big")

    def _read_s16(self, reg):
        data = self.i2c.readfrom_mem(self.address, reg, 2)
        val = int.from_bytes(data, "little", signed=True)
        return val

    def _read_calibration_data(self) -> None:
        # TODO: implement according to BME280 data sheet
        # Read blocks of registers into attributes like self.dig_T1, dig_T2, ...

        # From the official BME280 data sheet:
        #   0x88 / 0x89         dig_T1 [7:0] / [15:8]   unsigned short
        #   0x8A / 0x8B         dig_T2 [7:0] / [15:8]   signed short
        #   0x8C / 0x8D         dig_T3 [7:0] / [15:8]   signed short
        #   0x8E / 0x8F         dig_P1 [7:0] / [15:8]   unsigned short
        #   0x90 / 0x91         dig_P2 [7:0] / [15:8]   signed short
        #   0x92 / 0x93         dig_P3 [7:0] / [15:8]   signed short
        #   0x94 / 0x95         dig_P4 [7:0] / [15:8]   signed short
        #   0x96 / 0x97         dig_P5 [7:0] / [15:8]   signed short
        #   0x98 / 0x99         dig_P6 [7:0] / [15:8]   signed short
        #   0x9A / 0x9B         dig_P7 [7:0] / [15:8]   signed short
        #   0x9C / 0x9D         dig_P8 [7:0] / [15:8]   signed short
        #   0x9E / 0x9F         dig_P9 [7:0] / [15:8]   signed short
        #   0xA1                dig_H1 [7:0]            unsigned char
        #   0xE1 / 0xE2         dig_H2 [7:0] / [15:8]   signed short
        #   0xE3                dig_H3 [7:0]            unsigned char
        #   0xE4 / 0xE5[3:0]    dig_H4 [11:4] / [3:0]   signed short
        #   0xE5[7:4] / 0xE6    dig_H5 [3:0] / [11:4]   signed short
        #   0xE7                dig_H6                  signed char

        # Read the temperature and pressure calibration values in a large block:
        tp_buf = self.i2c.readfrom_mem(self.address, 0x88, 26)
        # buf1[0] = 0x88, buf1[1] = 0x89, ... buf1[23] = 0x9F

        # Temperature values:
        self.dig_T1 = self._u16_le(tp_buf[0], tp_buf[1])    # unsigned  short
        self.dig_T2 = self._s16_le(tp_buf[2], tp_buf[3])    # signed    short
        self.dig_T3 = self._s16_le(tp_buf[4], tp_buf[5])    # signed    short

        # Pressure values:
        self.dig_P1 = self._u16_le(tp_buf[6], tp_buf[7])    # unsigned  short
        self.dig_P2 = self._s16_le(tp_buf[8], tp_buf[9])    # signed    short
        self.dig_P3 = self._s16_le(tp_buf[10], tp_buf[11])  # signed    short
        self.dig_P4 = self._s16_le(tp_buf[12], tp_buf[13])  # signed    short
        self.dig_P5 = self._s16_le(tp_buf[14], tp_buf[15])  # signed    short
        self.dig_P6 = self._s16_le(tp_buf[16], tp_buf[17])  # signed    short
        self.dig_P7 = self._s16_le(tp_buf[18], tp_buf[19])  # signed    short
        self.dig_P8 = self._s16_le(tp_buf[20], tp_buf[21])  # signed    short
        self.dig_P9 = self._s16_le(tp_buf[22], tp_buf[23])  # signed    short

        # Humidity values (incomplete):
        self.dig_H1 = tp_buf[25]                            # unsigned  char

        # Humidity calibration gets complicated, as some values are packed.
        # Read the humidity calibration values in a large block:
        h_buf = self.i2c.readfrom_mem(self.address, 0xE1, 7)
        # buf2[0] = 0xE1, ..., buf2[6] = 0xE7

        # Humidity values (easy):
        self.dig_H2 = self._s16_le(h_buf[0], h_buf[1])      # signed    short
        self.dig_H3 = h_buf[2]                              # unsigned  char

        # The following values require some assembly:
        e4 = h_buf[3]   # 0xE4
        e5 = h_buf[4]   # 0xE5
        e6 = h_buf[5]   # 0xE6

        # Shift 0xE4 left 4 bits [11:4] with E5[3:0] before combining:
        raw_h4 = (e4 << 4) | (e5 & 0x0F)
        # Sign-extend the 12-bit signed to a Python int:
        if raw_h4 & 0x800:  # If the 12th bit is 1:
            raw_h4 -= 1 << 12
        self.dig_H4 = raw_h4                                # signed    short

        # Shift 0xE6 left 4 bits and 0xE5 left 4 bits before combining:
        raw_h5 = (e6 << 4) | (e5 >> 4)
        # Sign-extend the 12-bit signed into a Python int:
        if raw_h5 & 0x800:  # If the 12th bit is 1:
            raw_h5 -= 1 << 12
        self.dig_H5 = raw_h5                                # signed    short

        # Finally, H6 needs to assembly:
        self.dig_H6 = self._s8(h_buf[6])                    # signed    char

    ###
    # These helper functions are necessary to convert raw register values into usable integers.
    #   @staticmethod allows for the helper functions to avoid needing to use 'self', as they don't
    #       modify any instance attributes.
    ###

    @staticmethod
    def _u16_le(low: int, high: int) -> int:
        """
        Combine two bytes (little-endian) into an unsigned 16-bit int.
        """
        return low | (high << 8)  # Bit-shifts the high value and then combines the two values.

    @staticmethod
    def _s16_le(low: int, high: int) -> int:
        """
        Combine two bytes into a signed 16-bit int (two's complement).
        """
        value = low | (high << 8)
        if value & 0x8000:  # check the sign bit
            value -= 0x100000
        return value

    @staticmethod
    def _s8(b: int) -> int:
        """
        Interpret one byte as a signed 8-bit value.
        """
        return b - 0x100 if b & 0x80 else b  # Sign if needed

    def _configure(self):
        """
        Configures the device according to provided values.  This includes the sensor mode, 
        oversampling, standby time (normal mode only), IIR filter coefficient, and I2C / 3-wire SPI
        interfaces.
        """

        # NOTE: Humidity oversampling changes only take effect after writing to 'ctrl_meas'
        # NOTE: Writes to 'config' may be ignored in normal mode, guaranteed in sleep mode

        # ctrl_hum: 0xF2
        #   This controls oversampling of humidity data.  See below for values.
        # ctrl_meas: 0xF4
        #   This controls oversampling of temperature and pressure data, as well as sensor mode.
        #       Bit 7, 6, 5:    osrs_t[2:0]
        #       Bit 4, 3, 2:    osrs_p[2:0]
        #       Bit 1, 0:       mode[1:0]
        #   osrs_h[2:0], osrs_p[2:0], osrs_t[2:0]
        #       000             skipped (output set to 0x8000)      No measurement taken
        #       001             oversampling x 1                    Single measurement
        #       010             oversampling x 2                    2 measurements per value
        #       011             oversampling x 4                    4 measurements per value, etc
        #       100             oversampling x 8                    More sampling/processing
        #       101, others     oversampling x 16                   Less jitter, more accurate
        #   mode[1:0]
        #       00              Sleep mode                          Default, no measurements
        #       01 and 10       Forced mode                         Do one measure cycle, then sleep
        #       11              Normal mode                         Measure repeatedly, see config
        # config: 0xF5
        #   This configures standby time, IIR filter constant, and 3-wire SPI interface
        #       Bit 7, 6, 5     t_sb[2:0]       Configures delay between normal mode samples
        #       Bit 4, 3, 2     filter[2:0]
        #       Bit 0           spi3w_en[0]     If enabled [1], disables I2C and enables 3-wire SPI
        #   t_sb[2:0]       t_standby[ms]
        #       000                0.5
        #       001               62.5
        #       010              125
        #       011              250
        #       100              500
        #       101             1000
        #       110               10
        #       111               20
        #   filter[2:0]     Filter coefficient      The IIR filter is a digital low-pass filter.
        #       000             Filter off              This reduces short-term noise and jitter.
        #       001                 2                   Affects temperature and pressure ONLY.
        #       010                 4                   Higher filter values smooths outputs more,
        #       011                 8                   based on previous measurements.
        #       100, others        16

        # Configure the humidity oversampling (ctrl_hum) first:
        ctrl_hum = self.osrs_h & 0x07   # bits 2:0
        self.i2c.writeto_mem(self.address, self.CTRL_HUM, bytes([ctrl_hum]))

        # Configure standby time, IIR filtering, and SPI/I2C next:
        config = ((self.t_sb & 0x07) << 5) | (
            (self.filter_coef & 0x07) << 2) | self.spi3w_en  # See comments above
        self.i2c.writeto_mem(self.address, self.CONFIG, bytes([config]))

        # Finally, configure temp/press oversampling and sensor mode:
        ctrl_meas = ((self.osrs_t & 0x07) << 5) | (
            (self.osrs_p & 0x07) << 2) | (self.mode & 0x03)  # See comments above
        self.i2c.writeto_mem(self.address, self.CTRL_MEAS, bytes([ctrl_meas]))

    def read_raw(self):
        # TODO: read raw temperature, pressure, humidity registers
        # Return (adc_T, adc_P, adc_H)
        # NOTE: Be mindful of whether this is in forced or normal mode!
        pass

    def read(self):
        """
        Returns (temperature_C, pressure_Pa, humidity_percent)
        """
        adc_T, adc_P, adc_H = self.read_raw()
        # TODO: apply compensation formulas from data sheet
        # Use self.dig_T1, dig_T2, ... to compute true readings
        return (temperature_C, pressure_Pa, humidity_percent)
