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
from twisted.internet.protocol import Protocol
from twisted.internet.serialport import SerialPort

from srdp import SrdpFrameHeader



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


from collections import deque
import struct


class DemoBoardSerialProtocol(Protocol):

   def __init__(self):
      self._ledToggle = False
      self._seq = 0

      self._send_queue = deque()
      self._send_queue_triggered = False

   def _send(self):
      if len(self._send_queue) > 0:
         d = self._send_queue.popleft()
         self.transport.write(d)
         reactor.callLater(0.1, self._send)
      else:
         self._send_queue_triggered = False

   def _trigger(self):
      if not self._send_queue_triggered:
         self._send_queue_triggered = True
         self._send()


   def dataReceived(self, data):
      #print data
      print binascii.hexlify(data)


   def readRegister(self, device, register):
      self._seq += 1
      f = SrdpFrameHeader(seq = self._seq,
                          frametype = SrdpFrameHeader.SRDP_FT_REQ,
                          opcode = SrdpFrameHeader.SRDP_OP_READ,
                          device = device,
                          register = register)
      f.computeCrc()

      wireData = f.serialize()
      self.transport.write(wireData)
      #print binascii.hexlify(wireData)


   def writeRegister(self, device, register, data):
      self._seq += 1
      f = SrdpFrameHeader(seq = self._seq,
                          frametype = SrdpFrameHeader.SRDP_FT_REQ,
                          opcode = SrdpFrameHeader.SRDP_OP_WRITE,
                          device = device,
                          register = register)
      f.computeCrc(data)

      wireData = f.serialize() + data
      if False:
         for c in wireData:
            self._send_queue.append(c)
         self._trigger()
      else:
         self.transport.write(wireData)
      #print binascii.hexlify(wireData)


   def toggleLed(self):
      self._ledToggle = not self._ledToggle
      if self._ledToggle:
         self.writeRegister(1, 1024, '\x7f')
         self.writeRegister(1, 1025, '\x00')
      else:
         self.writeRegister(1, 1024, '\x00')
         self.writeRegister(1, 1025, '\x7e')


   def readButton(self):
      self.readRegister(1, 1027)

   def readAnalog(self):
      #self.readRegister(1, 1031)
      self.readRegister(1, 1) # UUID
      #self.readRegister(1, 2) # EDS


   def doTest(self):
      #self.toggleLed()
      #self.readButton()
      #self.readAnalog()
      reactor.callLater(1, self.doTest)

   def startup(self):
      log.msg('Startup.')
      self.writeRegister(1, 1033, "\x01")
      self.writeRegister(1, 1032, struct.pack("<H", 255))
      reactor.callLater(1, self.doTest)

   def connectionMade(self):
      log.msg('Serial port connected.')
      reactor.callLater(1, self.startup)

   def connectionLost(self, reason):
      log.msg('Serial port connection lost: %s' % reason)



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

   reactor.run()
