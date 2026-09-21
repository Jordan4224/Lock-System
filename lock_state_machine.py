"""
lock_state_machine.py
Hardware-agnostic deadbolt state machine.

This module makes NO GPIO/PWM calls, so it can be unit-tested on a
laptop before anything touches the Pico. main.py wires this logic to
real pins.

State machine summary (from the project spec):
- LOCKED:  deadbolt extended. Light sensor should keep reading TRUE
           (reflective plate visible / door closed). Nothing happens
           while it keeps reading TRUE.
- On fob presented: deadbolt retracts immediately, state -> UNLOCKED,
           last_recorded = FALSE, and a 10s cooldown starts before the
           next sensor read is even taken.
- UNLOCKED: if sensor reads FALSE, nothing happens (door still open).
           If sensor reads TRUE (door swung closed onto the plate),
           it's not trusted instantly -- wait 10s and re-check.
- PENDING_RELOCK: if, 10s later, the sensor STILL reads TRUE, extend
           the deadbolt and go back to LOCKED. If it reads FALSE
           instead, the door reopened -- go back to UNLOCKED and wait
           again.

Timing uses a monotonic clock function passed in (instead of
time.sleep()), because sleep() would block the Pico's main loop and
it would miss fob reads during the 10s windows. Tests can fake the
clock; main.py feeds it a function based on time.ticks_ms().
"""

import time

LOCKED = "LOCKED"
UNLOCKED = "UNLOCKED"
PENDING_RELOCK = "PENDING_RELOCK"

RELOCK_CONFIRM_DELAY_S = 10
POST_UNLOCK_COOLDOWN_S = 10


class DeadboltStateMachine:
    def __init__(self, clock=time.monotonic, on_retract=None, on_extend=None):
        """
        clock:      function returning current time in seconds (float).
        on_retract: callback fired when the deadbolt should retract.
        on_extend:  callback fired when the deadbolt should extend.
        """
        self._clock = clock
        self._on_retract = on_retract or (lambda: None)
        self._on_extend = on_extend or (lambda: None)

        self.state = LOCKED
        self.last_recorded = True          # door starts closed
        self._next_read_allowed_at = 0.0   # cooldown gate after unlock
        self._pending_since = None         # when the first TRUE was seen post-unlock

    # ---- public API, call every loop tick from main.py -------------------

    def on_fob_presented(self):
        """Call the instant the Pico receives a valid fob signal."""
        now = self._clock()
        self._on_retract()
        self.state = UNLOCKED
        self.last_recorded = False
        self._pending_since = None
        self._next_read_allowed_at = now + POST_UNLOCK_COOLDOWN_S

    def on_sensor_read(self, value: bool):
        """
        Call every loop tick with the current light-sensor reading.
        The state machine decides internally whether a reading is
        actually "due" yet (cooldown / confirm-delay windows).
        """
        now = self._clock()

        if self.state == LOCKED:
            # Baseline case: TRUE matches TRUE -> do nothing.
            # A FALSE here with no preceding fob event means the door
            # was opened/forced without a fob -- see README "tamper case".
            self.last_recorded = value
            return

        if self.state == UNLOCKED:
            if now < self._next_read_allowed_at:
                return  # still inside the 10s post-unlock cooldown
            if value is False:
                self.last_recorded = False
                return  # door still open, remain retracted
            # value is True: plate seen, but don't trust it yet
            self.state = PENDING_RELOCK
            self._pending_since = now
            return

        if self.state == PENDING_RELOCK:
            if now - self._pending_since < RELOCK_CONFIRM_DELAY_S:
                return  # still waiting out the 10s confirm window
            if value is True:
                self._on_extend()
                self.state = LOCKED
                self.last_recorded = True
            else:
                # door reopened during the confirm window
                self.state = UNLOCKED
                self.last_recorded = False
                self._next_read_allowed_at = now  # re-check immediately
            self._pending_since = None
            return
