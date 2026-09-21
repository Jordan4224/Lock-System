"""
main.py - runs ON the Raspberry Pi Pico (MicroPython)

Wires real GPIO to the hardware-agnostic DeadboltStateMachine in
lock_state_machine.py. Copy both files onto the Pico (e.g. with
Thonny: File > Save As > Raspberry Pi Pico). main.py runs
automatically on boot; lock_state_machine.py just needs to sit
alongside it in the Pico's filesystem.
"""

import time
from machine import Pin, PWM
from lock_state_machine import DeadboltStateMachine

# ---- pin config: CHANGE THESE to match your actual wiring -------------
LIGHT_SENSOR_PIN = 16   # digital in from photo-interrupter / reflective sensor
FOB_RECEIVER_PIN = 17   # digital in, pulses HIGH when RFID receiver validates a fob
STEP_PIN = 2            # -> stepper driver STEP input
DIR_PIN = 3             # -> stepper driver DIR input
ENABLE_PIN = 4          # -> stepper driver EN input (many boards are active-LOW)

STEPS_PER_MOVE = 200    # tune to your motor + gearing + deadbolt throw
STEP_PWM_FREQ = 800     # Hz; tune to the torque/speed your motor can handle

light_sensor = Pin(LIGHT_SENSOR_PIN, Pin.IN, Pin.PULL_DOWN)
fob_pin = Pin(FOB_RECEIVER_PIN, Pin.IN, Pin.PULL_DOWN)
step_pin = Pin(STEP_PIN, Pin.OUT)
dir_pin = Pin(DIR_PIN, Pin.OUT)
enable_pin = Pin(ENABLE_PIN, Pin.OUT)
enable_pin.value(0)  # enable the driver (flip to 1 if yours is active-high)

_fob_flag = False


def _fob_irq(pin):
    # Keep ISR tiny: just set a flag, handle it in the main loop.
    global _fob_flag
    _fob_flag = True


fob_pin.irq(trigger=Pin.IRQ_RISING, handler=_fob_irq)


def _step(n, direction):
    """Drive STEP_PIN with a PWM burst of n pulses at STEP_PWM_FREQ."""
    dir_pin.value(direction)
    pwm = PWM(step_pin)
    pwm.freq(STEP_PWM_FREQ)
    pwm.duty_u16(32768)  # 50% duty square wave = step pulses
    time.sleep(n / STEP_PWM_FREQ)
    pwm.deinit()
    step_pin.value(0)


def retract_deadbolt():
    print("[motor] retracting")
    _step(STEPS_PER_MOVE, direction=0)


def extend_deadbolt():
    print("[motor] extending")
    _step(STEPS_PER_MOVE, direction=1)


def ticks_clock():
    return time.ticks_ms() / 1000.0


sm = DeadboltStateMachine(
    clock=ticks_clock,
    on_retract=retract_deadbolt,
    on_extend=extend_deadbolt,
)

print("Deadbolt controller running. state =", sm.state)

while True:
    if _fob_flag:
        _fob_flag = False
        print("[fob] valid fob detected")
        sm.on_fob_presented()

    reading = bool(light_sensor.value())
    sm.on_sensor_read(reading)

    time.sleep(0.1)  # ~10Hz poll: fast enough for 10s windows, easy on the CPU
