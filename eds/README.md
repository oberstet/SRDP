# EDS

This document describes the format and meaning of **SRDP electronic datasheets**.

You can find examples of EDS files in the folders next to this document:

  * ./devices/*.eds
  * ./adapters/*.eds

## Introduction

A SRDP host maintains a database of electronic datasheets (EDSs). Besides general information, an EDS describes the **register map** of an *adapter* or a *device* in a computer readable form. Each EDS is uniquely identified by a URI.

Using the EDS - and in particular the register map description contained in the EDS - allows the SRDP host to make use of the specific functionality exposed via the adapter or device registers - automatically and without further manual configuration.


## EDS File Format

An EDS is provided as a *JSON* encoded file. The core structure of the JSON contained in an EDS is as follows:

	{
	   "uri":   <A string with an URI (HTTP scheme) identifying the EDS>,
	
	   "label": <A string with a short, human readable device/adapter label>,
	
	   "desc":  <A string with a detailed, human readable device/adapter description>,
	
	   "registers": [
           ... device/adapter register map - see next section ...
	   ]
	}

A *concrete* device/adapter may contain additional information about the  device/adapter **vendor** and/or **model**:

	{
	   "uri":   <...>,
	   "label": <...>,
	   "desc":  <...>,
	
	   "vendor": {
	      "uri":   <A string with an URI (HTTP scheme) identifying the device/adapter vendor>,
	      "label": <A string with a short, human vendor label>
	      "web":   <A string with a Web link to the vendor>
	   },
	
	   "model": {
	      "uri":   <A string with an URI (HTTP scheme) identifying the device/adapter model>,
	      "label": <A string with a short, human model label>
	      "web":   <A string with a Web link for the model/product>
	   },
	
	   "registers": [
           ... device/adapter register map - see next section ...
	   ]
	}


## Register Maps

*Register maps* describe the registers a device or adapter exposes via SRDP. Here is an example:

      {
         "index":    1024,
         "path":     "/light",

         "optional": false,
         "access":   "write",
         "type":     "uint8",
         "count":    1,

         "desc":     "LED (monochrome). Any non-zero value turns the LED on. Default is off."
      },

This describes a register that controls a single monochrome LED.

The `index` is an integer addressing the respective register. Integers <1024 are reserved for registers predefined by SRDP. The registers 1024 - 65535 are available for user registers.

The `path` is a string containing an URI path component that is used by the SRDP host to map registers to fully qualified URIs.

While the `index` of an register is used only in the communication *in between* host and adapter, the register URIs can be used to address registers from *outside*.

> 1. Both `index` and `path` must be unique (not appear more than once) within a given adapter or device register map.
> 2. The URI pth component MUST NOT contain path manipulators like `..` or query parts (`?`), but MAY contain fragments (`#`).
> 

The boolean valued `optional` attribute specifies if the register is optional, and hence an individual device or adapter may or may not implement the register. Or a given adapter or device may choose to make an optional register only available under certain conditions or upon activation. 

The `access` string attribute specifies the access level the host is given by the adapter or device. The three possible values are:

 * `read`
 * `write`
 * `readwrite`

The `type` and `count` attributes specify the type of values in the register. These attributes are described in the next section.

The `desc` string attribute contains a human readable description of the register and it's function. The text should be addressed to application developers.


### Register Types

The type system for registers is richer than key-value, but simpler than JSON. It is designed to work efficiently on even very restricted devices like for example 8-Bit MCUs with 2kB RAM.

#### Scalar Types

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

#### Composite Types

Besides having a scalar type, a register can have one of three composite types:

 1. *vector* of scalars
 2. *dictionary* of scalars
 3. *vector* of *dictionary* of scalars

Note that other composite types like *dictionary* of *vectors* are invalid.

#### Vectors

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


#### Dictionaries

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

#### Vectors of Dictionaries

*Vectors* of *dictionaries* have a `type` field that describes a dictionary (e.g. as in the dictionary example above) and a `count` different from `1` - that is either an integer >1 or an unsigned integer type (e.g. as in the vector example above).


## Watching Registers

Write me.

### Watching Vector Registers


## Register Map Inheritance

Write me.

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

 
After the host has resolved the device EDS, the register map applied will be - sorted by register index.



## Adapter and Device Discovery

SRDP defines a mechanism for plug-and-play of devices that allows automatic discovery and configuration. This section describes the mechanism.

### Initial Discovery

An *adapter* connects *devices* to a SRDP host. When a SRDP adapter is connected to an SRDP host, the host will first query the adapter (which has the fixed device index `1`) at the following two predefined, mandatory registers:

  1. *Adapter ID*: Register index `1` (mapped to path `/system/id` on the host)
  2. *Adapter EDS*: Register index `2` (mapped to path `/system/eds` on the host)

The *Adapter ID* register contains a unique 128-Bit UUID identifying the individual adapter, e.g.

	550e8400-e29b-41d4-a716-446655440000

The *Adapter EDS* register contains a string with the URI identifying the EDS that applies to the adapter, e.g.

	http://eds.tavendo.com/adapter/arduino-demoboard

The SRDP host looks up the adapter EDS in it's EDS database by URI.

In the next step, the SRDP host queries the following (mandatory) register:

  2. *Device List*: Register index `5` (mapped to path `/system/devices` on the host)

The *Device List* register contains a vector with device indices of all devices currently connected to the adapter, e.g.

	2, 3, 4

In this example, there are three devices currently connected to the adapter. Device index `1` is not used, since it is reserved for the adapter itself. The device index `0` MAY appear in the vector, but is ignored. The order of device indices is unspecified. Indices (other than `0`) MUST NOT appear more than once.

Dependent on the SRDP host configuration, the host then starts to query the detected devices at the following two predefined registers:

  1. *Device ID*: Register index `1` (mapped to path `/system/id` on the host)
  2. *Device EDS* Register index `2` (mapped to path `/system/eds` on the host)

The *Device ID* register contains a unique 128-bit UUID value. The *Device EDS* register contains the URI of the EDS applying to the device.
Using the EDS, the host then knows how to communicate with the device.

### Static and Dynamic Device Lists

An adapter may manage a fixed set of devices or may allow devices to dynamically connect and disconnect from the adapter.

When the adapter manages a fixed set of devices, the contents of the *Device List* register never changes.

Enabling register watching on the *Device List* register is allowed, but will never generate any register change event since the register contents is static.

When the adapter manages a dynamic set of devices the adapter must update the *Device List* register accordingly.

#### *Example 1*
An adapter that can manage a maximum of 10 devices maintains the device list register as a vector of `uint8` of fixed length 10.

The vector is initialized to 0. When a device is connected, the first non-zero vector position is set to the connecting device index. When no empty vector position is left, the maximum number of devices the adapter can manage is reached. When a device is disconnected, the vector position containing the index of the device being removed is set to `0` again.

Whenever the device index vector changes, the adapter generates a register change event with the complete vector (register contents).

#### *Example 2*
Write me.
