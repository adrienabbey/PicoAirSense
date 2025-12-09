# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Adrien Abbey
#
# PicoAirSense main application
#
# - Initializes I2C, BME280, and SGP30
# - Uses BME280 temperature/humidity to compensate SGP30 readings
# - Persists SGP30 IAQ baseline to internal flash
# - Exposes helper functions for REPL use

from machine import Pin, I2C  # type: ignore
import time
from bme280 import BME280
import adafruit_sgp30

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

SGP30_BASELINE_FILE = "sgp30_baseline.txt"
# Save the baseline file at most once per hour to limit flash wear:
SGP30_BASELINE_SAVE_INTERVAL = 3600  # seconds

# Globals for REPL access
i2c = None
bme = None
sgp = None
_last_baseline_save = 0.0


# -----------------------------------------------------------------------------
# Initialization Helpers
# -----------------------------------------------------------------------------

def init_i2c(sda_pin: int = 0, scl_pin: int = 1, freq: int = 100_000) -> I2C:
    """
    Initialize and return the I2C bus.
    """
    global i2c  # Allow changing the i2c variable

    # Initialize the I2C bus object:
    i2c = I2C(0, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=freq)

    return i2c


def scan_i2c() -> list[int]:
    """
    Scan the I2C bus and print a short report.
    """
    global i2c

    # Make sure the I2C bus has been initialized:
    if i2c is None:
        init_i2c()

    # Scan the I2C bus for connected devices:
    devices = i2c.scan()  # type: ignore
    print("I2C devices found:", [hex(d) for d in devices])

    # Verify that the expected sensors are detected:
    if 0x76 not in devices and 0x77 not in devices:
        print("Warning: BME280 address not detected on the bus.")
    if 0x58 not in devices:
        print("Warning: SGP30 address not detected on the bus.")

    return devices


def init_bme280(bus: I2C | None = None) -> BME280:
    """
    Initialize the BME280 and return the sensor object.
    """
    global bme, i2c

    if bus is None:
        if i2c is None:
            init_i2c()
        bus = i2c

    # NOTE: This is currently initializing with my class defaults, 'weather station'.
    bme = BME280(i2c=bus)  # type: ignore

    print("BME280 initialized successfully.")

    return bme


def init_sgp30(bus: I2C | None = None) -> adafruit_sgp30.Adafruit_SGP30:
    global sgp, i2c

    if bus is None:
        if i2c is None:
            init_i2c()
        bus = i2c

    sgp = adafruit_sgp30.Adafruit_SGP30(bus)

    print("SGP30 serial:", [hex(x) for x in sgp.serial])  # type: ignore

    return sgp


# -----------------------------------------------------------------------------
# Baseline persistence helpers
# -----------------------------------------------------------------------------


def load_sgp30_baseline() -> bool:
    """
    Try to restore SGP30 baselines from flash.

    Returns True on success, False if the file is missing or invalid.
    """
    global sgp

    # If the SGP is not initialize, throw an error.
    if sgp is None:
        raise RuntimeError("SGP30 is not initialized.")

    try:
        # Attempt to open the baseline file and read its contents:
        with open(SGP30_BASELINE_FILE, "r") as f:
            line = f.read().strip()
        if not line:
            print("Baseline file is empty; ignoring.")
            return False

        # Parse the baseline file:
        parts = line.split(",")
        if len(parts) != 2:
            print("Baseline file is malformed; ignoring.")
            return False

        co2eq = int(parts[0])
        tvoc = int(parts[1])

        # Apply the baseline to the SGP30:
        sgp.set_iaq_baseline(co2eq, tvoc)

        print("Restored SGP30 baseline from {}: eCO2={} TVOC={}".format(
            SGP30_BASELINE_FILE, co2eq, tvoc))

        return True

    except (OSError, RuntimeError) as error_code:
        # No file yet, or filesystem issue:
        print("No usable SGP30 baseline found; starting with factory baseline.", error_code)
        return False

    except ValueError:
        print("Could not parse SGP30 baseline file; ignoring.")
        return False


