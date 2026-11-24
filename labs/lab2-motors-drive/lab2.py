import argparse
import time
import busio
from board import SCL, SDA
from adafruit_pca9685 import PCA9685
import numpy as np

parser = argparse.ArgumentParser(description="Motor testing script!")
parser.add_argument('-e', '--esc', type=int, default=8, help='ESC channel (default: 1)')
parser.add_argument('-s', '--servo', type=int, default=14, help='Servo channel (default: 0)')
parser.add_argument('-i', '--initialize', type=int, default=0, help='Is the motor running for the first time since being switched on? (default: 0)')
parser.add_argument('--extra_option', type=str, default="", help='Message to explain the option (default: empty string)')  # Template for additional arguments
args = parser.parse_args()
ESC_CHANNEL = args.esc
SERVO_CHANNEL = args.servo
# If the motor is running for the first time since being switched on, the ESC needs to be "armed" (meaning that we need to send a neutral signal for 2 seconds)
arm_ESC = args.initialize
extra_argument = args.extra_option

# Constants (pulse widths in microseconds)
FREQ = 60
NEUTRAL = 1500
MAX = 1900
MIN = 1200
SERVO_MIN = 1150   # keep servo within 1.15 - 1.85 ms (slide 43)
SERVO_MAX = 1850

# Setup I2C bus and PCA9685
i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c)
pca.frequency = FREQ


def pulse_to_duty(pulse_us):
    """Convert a pulse width in microseconds to the library's 16-bit duty cycle (0 - 0xFFFF)."""
    period_us = 1_000_000 / FREQ            # 16,667 us at 60 Hz
    return int((pulse_us / period_us) * 0xFFFF)


def set_esc(pulse_us):
    """Send a pulse to the ESC, clamped to NEUTRAL..MAX (forward only)."""
    pulse_us = int(np.clip(pulse_us, NEUTRAL, MAX))
    pca.channels[ESC_CHANNEL].duty_cycle = pulse_to_duty(pulse_us)


def set_servo(pulse_us):
    """Send a pulse to the servo, clamped to the safe steering range."""
    pulse_us = int(np.clip(pulse_us, SERVO_MIN, SERVO_MAX))
    pca.channels[SERVO_CHANNEL].duty_cycle = pulse_to_duty(pulse_us)


# Test
try:
    # Arm the ESC: neutral signal for 2 seconds
    if arm_ESC:
        print("Arming ESC...")
        set_esc(NEUTRAL)
        time.sleep(2)

    # Center the servo and hold the ESC at neutral
    set_servo(NEUTRAL)
    set_esc(NEUTRAL)
    time.sleep(1)

    # Steering sweep: left, right, center
    print("Steering test...")
    set_servo(SERVO_MIN)
    time.sleep(1)
    set_servo(SERVO_MAX)
    time.sleep(1)
    set_servo(NEUTRAL)
    time.sleep(1)

    # Throttle test: step up slowly, with the wheels off the ground
    print("Throttle test...")
    for pulse in (1550, 1600, 1650):
        set_esc(pulse)
        time.sleep(2)

    # Stop
    set_esc(NEUTRAL)
    time.sleep(1)

finally:
    # Always return to neutral and release the PCA board, even on Ctrl+C or an error
    set_esc(NEUTRAL)
    set_servo(NEUTRAL)
    time.sleep(0.5)
    pca.deinit()
