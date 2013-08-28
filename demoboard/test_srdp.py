###############################################################################
##
##  Copyright 2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

import sys, binascii

if sys.platform == 'win32':
   ## on windows, we need to use the following reactor for serial support
   ## http://twistedmatrix.com/trac/ticket/3802
   ##
   from twisted.internet import win32eventreactor
   win32eventreactor.install()

from twisted.internet import reactor
print "Using Twisted reactor", reactor.__class__
print

from twisted.python import usage, log
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import Protocol
from twisted.internet.serialport import SerialPort

from autobahn.websocket import connectWS
from autobahn.wamp import WampClientFactory, WampCraClientProtocol

from srdp import SrdpFrameHeader

BASEURI = "http://tavendo.de/webmq/demo/arduinoboard1#"


SENSOR_TO_URI = {
   "analog1": "http://tavendo.de/webmq/demo/gauges#0",
   #"analog2": "http://tavendo.de/webmq/demo/gauges#1",
   "analog2": "http://tavendo.de/webmq/demo/arduino#analog2",
   "button1": "http://tavendo.de/webmq/demo/arduino#button1",
   "button2": "http://tavendo.de/webmq/demo/arduino#button2",
}

class DemoBoardOptions(usage.Options):
   """
   Command line options for this app.
   """
   optFlags = [['debug', 'd', 'Enable debug log messages.']]
   optParameters = [
      ['baudrate', 'b', 115200, 'Serial port baudrate [default: 9600]'],
      ['port', 'p', 11, 'Serial port to use (e.g. "11" for COM12 or "/dev/ttxACM0") [default: 11]'],
      ['wsuri', 'w', "ws://127.0.0.1/ws", 'Tavendo WebMQ WebSocket endpoint [default: ws://127.0.0.1/ws]']
   ]


class DemoBoardClientProtocol(WampCraClientProtocol):
   """
   WAMP client protocol for our gateway.
   """

   def onSessionOpen(self):
      print "connected"
      d = self.authenticate()
      d.addCallbacks(self.onAuthSuccess, self.onAuthError)


   def onClose(self, wasClean, code, reason):
      reactor.stop()


   def onAuthSuccess(self, permissions):
      print "WAMP session authenticated - permissions:", permissions
      self.subscribe(BASEURI + "led1", self.onLed1Control)
      self.subscribe(BASEURI + "led2", self.onLed2Control)
      self.subscribe(BASEURI + "led3", self.onLed3Control)


   def onAuthError(self, e):
      uri, desc, details = e.value.args
      print "Authentication Error!", uri, desc, details


   def onLed1Control(self, topic, event):
      self.factory.serialproto.controlLed(1, event)


   def onLed2Control(self, topic, event):
      self.factory.serialproto.controlLed(2, event)


   def onLed3Control(self, topic, event):
      self.factory.serialproto.controlRgbLed(3, event['r'], event['g'], event['b'])



class DemoBoardClientFactory(WampClientFactory):
   """
   WAMP client factory for our gateway.
   """

   def buildProtocol(self, addr):
      proto = DemoBoardClientProtocol()
      proto.factory = self
      self.serialproto.client = proto
      return proto



