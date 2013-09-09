# An SRDP enabled Arduino board

This is a complete example of an Arduino board exposed via SRDP. The board's hardware includes:

 * Arduino Mega 2560
 * 1x RGB LED
 * 2x LED
 * 2x Button
 * 2x Analog Knobs

You can control the board from any SRDP host, such as **srdptool** via a Serial-over-USB connection.

The example includes the Arduino firmware in the folders:

 * `SRDP/arduino/demoboard/Demoboard`
 * `SRDP/ansic/srdp`

The main program for the firmware is here

	SRDP/arduino/demoboard/Demoboard/DemoBoard.ino

You can find the EDS files for the *Demoboard* adapter and it's devices here

 * `SRDP/python/srdp/srdp/eds/adapters`
 * `SRDP/python/srdp/srdp/eds/devices`

Finally, you can use **srdptool** to access the *Demoboard* from a notebook or some networked device like a RaspberryPi. For more information on **srdptool**, please see the folder `SRDP/python/srdp`.
