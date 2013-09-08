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

 1. *check*
 2. *list*
 3. *show*
 4. *read*
 5. *monitor*
 6. *uuid*

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
	1026 1
	1029 1
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
