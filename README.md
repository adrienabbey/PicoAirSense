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
