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

import sys, struct

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
from twisted.internet.defer import Deferred, returnValue, inlineCallbacks
from twisted.internet.serialport import SerialPort

from srdp import SrdpHostProtocol, SrdpFrameHeader



##
## scalar
## object
## vector of scalars
## vector of objects
## string
##

# string
# float, double
# int8, int16, int32, int64
# uint8, uint16, uint32, uint64

class DemoBoardHostProtocol(SrdpHostProtocol):

   IDX_REG_FREE_RAM = 1024

   @inlineCallbacks
   def getFreeMem(self):
      try:
         res = yield self.readRegister(0, self.IDX_REG_FREE_RAM)
      except Exception, e:
         error_code = struct.unpack("<l", e.args[0])[0]
         if SrdpFrameHeader.SRDP_ERR_DESC.has_key(error_code):
            error_text = SrdpFrameHeader.SRDP_ERR_DESC[error_code]
         raise Exception(error_code, error_text)
      else:
         res = struct.unpack("<L", res)[0]
         returnValue(res)


   @inlineCallbacks
   def runTests(self):
      try:
         print "Free memory (bytes): %d" % (yield self.getFreeMem())
      except Exception, e:
         print "Error:", e
      self.transport.loseConnection()


   def connectionMade(self):
      log.msg('Serial port connected.')
      reactor.callLater(1, self.runTests)


   def connectionLost(self, reason):
      log.msg('Serial port connection lost: %s' % reason)
      reactor.stop()


# http://twistedmatrix.com/trac/ticket/1248
# http://stackoverflow.com/a/287293/884770
class SerialPortFix(SerialPort):

   def __init__(self, *args, **kw):
      super(SerialPortFix, self).__init__(*args, **kw)
      self._tempDataBuffer = []

   def writeSomeData(self, data):
      return len(data)


# class Super( object ):
#    def __init__( self, this, that ):
#        self.this = this
#        self.that = that

# class Sub( Super ):
#    def __init__( self, myStuff, *args, **kw ):
#        super( Sub, self ).__init__( *args, **kw )
#        self.myStuff= myStuff


class DemoBoardHostOptions(usage.Options):
   """
   Command line options for this app.
   """
   optFlags = [['debug', 'd', 'Enable debug log messages.']]
   optParameters = [
      ['baudrate', 'b', 115200, 'Serial port baudrate [default: 9600]'],
      ['port', 'p', 11, 'Serial port to use (e.g. "11" for COM12 or "/dev/ttxACM0") [default: 11]'],
      ['wsuri', 'w', "ws://127.0.0.1/ws", 'Tavendo WebMQ WebSocket endpoint [default: ws://127.0.0.1/ws]']
   ]


import json, os, sys, re
from pprint import pprint





if __name__ == '__main__':

   db = SrdpEdsDatabase()
   db.loadFromDir("../eds")
   db.toHtml("http://eds.tavendo.com/device/arduino-combocontrol", "arduino-combocontrol.html")
   #db.pprint("http://eds.tavendo.com/device/arduino-combocontrol")
   #db.pprint("http://eds.tavendo.com/device/device")
   #db.pprint("http://eds.tavendo.com/device/colorlight")
   #db.pprint("http://eds.tavendo.com/device/arduino-rgb-led")
   #db.pprint()

   sys.exit(0)

   eds = SrdpEds()
   eds.load('../eds/devices/device.eds')
   eds.load('../eds/devices/colorlight.eds')
   eds.load('../eds/devices/tavendo_arduino_colorlight.eds')
   pprint(eds.registersByIndex)
   pprint(eds.registersByPath)

   ## parse options
   ##
   options = DemoBoardHostOptions()
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
   serialProtocol = DemoBoardHostProtocol(debug = debug)
   serialPort = SerialPortFix(serialProtocol, port, reactor, baudrate = baudrate)

   reactor.run()