class DemoBoardSerialProtocol(Protocol):
#class DemoBoardSerialProtocol(LineReceiver):
   """
   Serial connector protocol for our gateway.
   """
   _STATE_UNCONNECTED = 0
   _STATE_CONNECTED = 1
   _STATE_SYNCHED = 2

   def __init__(self):
      self._state = DemoBoardSerialProtocol._STATE_UNCONNECTED
      self.client = None
      self._events = 0
      self._ledToggle = False

   def dataReceived(self, data):
      print binascii.hexlify(data)
      #print data


   def controlLed(self, led, v):
      print "control LED %d: %d" % (led, v)
      self.transport.write(",".join([str(x) for x in [led, v]]) + '\n')


   def controlRgbLed(self, led, r, g, b):
      print "control RGB Led %d: %d %d %d" % (led, r, g, b)
      self.transport.write(",".join([str(x) for x in [led, r, g, b]]) + '\n')


   def readRegister(self, device, register):
      f = SrdpFrameHeader(opcode = SrdpFrameHeader.OPCODE_READ_REGISTER,
                          device = device,
                          register = register)
      f.computeCrc()

      wireData = f.serialize()
      self.transport.write(wireData)
      #print binascii.hexlify(wireData)


   def writeRegister(self, device, register, data):
      f = SrdpFrameHeader(opcode = SrdpFrameHeader.OPCODE_WRITE_REGISTER,
                          device = device,
                          register = register)
      f.computeCrc(data)

      wireData = f.serialize() + data
      self.transport.write(wireData)
      print binascii.hexlify(wireData)


   def toggleLed(self):
      self._ledToggle = not self._ledToggle
      if self._ledToggle:
         self.writeRegister(1, 3, '\x01')
         self.writeRegister(1, 4, '\x00')
      else:
         self.writeRegister(1, 3, '\x00')
         self.writeRegister(1, 4, '\x01')


   def readButton(self):
      self.readRegister(1, 6)


   def doTest(self):
      #self.toggleLed()
      #self.readButton()
      reactor.callLater(1, self.doTest)


   def connectionMade(self):
      log.msg('Serial port connected.')
      self._state = DemoBoardSerialProtocol._STATE_CONNECTED
      reactor.callLater(1, self.doTest)

   def connectionLost(self, reason):
      log.msg('Serial port connection lost: %s' % reason)
      self._state = DemoBoardSerialProtocol._STATE_UNCONNECTED


   def lineReceived(self, line):
      print line
      return
      ##
      ## read([key1, key2, ...])
      ## write({key1: value1, key2: value2, ...})
      ## watch([key1, key2, ...])
      ## unwatch([key1, key2, ...])
      ##
      ## ['timestamp', longitude', 'latitude', 'mode']
      ## '<Iff'

      ## Electronic Datasheet (EDS) for device
      ## connected to WebMQ via SRDP.
      eds = {
         'manufactorer': 'Megacorp. Ltd.',
         'registers':
            [
               {
                  'index': 1,
                  'path': '/location/position',
                  'type': 'Iffc',
                  'components': ['timestamp', 'longitude', 'latitude', 'mode']
               },
               {
                  'index': 2,
                  'path': '/location/position/maxUpdateRate',
                  'type': 'I',
                  'description': 'Maximum update frequency of position.'
               },
               {
                  'index': 3,
                  'path': '/location/position/enableNormalize',
                  'type': '?'
               }
            ]
      }


#    http://wastecenter.com/vehicles/A920C9F0/location/position#read

#   session.call('http://wastecenter.com/vehicles/A920C9F0/location/position#read'
#       ).then(function (position) {
#              }
#    );

      ## parse data received from Arduino demoboard
      ##
      try:
         l = line.split()
         sensor = str(l[0])
         timestamp = int(l[1])
         value = int(l[2])
      except Exception, e:
         log.err('unable to parse serial data line %s [%s]' % (line, e))

      if sensor in ['analog1', 'analog2']:
         value = float(value) / 10.

      ## construct WAMP event
      ##
      topic = SENSOR_TO_URI.get(sensor, BASEURI +  sensor)
      #event = {'time': timestamp, 'value': value}
      event = value

      self._events += 1

      if self.client:
         self.client.publish(topic, event)
         print "PUBLISH", self._events, topic, event
      else:
         print "UNCONNECTED", self._events, topic, event



if __name__ == '__main__':

   ## parse options
   ##
   options = DemoBoardOptions()
   try:
      options.parseOptions()
   except usage.UsageError, errortext:
      print '%s %s' % (sys.argv[0], errortext)
      print 'Try %s --help for usage details' % sys.argv[0]
      sys.exit(1)

   log.startLogging(sys.stdout)

   baudrate = int(options.opts['baudrate'])
   port = options.opts['port']
   try:
      port = int(port)
   except:
      # on RaspberryPi, Serial-over-USB appears as /dev/ttyACM0
      pass
   wsuri = options.opts['wsuri']
   debug = True if options['debug'] else False

   ## serial connection to Arduino
   ##
   log.msg("Opening serial port %s [%d baud]" % (port, baudrate))
   serialProtocol = DemoBoardSerialProtocol()
   serialPort = SerialPort(serialProtocol, port, reactor, baudrate = baudrate)

   ## WAMP client factory
   ##
   #log.msg("Connecting to %s" % wsuri)
   #wampClientFactory = DemoBoardClientFactory(wsuri, debugWamp = debug)
   #wampClientFactory.serialproto = serialProtocol
   #connectWS(wampClientFactory)

   reactor.run()
