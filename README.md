# aquarium_float_cutoff
MicroPython code to control an aquarium filter- turning it off and sending a pushover notification if a float switch is triggered (to prevent tank overflowing).

Additionally:
* Beeps every X seconds if network is down (see settings inside ```main.py```)
* Beeps every X seconds if the float switch is in an alert state. (see settings inside ```main.py```)
* Sends notifications via Pushover (https://pushover.net) on state changes.

**Be sure to set your settings inside ```settings.py```!**

## Wiring

* Float switch to 3.3v and GPIO_2
* Buzzer+ to GPIO_4, Buzzer- to GND
* Relay output (in my case, an old PowerSwitch Tail which supports 3.3v logic switching!):
  * Positive to D18
  * Negative to GND

## Features

* Non-blocking WiFi connection (if Wifi is down, control still continues!)
* Pushover notifications sent on state changes (startup, alert, recovery)
* Beeps regularly (configurable) if WiFi not connected
* Beeps regularly (configurable) if float switch in an alert state

## TODO

* Clean up the code, 'cos this is messy (dupe pushover calls)
* Move stuff to OOP, for better state management in particular

## Notes

* Tested with NodeMCU ESP32 board.
* Having the float switch on GPIO_2 has a nice side effect of lighting the LED when in an "OK" state
* Put your settings into ```settings.py``` (note that this is excluded in the ```.gitignore``` file to stop you accidentally pushing sensitive info!)
