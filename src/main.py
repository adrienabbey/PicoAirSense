# Simple test harness to verify my bme280.py library works.
# From ChatGPT.  I am NOT intending to keep this code!

from machine import Pin, I2C, SPI  # type: ignore
import time
import framebuf # type: ignore
from bme280 import BME280
import adafruit_sgp30
import epaper2in13


def init_i2c():
    return I2C(0, sda=Pin(0), scl=Pin(1), freq=100_000)


def init_bme280(i2c):
    sensor = BME280(i2c=i2c)
    print("BME280 initialized successfully.")
    return sensor


def init_sgp30(i2c):
    sgp = adafruit_sgp30.Adafruit_SGP30(i2c)
    print("SGP30 object created, running iaq_init()...")
    sgp.iaq_init()

    print("SGP30 short warm-up (15 s)...")
    for _ in range(15):
        sgp.iaq_measure()
        time.sleep(1)

    print("SGP30 initialized successfully.")

    return sgp


def init_epd():
    spi = SPI(1, baudrate=2_000_000, polarity=0, phase=0,
              sck=Pin(10), mosi=Pin(11), miso=None)

    cs = Pin(9)
    dc = Pin(8)
    rst = Pin(12)
    busy = Pin(13)

    epd = epaper2in13.EPD(spi, cs, dc, rst, busy)
    epd.init()

    buf = bytearray(epd.width * epd.height // 8)
    fb = framebuf.FrameBuffer(buf, epd.height, epd.width, framebuf.MONO_VLSB)

    return epd, fb, buf


def main():
    epd, fb, buf = init_epd()
    fb.fill(0)
    y = 6
    fb.text("PicoAirSense", 2, y, 0xFFFF)
    y += 14
    fb.text("Hello, world!", 2, y, 0xFFFF)

    epd.set_frame_memory(buf, 0, 0, epd.width, epd.height)
    epd.display_frame()

    i2c = init_i2c()

    devices = i2c.scan()
    print("I2C devices found:", [hex(d) for d in devices])

    if 0x76 not in devices and 0x77 not in devices:
        print("Warning: BME280 address not detected on the bus.")
    if 0x58 not in devices:
        print("Warning: SGP30 address not detected on the bus.")

    bme = init_bme280(i2c)
    sgp = init_sgp30(i2c)

    while True:
        try:
            temperature_c, pressure_Pa, humidity_percent = bme.read()
            eco2, tvoc = sgp.iaq_measure()  # type: ignore
        except Exception as e:
            print("Sensor read failed:", e)
        else:
            pressure_hPa = pressure_Pa / 100.0

            print("T = {:6.2f} C   P = {:7.2f} hPa   H = {:5.1f} %RH   eCO2 = {:4d} ppm   TVOC = {:4d} ppb".format(
                temperature_c, pressure_hPa, humidity_percent, eco2, tvoc))

        time.sleep(1)


if __name__ == "__main__":
    main()
