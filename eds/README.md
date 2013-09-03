# EDS

An SRDP host maintains a database of electronic datasheets (EDSs). Besides general information, an EDS describes the **register map** of an *adapter* or a *device* in a computer readable form. Each EDS is uniquely identified by a URI.

An *adapter* connects *devices* to a SRDP host. When a SRDP adapter is connected to an SRDP host, the host will first query the adapter (which has the fixed device index `1`) at the following two predefined, mandatory registers:

  1. *Adapter ID*: Register index `1` (mapped to path `/system/id` on the host)
  2. *Adapter EDS*: Register index `2` (mapped to path `/system/eds` on the host)

The *Adapter ID* register contains a unique 128-Bit UUID identifying the individual adapter, e.g.

	550e8400-e29b-41d4-a716-446655440000

The *Adapter EDS* register contains a string with the URI identifying the EDS that applies to the adapter, e.g.

	http://eds.tavendo.com/adapter/arduino-demoboard

The SRDP host looks up the adapter EDS in it's EDS database. Using the EDS allows the SRDP host to automatically make use of the specific functionality exposed via the adapter registers.

In the next step, the SRDP host queries the following (mandatory) register:

  2. *Device List*: Register index `5` (mapped to path `/system/devices` on the host)

The *Device List* register contains a vector with device indices of all devices currently connected to the adapter, e.g.

	2, 3, 4

In this example, there are three devices currently connected to the adapter. Device index `1` is not used, since it is reserved for the adapter itself. The device index `0` MAY appear in the vector, but is ignored.

Dependent on the SRDP host configuration, the host then starts to query the detected devices at the following two predefined registers:

  1. *Device ID*: Rregister index `1` (mapped to path `/system/id` on the host)
  2. *Device EDS* (register index `2` (mapped to path `/system/eds` on the host)

The *Device ID* register contains a unique 128-bit UUID value.

The *Device EDS* register contains the URI of the EDS applying to the device.

Using the EDS, the host then knows how to communicate with the device.

# Register Descriptors


    {
       "index":    1,
       "path":     "/system/id",
       "optional": false,
       "access":   "read",
       "type":     "uint8",
       "count":    16,
       "desc":     "The globally unique 128-Bit UUID of the driver."
    }


## Register Types

The type system for registers is richer than key-value, but simpler than JSON. It's designed to work efficiently on restricted devices like 8-Bit MCUs with 2kB RAM.

### Scalar Types

The following scalar types are defined in SRDP.

1. Unsigned integers:
 
   * `uint8`
   * `uint16`
   * `uint32`
   * `uint64`

2. Signed integers:

   * `int8`
   * `int16`
   * `int32`
   * `int64`

3. IEEE single and double floating point:

   * `float`
   * `double`

4. Single Byte from UTF-8 encoded Unicode string:

   * `char`

### Composite Types

Besides having a scalar type, a register can have one of three composite types:

 1. *vector* of scalars
 2. *dictionary* of scalars
 3. *vector* of *dictionary* of scalars

Note that other composite types like *dictionary* of *vectors* are invalid.

### Vectors

The number of elements contained in each register must be specified using the `count` attribute. A scalar type register has a `count` of `1`.

The `count` attribute can either have an integer value

    {
       ...
       "type":     "uint8",
       "count":    16,
       ...
    }

which then specifies a **fixed** length **vector** of elements or `1`in case of a scalar register.

The `count` attribute can also indicate a unsigned integer type

    {
       ...
       "type":     "float",
       "count":    "uint16",
       ...
    }

which then specifies a vector of elements that is prefixed with an integer field (little endian) containing the length of the vector that follows:

    | length N (uint16) | float[0] | float[1] | ... | float[N - 1]

In this type system, Unicode strings are specified as vectors of the scalar `char`:

    {
       ...
       "type":     "char",
       "count":    "uint16",
       ...
    }

The register contents is the UTF-8 encoded Unicode string (prefixed by the integer length field, where the length is given in bytes, not Unicode characters).

> Note that when accessing parts of a string register, `position` and `length` are byte-wise and as such may fall into the middle of a UTF-8 encoded single character. Hence, with strings, the ability of SRDP to access only part of an register is of limited use.


### Dictionaries

A register can have *dictionary*  type, e.g.

      {
         "index": 1024,
         "path": "/light",
         "access": "write",
         "type": [
            {
               "field": "red",
               "type": "uint8",
               "desc": "Red color component value. Default is 0."
            },
            {
               "field": "green",
               "type": "uint8",
               "desc": "Green color component value. Default is 0."
            },
            {
               "field": "blue",
               "type": "uint8",
               "desc": "Blue color component value. Default is 0."
            }
         ],
         "count": 1,
         "desc": "Light color (RGB color space). Default is black."
      }

The type is specified by providing a list of *fields*, and for each *field*, the field name (`field`), the field type (`type`) - which must be a scalar type - and the field description (`desc`).

### Vectors of Dictionaries

*Vectors* of *dictionaries* have a `type` field that describes a dictionary (e.g. as in the dictionary example above) and a `count` different from `1` - that is either an integer >1 or an unsigned integer type (e.g. as in the vector example above).


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
	
