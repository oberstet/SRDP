# Simple Register Device Protocol (SRDP)

SRDP is a light-weight client-server protocol that exposes *devices* using a *(virtual) register set* abstraction similar to field buses like [CANopen](http://en.wikipedia.org/wiki/CANopen), [DeviceNet](http://en.wikipedia.org/wiki/Devicenet) and [Modbus](http://en.wikipedia.org/wiki/Modbus).

## Transports

SRDP is designed to work as an application layer protocol (L7) over different transports:

 1. Datagram based
   * 6LowWPAN / UDP
   * UDP (standard IPv4 and IPv6)
 2. Stream based
   * Serial (both synchronous and asynchronous)
   * TCP (with or without TLS)
   * Pipes (IPC)

## Scenarios

SRDP is design to work in scenarios such as the following.

### Scenario 1: SRDP over Serial/COM

An Arduino connected over Serial/USB (= virtual COM port) via SRDP to a small Linux device (e.g. a RaspberryPi) which runs *WebMQ Edge Edition*.

### Scenario 2: SRDP over 6LowWPAN/UDP

A wireless sensor network: MCU SoCs with ARM Cortex M3 and IEEE 802.15.4 (e.g. [ST STM32W](http://www.st.com/web/en/catalog/mmc/FM141/SC1169/SS1581)) running ContikiOS with SRDP over 6LowWPAN/UDP to connect to a small Linux device (e.g. RaspberryPi) which runs *WebMQ Edge Edition*.

### Scenario 3: SRDP over Pipes/IPC

A Modbus master hardware connected to a small Linux device (e.g. RaspberryPi). An SRDP adapter (a piece of software running as a separate Linux process) talks to Modbus on one side (via whatever mechanism/transport), and WebMQ Edge via *SRDP over pipes*.

## Resources

 * [ContikiOS](http://www.contiki-os.org/)
 * [6LoWPAN](http://en.wikipedia.org/wiki/6LoWPAN)
 * [IPv6 over Low-Power Wireless Personal Area Networks (6LoWPANs)](http://tools.ietf.org/html/rfc4919)
 * [Constrained Application Protocol (CoAP)](http://tools.ietf.org/html/draft-ietf-core-coap-18)
 * [Observing Resources in CoAP](http://tools.ietf.org/html/draft-ietf-core-observe-09)
 * [Blockwise transfers in CoAP](http://tools.ietf.org/html/draft-ietf-core-block-12)
 * [Datagram Transport Layer Security](http://en.wikipedia.org/wiki/Datagram_Transport_Layer_Security)
 * [The 6LoWPAN Format](http://www.mi.fu-berlin.de/inf/groups/ag-tech/teaching/2012-13_WS/L_19528_Embedded_Internet_and_the_Internet_of_Things/06.pdf?1358508475)

# CRC

SRDP uses CRC-16 with the following parameters (parameters like Xmodem):

 1. Poly: `0x1021`
 2. Initial value: `0x0000`
 3. No Reverse
 4. No XOR

The check value for the ASCII byte string "123456789" (= 9 bytes) is `0x31C3`.

CRC-16 is a whole family of CRCs, and there is considerable confusion and wrong implementations in the field. Please read:

 * [Wikipedia on CRCs](http://en.wikipedia.org/wiki/Crc16)
 * [C code generator](http://www.mcgougan.se/universal_crc/)
 * [CRC16 online calculator](http://www.lammertbies.nl/comm/info/crc-calculation.html)
 * [CRC16 confusion](http://web.archive.org/web/20071229021252/http://www.joegeluso.com/software/articles/ccitt.htm)

For C, you can use above code generator to get working code. For Python, you can use [crcmod](https://pypi.python.org/pypi/crcmod):

    import crcmod
    crc = crcmod.predefined.PredefinedCrc("xmodem")
    crc.update("123456789")
    print "%0000x" % crc.crcValue

With SRDP, the CRC is computed over the complete frame header and data with the CRC16 field set to 0. After computation of CRC, the value is inserted into the frame CRC field and the frame is transmitted.


> Why isn't the CRC appended after frame data? Because having the CRC in the fixed portion of the frame header simplifies protocol parsing.
