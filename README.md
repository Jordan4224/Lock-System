# Lock-System

- RFID controlled deadbolt locking system
Fob controlled clocking system that sends a receiver signal to the PICO, that in turn sends a PWM signal to the stepper motor to retract the deadbolt.

Now for the lock extending.....


	Logic for the lock system

While door is closed, value is TRUE for the light sensor, record value and if recorded value matches next read, do nothing, remain extended.
If fob is presented, the FALSE value is immediately implemented into the sensor logic and retracts the lock, 10 sec pass before next read. Record FALSE.
If last recorded value is FALSE and the light sensor reads a FALSE, then do nothing, remain retracted.
If the last recorded value is FALSE and then the light sensor reads a TRUE value from the reflective plate, record the TRUE after 10 secs and check the value again, if both are TRUE, extend the deadbolt.
