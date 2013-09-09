# An SRDP enabled Arduino board

## Overview

This is a complete example of an Arduino board exposed via SRDP.

The board's hardware includes:

 * Arduino Mega 2560
 * 1x RGB LED
 * 2x LED
 * 2x Button
 * 2x Analog Knobs

This hardware is exposed as a set of virtual registers accessed via SRDP.

You can control the board from any SRDP host, such as **srdptool** via a Serial-over-USB connection.

## Plug & Play

Here is how you can dynamically query the *Demoboard* using **srdptool**:

	$ srdptool --port COM12 --baud 115200 --show 2
	Ok: loaded and checked 7 EDS files from c:\Python27\lib\site-packages\srdp-0.0.4-py2.7.egg\srdp\eds
	EDS database with 7 objects initiated.
	Connecting to serial port COM12 at 115200 baud ..
	Serial device connected.
	Giving the device 1.0 seconds to get ready ..
	
	SRDP Device: Register Map
	=========================
	
	Device Index   : 2
	Device UUID    : eece840d244649988523bbd84c781f93
	Device EDS URI : http://eds.tavendo.com/device/arduino-rgb-led
	
	----------+--------------------------+------------+----------+----------+----------+------------+-----------------------
	 Register | Path                     | Access     | Optional | Count    | Type     | Component  | Description
	----------+--------------------------+------------+----------+----------+----------+------------+-----------------------
	        1 | /system/id               | read       | False    | 16       | uint8    |            | The globally unique ..
	        2 | /system/eds              | read       | False    | uint16   | char     |            | The URI of the elect..
	        3 | /system/version#hardware | read       | True     | uint16   | char     |            | Optional register: d..
	        4 | /system/version#firmware | read       | True     | uint16   | char     |            | Optional register: d..
	     1024 | /light                   | write      | False    | 1        | dict:    |            | Light color (RGB col..
	          |                          |            |          |          |   uint8  | red        | Red color component ..
	          |                          |            |          |          |   uint8  | green      | Green color componen..
	          |                          |            |          |          |   uint8  | blue       | Blue color component..
	     1025 | /light#flashrate         | readwrite  | False    | 1        | float    |            | LED flash rate in Hz..
	----------+--------------------------+------------+----------+----------+----------+------------+-----------------------
	
	Serial device disconnected.

and read current register values:

	$ srdptool --port COM12 --baud 115200 --read 3
	Ok: loaded and checked 7 EDS files from c:\Python27\lib\site-packages\srdp-0.0.4-py2.7.egg\srdp\eds
	EDS database with 7 objects initiated.
	Connecting to serial port COM12 at 115200 baud ..
	Serial device connected.
	Giving the device 1.0 seconds to get ready ..
	
	SRDP Device: Register Values
	============================
	
	Device Index   : 3
	Device UUID    : c01afa3d46634e82bbecf17c87a1162f
	Device EDS URI : http://eds.tavendo.com/device/arduino-combocontrol
	
	----------+--------------------------+----------------------------------------------------------------------------------
	 Register | Path                     | Current Value
	----------+--------------------------+----------------------------------------------------------------------------------
	        1 | /system/id               | 0xc01afa3d46634e82bbecf17c87a1162f
	        2 | /system/eds              | http://eds.tavendo.com/device/arduino-combocontrol
	        3 | /system/version#hardware | - (not implemented)
	        4 | /system/version#firmware | - (not implemented)
	     1025 | /button                  | {'state': 0, 'time': 21100}
	     1026 | /button#watch            | 0
	     1027 | /slider                  | {'value': 503, 'time': 252340}
	     1028 | /slider#max              | 1000
	     1029 | /slider#watch            | 0
	     1030 | /slider#urate            | 2.5
	     1031 | /slider#smooth           | - (not implemented)
	----------+--------------------------+----------------------------------------------------------------------------------
	
	Serial device disconnected.
	


## Files

The example includes the Arduino firmware in the folders:

 * `SRDP/arduino/demoboard/Demoboard`
 * `SRDP/ansic/srdp`

The main program for the firmware is here

	SRDP/arduino/demoboard/Demoboard/DemoBoard.ino

You can find the EDS files for the *Demoboard* adapter and it's devices here

 * `SRDP/python/srdp/srdp/eds/adapters`
 * `SRDP/python/srdp/srdp/eds/devices`

Finally, you can use **srdptool** to access the *Demoboard* from a notebook or some networked device like a RaspberryPi. For more information on **srdptool**, please see the folder `SRDP/python/srdp`.
