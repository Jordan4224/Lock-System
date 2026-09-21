"""
test_logic.py - automated tests for the state machine (no hardware, no input()).
Run: python3 test_logic.py
"""
from lock_state_machine import DeadboltStateMachine, LOCKED, UNLOCKED, PENDING_RELOCK


def make_sm():
    t = [0.0]
    events = []
    sm = DeadboltStateMachine(
        clock=lambda: t[0],
        on_retract=lambda: events.append("retract"),
        on_extend=lambda: events.append("extend"),
    )
    return sm, t, events


def test_starts_locked_stable():
    sm, t, ev = make_sm()
    sm.on_sensor_read(True)
    assert sm.state == LOCKED
    assert ev == []


def test_fob_retracts_immediately():
    sm, t, ev = make_sm()
    sm.on_fob_presented()
    assert sm.state == UNLOCKED
    assert ev == ["retract"]
    assert sm.last_recorded is False


def test_cooldown_blocks_reads_for_10s():
    sm, t, ev = make_sm()
    sm.on_fob_presented()
    sm.on_sensor_read(False)  # inside cooldown, ignored
    assert sm.state == UNLOCKED
    t[0] += 5
    sm.on_sensor_read(True)   # still inside cooldown (only 5s passed)
    assert sm.state == UNLOCKED
    t[0] += 6                 # now past 10s total
    sm.on_sensor_read(True)
    assert sm.state == PENDING_RELOCK


def test_relock_requires_two_true_10s_apart():
    sm, t, ev = make_sm()
    sm.on_fob_presented()
    t[0] += 10
    sm.on_sensor_read(True)          # first TRUE -> pending
    assert sm.state == PENDING_RELOCK
    sm.on_sensor_read(True)          # too soon, ignored
    assert sm.state == PENDING_RELOCK
    assert ev == ["retract"]
    t[0] += 10
    sm.on_sensor_read(True)          # confirmed
    assert sm.state == LOCKED
    assert ev == ["retract", "extend"]


def test_door_reopens_during_pending_cancels_relock():
    sm, t, ev = make_sm()
    sm.on_fob_presented()
    t[0] += 10
    sm.on_sensor_read(True)
    t[0] += 10
    sm.on_sensor_read(False)   # door reopened before confirm
    assert sm.state == UNLOCKED
    assert ev == ["retract"]  # never extended


def test_false_reads_while_unlocked_do_nothing():
    sm, t, ev = make_sm()
    sm.on_fob_presented()
    t[0] += 10
    for _ in range(5):
        sm.on_sensor_read(False)
    assert sm.state == UNLOCKED
    assert ev == ["retract"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn()
        print("PASS:", fn.__name__)
    print(f"\n{len(tests)} tests passed.")
