# EDS

An SRDP host maintains a database of electronic datasheets (EDSs). Each EDS is uniquely identified by a URI. Besides general information, an EDS describes the register map of a device in a computer readable form.

When a SRDP device is connected (via an SRDP driver) to an SRDP host, the host will first query the device at the following two predefined registers:

  1. *Device ID* (register index `1`, path `/system/id`)
  2. *Device EDS* (register index `2`, path `/system/eds`)

The *Device ID* register contains a unique 128-bit UUID value.
The *Device EDS* register contains the URI of the EDS applying to the device.

Using the EDS, the host then knows how to communicate with the device.

# Example

The device profile with URI `http://eds.tavendo.com/device/arduino-rgb-led` in file `devices/tavendo_arduino_colorlight.eds` defines general information such as

  * Vendor
  * Model

and the complete device register map by both referring to other EDSs (1, 2) and providing register signatures:

    http://eds.tavendo.com/device/arduino-rgb-led
      |
      +-- http://eds.tavendo.com/device/device        (1)
      |
      +-- http://eds.tavendo.com/device/colorlight    (2)
      |
      +-- ...                                         (3)

 
After the host has resolved the device EDS, the register map applied will be - sorted by register index:

	{1: {'access': 'read',
	     'count': 16,
	     'desc': 'The globally unique 128-Bit UUID of the device.',
	     'index': 1,
	     'path': '/system/id',
	     'type': 'uint8'},
	 2: {'access': 'read',
	     'count': 1,
	     'desc': 'The URI of the electronic datasheet (EDS) of the device.',
	     'index': 2,
	     'path': '/system/eds',
	     'type': 'string'},
	 3: {'access': 'read',
	     'count': 1,
	     'desc': 'Optional register: hardware version.',
	     'index': 3,
	     'path': '/system/version#hardware',
	     'type': 'string'},
	 4: {'access': 'read',
	     'count': 1,
	     'desc': 'Optional register: firmware version.',
	     'index': 4,
	     'path': '/system/version#firmware',
	     'type': 'string'},
	 1024: {'access': 'write',
	        'count': 1,
	        'desc': 'Light color (RGB color space). Default is black.',
	        'index': 1024,
	        'path': '/light',
	        'type': [{'desc': 'Red color component value. Default is 0.',
	                   'field': 'red',
	                   'type': 'uint8'},
	                  {'desc': 'Green color component value. Default is 0.',
	                   'field': 'green',
	                   'type': 'uint8'},
	                  {'desc': 'Blue color component value. Default is 0.',
	                   'field': 'blue',
	                   'type': 'uint8'}]},
	 1025: {'access': 'readwrite',
	        'count': 1,
	        'desc': 'LED flash rate in Hz or 0 for no flashing. Default is 0.',
	        'index': 1025,
	        'path': '/light#flashrate',
	        'type': 'float'}}

and sorted by path:

	{'/light': {'access': 'write',
	             'count': 1,
	             'desc': 'Light color (RGB color space). Default is black.',
	             'index': 1024,
	             'path': '/light',
	             'type': [{'desc': 'Red color component value. Default is 0.',
	                        'field': 'red',
	                        'type': 'uint8'},
	                       {'desc': 'Green color component value. Default is 0.',
	                        'field': 'green',
	                        'type': 'uint8'},
	                       {'desc': 'Blue color component value. Default is 0.',
	                        'field': 'blue',
	                        'type': 'uint8'}]},
	 '/light#flashrate': {'access': 'readwrite',
	                       'count': 1,
	                       'desc': 'LED flash rate in Hz or 0 for no flashing. Default is 0.',
	                       'index': 1025,
	                       'path': '/light#flashrate',
	                       'type': 'float'},
	 '/system/eds': {'access': 'read',
	                  'count': 1,
	                  'desc': 'The URI of the electronic datasheet (EDS) of the device.',
	                  'index': 2,
	                  'path': '/system/eds',
	                  'type': 'string'},
	 '/system/id': {'access': 'read',
	                 'count': 16,
	                 'desc': 'The globally unique 128-Bit UUID of the device.',
	                 'index': 1,
	                 'path': '/system/id',
	                 'type': 'uint8'},
	 '/system/version#firmware': {'access': 'read',
	                               'count': 1,
	                               'desc': 'Optional register: firmware version.',
	                               'index': 4,
	                               'path': '/system/version#firmware',
	                               'type': 'string'},
	 '/system/version#hardware': {'access': 'read',
	                               'count': 1,
	                               'desc': 'Optional register: hardware version.',
	                               'index': 3,
	                               'path': '/system/version#hardware',
	                               'type': 'string'}}
	
