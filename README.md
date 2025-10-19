# PicoAirSense

RasPi Pico-based Indoor Environment Monitor

## The Goal

- Monitor indoor air quality, humidity, temperature, and pressure.
- Develop skills and experience working with microcontrollers.
  - Use Fritzing to create wiring schematics.
- Use a Raspberry Pi Pico 2W, an E-Ink display, and several sensors to do this.

## Hardware

- Raspberry Pi Pico 2W Microcontroller
- BME280 Environmental Sensor (Temperature, Humidity, Barometric Pressure) [I2C]
- SGP30 Air Quality Sensor (VOC + eCO2) [I2C]
- waveshare 2.13 inch E-Ink display [SPI]

### Wiring

- The BME280 and SGP30 will share the same I2C wiring:
  - `Pico pin 36` (VCC 3.3V) -> both sensors' VCC (RED cable)
  - `Pico pin 38` (GND) -> both sensors' GND (BLK cable)
  - `Pico pin 1` (I2C0 SDA) -> both sensors' SDA (GRN cable)
  - `Pico pin 2` (I2C0 SCL) -> both sensors' SCL (YEL cable)

## Software

- MicroPython for the various programs and libraries
  - While C/C++ is a viable alternative, I want to start simple and expand from there.
  - The SGP30 driver for C requires some additional steps to get working well on the Pico 2W.
  - While Wi-Fi is better supported by C/C++, the MicroPython implementation should be sufficient if I decide to use it to push sensor data wirelessly.
  - Thonny will be used to verify that the Pico is able to communicate with the sensors.

### Software Setup & Testing

After connecting the sensors to the Raspberry Pi Pico 2W, test the wiring by doing the following:

- First grab the appropriate MicroPython `.uf2` file for the Pico 2W from [the official MicroPython website](https://micropython.org/download/RPI_PICO2_W/).
- Unplug the Pico from your PC, hold the `BOOTSEL` button on the Pico, then plug it back in.  This will appear as a removable drive.
- Copy the file downloaded above to this removable drive.  It will automatically unmount and reboot the Pico once done.
- Launch Thonny.  Go to `Tools -> Options -> Interpreter` and configure it to `MicroPython (Raspberry Pi Pico)`.  I was able to let it autodetect which port to use.
- If necessary, click `Stop/Start Backend` to open the MicroPython interpreter interface on the Pico.
- In this new terminal window, paste the following code:

```python
from machine import Pin, I2C
i2c = I2C(0, scl=Pin(1), sda=Pin(0))
print(i2c.scan())
```

- If you get the following output, your Pico and the two sensors are correctly configured:

```text
[88, 118]
```
