"""
test_desktop_sim.py
Run this on your laptop (plain CPython, no Pico needed) to interactively
poke at the state machine before wiring any hardware.

Usage:
    python3 test_desktop_sim.py

Commands while running:
    t   -> simulate light sensor reading TRUE  (door closed / plate seen)
    f   -> simulate light sensor reading FALSE (door open)
    b   -> simulate a fob badge presented
    a   -> advance the fake clock by 10s (so you don't wait for real)
    q   -> quit
"""

from lock_state_machine import DeadboltStateMachine

fake_time = [0.0]


def clock():
    return fake_time[0]


def on_retract():
    print(">>> MOTOR: retract (deadbolt open)")


def on_extend():
    print(">>> MOTOR: extend (deadbolt locked)")


def main():
    sm = DeadboltStateMachine(clock=clock, on_retract=on_retract, on_extend=on_extend)
    print("Start state:", sm.state)
    print("Commands: t=sensor TRUE, f=sensor FALSE, b=fob, a=advance clock 10s, q=quit\n")

    while True:
        cmd = input(f"[t={fake_time[0]:.0f}s state={sm.state}] > ").strip().lower()
        if cmd == "q":
            break
        elif cmd == "t":
            sm.on_sensor_read(True)
        elif cmd == "f":
            sm.on_sensor_read(False)
        elif cmd == "b":
            sm.on_fob_presented()
        elif cmd == "a":
            fake_time[0] += 10
            print(f"(clock advanced to {fake_time[0]:.0f}s)")
        else:
            print("unknown command")
        print("  -> state:", sm.state, "| last_recorded:", sm.last_recorded)


if __name__ == "__main__":
    main()