def save_sgp30_baseline() -> None:
    """
    Read the current SGP30 baselines and store them to flash.

    This function can be called from the REPL once the IAQ algorithm has stabilized.
    """
    global sgp, _last_baseline_save

    if sgp is None:
        raise RuntimeError("SGP30 is not initialized.")

    # Load the current baselines from the SGP30:
    co2eq, tvoc = sgp.get_iaq_baseline()  # type: ignore

    # Write the new baselines to flash:
    with open(SGP30_BASELINE_FILE, "w") as f:
        f.write("{},{}\n".format(co2eq, tvoc))

    # Update the last baseline file save time:
    _last_baseline_save = time.time()

    print("Saved SGP30 baseline to {}: eCO2={} TVOC={}".format(
        SGP30_BASELINE_FILE, co2eq, tvoc))


def maybe_save_sgp30_baseline() -> None:
    """
    Periodically save the SGP30 baseline based on SGP30_BASELINE_SAVE_INTERVAL.
    """
    global _last_baseline_save
    now = time.time()

    # Initialize the timestamp if needed:
    if _last_baseline_save == 0:
        _last_baseline_save = now
        return

    # Check if it's time to update the baseline:
    if now - _last_baseline_save >= SGP30_BASELINE_SAVE_INTERVAL:
        try:
            save_sgp30_baseline()
        except OSError as error_code:
            print("Warning: could not save SGP30 baseline:", error_code)


# -----------------------------------------------------------------------------
# Measurement helpers (for REPL and main loop)
# -----------------------------------------------------------------------------


def read_environment() -> tuple[float, float, float, int, int]:
    """
    Take a single measurement from both sensors, with compensation.

    :return: (temperature_C, pressure_Pa, humidity_percent, eCO2_ppm, tvoc_ppb)
    :rtype: tuple[float, float, float, int, int]
    """
    global bme, sgp

    if bme is None or sgp is None:
        raise RuntimeError("Sensors are not initialized; call main() first.")

    # Read the BME280 first:
    temperature_c, pressure_pa, humidity_percent = bme.read()

    # Use the temp/RH to compensate the SGP30 readings:
    sgp.set_iaq_rel_humidity(humidity_percent, temperature_c)
    eco2, tvoc = sgp.iaq_measure()  # type: ignore

    return temperature_c, pressure_pa, humidity_percent, eco2, tvoc


def print_environment() -> None:
    """
    Read once and print a formatted line.
    """

    # Grab the sensor values:
    temperature_c, pressure_pa, humidity_percent, eco2, tvoc = read_environment()
    pressure_hpa = pressure_pa / 100.0

    # Print the formatted sensor values.  NOTE: This will go to the REPL terminal:
    print("T = {:6.2f} C   P = {:7.2f} hPa   H = {:5.1f} %RH   eCO2 = {:4d} ppm   TVOC = {:4d} ppb".format(
        temperature_c, pressure_hpa, humidity_percent, eco2, tvoc))


def run_continuous() -> None:
    """
    Continuous measurement loop.

    Prints readings every 1 second and periodically saves the SGP30
    IAQ baseline to flash.  Press Ctrl+C to stop and return to the REPL.
    """
    print("Starting a continuous measurement loop.  Press Ctrl+C to stop.")

    # Loop continuously:
    while True:
        try:
            print_environment()
            maybe_save_sgp30_baseline()
        except Exception as error_code:
            print("Sensor read failed:", error_code)
        time.sleep(1)  # Sleep 1 second.


# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------


def main(loop: bool = True) -> None:
    """
    Initialize sensors and optionally start a continuous measurement loop.

    :param loop: If True, start run_continuous().  If false, only initialize and
        take a few initial readings so you can use the REPL.
    :type loop: bool
    """

    # Initialize the I2C bus and its sensors:
    init_i2c()
    scan_i2c()
    init_bme280()
    init_sgp30()

    # Try restoring a stored baseline.  If none is available, do a short warm-up:
    baseline_loaded = load_sgp30_baseline()

    if not baseline_loaded:
        print("Performing a short SGP30 warm-up (15 s)...")
        for i in range(15):
            print("  Warm-up {:2d}/15".format(i+1), end="  ")
            print_environment()
            time.sleep(1)
        print("Warm-up complete.  The IAQ algorithm will continue to refine over time.")
    else:
        print("Baseline restored; taking a few initial compensated readings.")
        for _ in range(5):
            print_environment()
            time.sleep(1)

    if loop:
        run_continuous()
    else:
        print("Initialization complete.\n"
              "Use print_environment() or read_environment() from the REPL,\n"
              "or call run_continuous() to start running."
              )


if __name__ == "__main__":
    # On power-up / reset, initialize and start continuous measurements.
    # From the REPL, you can instead do: import main; main.main(loop=False)
    main(loop=True)
