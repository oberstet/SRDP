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

# SRDP vs WAMP

SRDP:

 * runs over UDP
 * binary, stateless
 * malloc-less pure C89 implementation
 * runs in 1kB RAM


# UDP Multicast

An SRDP adapter needs to communicate with an upstream SRDP host.

no manual configuration
no external configuration server

SRDP adapters use [mDNS](http://tools.ietf.org/html/rfc6762), [DNS-SD](http://tools.ietf.org/html/rfc6763) and optionally [DNSSEC](http://tools.ietf.org/html/rfc4033).

http://www.fiz-ix.com/2012/12/using-avahi-in-ubuntu-to-broadcast-services-to-macs-with-bonjour/

http://linux.die.net/man/5/avahi.service

http://elinux.org/RPi_Advanced_Setup
http://wiki.ubuntuusers.de/Avahi

http://stackoverflow.com/questions/3430245/how-to-develop-an-avahi-client-server
http://stackoverflow.com/questions/15553508/browsing-avahi-services-with-python-misses-services
http://avahi.org/wiki/PythonBrowseExample
http://avahi.org/wiki/PythonPublishExample

	
	sudo apt-get install nss-mdns avahi-daemon avahi-utils  

	old debian:
	sudo update-rc.d avahi-daemon defaults

	new debian:
	sudo insserv avahi-daemon

	sudo vim /etc/avahi/services/afpd.service
	
	
	<?xml version="1.0" standalone='no'?><!--*-nxml-*-->
	<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
	<service-group>
	   <name replace-wildcards="yes">%h</name>
	   <service>
	      <type>_afpovertcp._tcp</type>
	      <port>548</port>
	   </service>
	</service-group>



	<?xml version="1.0" standalone='no'?>
	<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
	<service-group>
	        <name replace-wildcards="yes">%h</name>
	        <service>
	                <type>_device-info._tcp</type>
	                <port>0</port>
	                <txt-record>model=RackMac</txt-record>
	        </service>
	        <service>
	                <type>_ssh._tcp</type>
	                <port>22</port>
	        </service>
	</service-group>
		
	sudo /etc/init.d/avahi-daemon restart



> "A multicast address is a logical identifier for a group of hosts in a computer network, that are available to process datagrams or frames intended to be multicast for a designated network service."
> 

239.192.0.0/14

239.0.0.0/8 is Administratively Scoped IPv4 Multicast Space.
239.255.0.0/16 is one of it's subsets (IPv4 Local Scope) in RFC 2365.

Subset that might be even closer to what is needed here is 239.192.0.0/14 (The IPv4 Organization Local Scope)

See [here](http://stackoverflow.com/questions/236231/how-do-i-choose-a-multicast-address-for-my-applications-use), [here](http://tools.ietf.org/html/rfc5771), [here](http://www.iana.org/assignments/multicast-addresses/multicast-addresses.xhtml), 


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
