# SRDP Tool

**srdptool** is a utility and debugging tool for working with SRDP devices and adapters connected over serial ports.

## Installation

**srdptool** is written in Python. Hence you should have a recent Python 2.7 installed.

Using Python [setuptools](https://pypi.python.org/pypi/setuptools), you can then install **srdptool** by doing:

	easy_install srdp

This will install the Python SRDP library and the **srdptool** command line tool.

You can test your installation by doing:

	$ srdptool --help
	usage: srdptool [-h] -e <EDS directory>
	                (--check | --list | --show <device> | --read <device> |
                     --monitor <device> | --uuid <count>)
	                [--write <register> <value>] [-b <serial baudrate>]
	                [-p <serial port>] [-t <line length>] [-d] [--delay DELAY]
	
	SRDP Tool v0.0.3
	
	optional arguments:
	  -h, --help            show this help message and exit
	
	EDS database:
	  -e <EDS directory>, --eds <EDS directory>
	                        Path to EDS directory.
	
	Run mode (one of the following):
	  --check               Load and check the EDS database.
	  --list                List the devices currently connected to the adapter.
	  --show <device>       Show information for given device.
	  --read <device>       Read current register values for given device (for all
	                        register that allow 'read' access).
	  --monitor <device>    Monitor the given device for notify events.
	  --uuid <count>        Generate given number of UUIDs.
	
	Register writing (optional):
	  --write <register> <value>
	                        Write register values before main action. Register can
	                        be specified either by index or path.
	
	Serial port configuration:
	  -b <serial baudrate>, --baud <serial baudrate>
	                        Serial port baudrate in Bits/s.
	  -p <serial port>, --port <serial port>
	                        Serial port to use (e.g. "11" for COM12 or
	                        "/dev/ttxACM0")
	
	Other options:
	  -t <line length>, --truncate <line length>
	                        Truncate display line length to given number of chars.
	  -d, --debug           Enable debug output.
	  --delay DELAY         Delay to wait for device to get ready (seconds|float).

## Basic Usage

### EDS Directory

**srdptool** operates from a local database of electronic datasheets loaded from EDS files. You specify the directory to (rerursively) search for `*.eds` files containing JSON with the EDS:

	srdptool --eds $HOME/eds ...

### Run Modes

**srdptool** has the following 6 run modes:

 1. **check**: Load and check EDS files.

 2. **list**: List devices connected to adapter.

 3. **show**: Show EDS for a device.

 4. **read**: Read register values from a device.

 5. **monitor**: Monitor registers of a device.

 6. **uuid**: Generate UUIDs.

## Examples

### Check EDS Database

	$ srdptool --eds ./eds/ --check
	
	Ok: loaded and checked 7 EDS files from f:\scm\SRDP\eds

### List Adapter Devices

	$ srdptool --port COM12 --baud 115200 --eds ./eds/ --list
	Loading EDS files from directory f:\scm\SRDP\eds ..
	EDS database with 7 objects initiated.
	Connecting to serial port COM12 at 115200 baud ..
	Serial device connected.
	Giving the device 1.0 seconds to get ready ..
	
	SRDP Adapter: Connected Devices
	===============================
	
	Adapter UUID    : a4104a898df146e5a64c3bc737dfd2f4
	Adapter EDS URI : http://eds.tavendo.com/adapter/arduino-demoboard
	
	--------+----------------------------------+-----------------------------------------------------------------+----------
	 Device | UUID                             | EDS URI                                                         | Registers
	--------+----------------------------------+-----------------------------------------------------------------+----------
	      1 | a4104a898df146e5a64c3bc737dfd2f4 | http://eds.tavendo.com/adapter/arduino-demoboard                |     7
	      2 | eece840d244649988523bbd84c781f93 | http://eds.tavendo.com/device/arduino-rgb-led                   |     6
	      3 | c01afa3d46634e82bbecf17c87a1162f | http://eds.tavendo.com/device/arduino-combocontrol              |    12
	      4 | 1ffdf7db1da540c9a130abe6f2700f40 | http://eds.tavendo.com/device/arduino-combocontrol              |    12
	--------+----------------------------------+-----------------------------------------------------------------+----------
	
	Serial device disconnected.

### Show Device EDS

	$ srdptool --port COM12 --baud 115200 --eds ./eds/ --show 4
	Loading EDS files from directory f:\scm\SRDP\eds ..
	EDS database with 7 objects initiated.
	Connecting to serial port COM12 at 115200 baud ..
	Serial device connected.
	Giving the device 1.0 seconds to get ready ..
	
	SRDP Device: Register Map
	=========================
	
	Device Index   : 4
	Device UUID    : 1ffdf7db1da540c9a130abe6f2700f40
	Device EDS URI : http://eds.tavendo.com/device/arduino-combocontrol
	
	----------+--------------------------+------------+----------+----------+----------+------------+-----------------------
	 Register | Path                     | Access     | Optional | Count    | Type     | Component  | Description
	----------+--------------------------+------------+----------+----------+----------+------------+-----------------------
	        1 | /system/id               | read       | False    | 16       | uint8    |            | The globally unique ..
	        2 | /system/eds              | read       | False    | uint16   | char     |            | The URI of the elect..
	        3 | /system/version#hardware | read       | True     | uint16   | char     |            | Optional register: d..
	        4 | /system/version#firmware | read       | True     | uint16   | char     |            | Optional register: d..
	     1024 | /light                   | write      | False    | 1        | uint8    |            | LED (monochrome). An..
	     1025 | /button                  | read       | False    | 1        | dict:    |            | Button.
	          |                          |            |          |          |   uint32 | time       | Sample time of `stat..
	          |                          |            |          |          |   uint8  | state      | Current button state..
	     1026 | /button#watch            | readwrite  | False    | 1        | uint8    |            | Enable watching of b..
	     1027 | /slider                  | read       | False    | 1        | dict:    |            | Slider.
	          |                          |            |          |          |   uint32 | time       | Sample time of `valu..
	          |                          |            |          |          |   uint16 | value      | Current slider value..
	     1028 | /slider#max              | readwrite  | False    | 1        | uint16   |            | Maximum value for sl..
	     1029 | /slider#watch            | readwrite  | False    | 1        | uint8    |            | Enable watching of s..
	     1030 | /slider#urate            | readwrite  | True     | 1        | float    |            | Setting a non-zero v..
	     1031 | /slider#smooth           | readwrite  | True     | 1        | float    |            | Controls slider anal..
	----------+--------------------------+------------+----------+----------+----------+------------+-----------------------
	
	Serial device disconnected.
	
### Read Register Values

	$ srdptool --port COM12 --baud 115200 --eds ./eds/ --read 4
	Loading EDS files from directory f:\scm\SRDP\eds ..
	EDS database with 7 objects initiated.
	Connecting to serial port COM12 at 115200 baud ..
	Serial device connected.
	Giving the device 1.0 seconds to get ready ..
	
	SRDP Device: Register Values
	============================
	
	Device Index   : 4
	Device UUID    : 1ffdf7db1da540c9a130abe6f2700f40
	Device EDS URI : http://eds.tavendo.com/device/arduino-combocontrol
	
	----------+--------------------------+----------------------------------------------------------------------------------
	 Register | Path                     | Current Value
	----------+--------------------------+----------------------------------------------------------------------------------
	        1 | /system/id               | 0x1ffdf7db1da540c9a130abe6f2700f40
	        2 | /system/eds              | http://eds.tavendo.com/device/arduino-combocontrol
	        3 | /system/version#hardware | - (not implemented)
	        4 | /system/version#firmware | - (not implemented)
	     1025 | /button                  | {'state': 0, 'time': 21112}
	     1026 | /button#watch            | 0
	     1027 | /slider                  | {'value': 537, 'time': 272988}
	     1028 | /slider#max              | 1000
	     1029 | /slider#watch            | 0
	     1030 | /slider#urate            | 2.5
	     1031 | /slider#smooth           | - (not implemented)
	----------+--------------------------+----------------------------------------------------------------------------------
	
	Serial device disconnected.

### Monitor Register Values

	$ srdptool --port COM12 --baud 115200 --eds ./eds/ --monitor 4 --write 1026 1 --write 1029 1
	Loading EDS files from directory f:\scm\SRDP\eds ..
	EDS database with 7 objects initiated.
	Connecting to serial port COM12 at 115200 baud ..
	Serial device connected.
	Giving the device 1.0 seconds to get ready ..
	
	SRDP Device: Monitor Registers
	==============================
	
	Device Index   : 4
	Device UUID    : 1ffdf7db1da540c9a130abe6f2700f40
	Device EDS URI : http://eds.tavendo.com/device/arduino-combocontrol
	
	----------+--------------------------+----------------------------------------------------------------------------------
	 Register | Path                     | Current Value
	----------+--------------------------+----------------------------------------------------------------------------------
	     1025 | /button                  | {'state': 1, 'time': 2400472}
	     1025 | /button                  | {'state': 0, 'time': 2646720}
	     1025 | /button                  | {'state': 1, 'time': 2913416}
	     1025 | /button                  | {'state': 0, 'time': 3077656}
	     1027 | /slider                  | {'value': 538, 'time': 4819876}
	     1027 | /slider                  | {'value': 539, 'time': 4922652}
	     1027 | /slider                  | {'value': 540, 'time': 5004932}
	     1027 | /slider                  | {'value': 539, 'time': 5148708}
	     1027 | /slider                  | {'value': 538, 'time': 5169532}
	     1027 | /slider                  | {'value': 537, 'time': 5190348}
	     1027 | /slider                  | {'value': 536, 'time': 5211172}
	     1027 | /slider                  | {'value': 535, 'time': 5231996}
	     1027 | /slider                  | {'value': 534, 'time': 5252812}
	     1027 | /slider                  | {'value': 533, 'time': 5294124}
    ...

### Write Composite Value

Here is a device with a RGB LED that is controlled from a register with 3 components:

	$ srdptool --port COM12 --baud 115200 --eds ../../../eds/ --show 2
	Loading EDS files from directory f:\scm\SRDP\eds ..
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

And here is how you can write to the `/light` register and set a LED color value:

	srdptool --port COM12 --baud 115200 --eds ../../../eds/ --monitor 2 \
             --write 1024 '{"red": 255, "green": 100, "blue": 30}'


### Generate UUIDs

	$ srdptool --eds ./eds/ --uuid 4
	
	UUID    : 6a762cb0-107a-410c-b7cf-05229414a508
	HEX     : 6a762cb0107a410cb7cf05229414a508
	C/C++   : {0x6a, 0x76, 0x2c, 0xb0, 0x10, 0x7a, 0x41, 0x0c, 0xb7, 0xcf, 0x05, 0x22, 0x94, 0x14, 0xa5, 0x08}
	
	UUID    : ebb65003-ce93-45c2-a606-290e4e372dff
	HEX     : ebb65003ce9345c2a606290e4e372dff
	C/C++   : {0xeb, 0xb6, 0x50, 0x03, 0xce, 0x93, 0x45, 0xc2, 0xa6, 0x06, 0x29, 0x0e, 0x4e, 0x37, 0x2d, 0xff}
	
	UUID    : b80e8d49-bba1-4892-89fa-bfb9e48e70c1
	HEX     : b80e8d49bba1489289fabfb9e48e70c1
	C/C++   : {0xb8, 0x0e, 0x8d, 0x49, 0xbb, 0xa1, 0x48, 0x92, 0x89, 0xfa, 0xbf, 0xb9, 0xe4, 0x8e, 0x70, 0xc1}
	
	UUID    : bc135d3e-e4f8-4230-b6fb-ee78bb1fc62b
	HEX     : bc135d3ee4f84230b6fbee78bb1fc62b
	C/C++   : {0xbc, 0x13, 0x5d, 0x3e, 0xe4, 0xf8, 0x42, 0x30, 0xb6, 0xfb, 0xee, 0x78, 0xbb, 0x1f, 0xc6, 0x2b}


# Builtin EDS Database

## Open Energy Monitor

 * http://openenergymonitor.org/emon/node/58
 * https://github.com/openenergymonitor/EmonLib/blob/master/examples/voltage_and_current/voltage_and_current.ino
 * https://github.com/openenergymonitor/EmonLib/blob/master/EmonLib.cpp
