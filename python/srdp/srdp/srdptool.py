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

import sys, os, struct, binascii
from pprint import pprint

if sys.platform == 'win32':
   ## on windows, we need to use the following reactor for serial support
   ## http://twistedmatrix.com/trac/ticket/3802
   ##
   from twisted.internet import win32eventreactor
   win32eventreactor.install()

from twisted.internet import reactor
print "Using Twisted reactor", reactor.__class__
print

from twisted.python import log, usage
from twisted.internet.defer import Deferred, returnValue, inlineCallbacks
from twisted.internet.serialport import SerialPort

from srdp import SrdpEdsDatabase, SrdpHostProtocol, SrdpFrameHeader



class SrdpToolOptions(usage.Options):

   # Available modes, specified with the --mode (or short: -m) flag.
   MODES = ['verify', 'check']

   optParameters = [
      ['mode', 'm', None, 'Mode, one of: %s [required]' % ', '.join(MODES)],
      ['eds', 'e', None, 'Path to directory with EDS files (recursively crawled).'],
      ['baudrate', 'b', 115200, 'Serial port baudrate.'],
      ['port', 'p', 11, 'Serial port to use (e.g. "11" for COM12 or "/dev/ttxACM0")'],
   ]

   optFlags = [
      ['debug', 'd', 'Activate debug output.']
   ]

   def postOptions(self):

      if not self['mode']:
         raise usage.UsageError, "a mode must be specified to run!"

      if self['mode'] not in SrdpToolOptions.MODES:
         raise usage.UsageError, "invalid mode %s" % self['mode']

      if not self['eds']:
         raise usage.UsageError, "a directory with EDS files is required!"


class SrdpException(Exception):

   def __init__(self, e):
      error_code = struct.unpack("<l", e.args[0])[0]
      if SrdpFrameHeader.SRDP_ERR_DESC.has_key(error_code):
         error_text = SrdpFrameHeader.SRDP_ERR_DESC[error_code]
      Exception.__init__(self, error_code, error_text)



class SrdpToolHostProtocol(SrdpHostProtocol):

   IDX_REG_ID = 1
   IDX_REG_EDS = 2
   IDX_REG_FREE_RAM = 1024


   @inlineCallbacks
   def getFreeMem(self):
      try:
         res = yield self.readRegister(0, self.IDX_REG_FREE_RAM)
      except Exception, e:
         raise SrdpException(e)
      else:
         res = struct.unpack("<L", res)[0]
         returnValue(res)


   @inlineCallbacks
   def getUuid(self):
      try:
         res = yield self.readRegister(0, self.IDX_REG_ID)
      except Exception, e:
         raise SrdpException(e)
      else:
         returnValue(res)


   @inlineCallbacks
   def getEdsUri(self):
      try:
         res = yield self.readRegister(0, self.IDX_REG_EDS)
      except Exception, e:
         raise SrdpException(e)
      else:
         ## FIXME: need to cut of the \0 byte inserted by C
         returnValue(res[:-1])


   @inlineCallbacks
   def run(self):
      print "Retrieving adapter information .."
      try:
         uuid = yield self.getUuid()
         edsUri = yield self.getEdsUri()
         freemem = yield self.getFreeMem()

         print "Adapter Information:"
         print
         print "UUID               : %s" % (binascii.hexlify(uuid))
         print "EDS URI            : %s (%d)" % (edsUri, len(edsUri))
         print "Free memory (bytes): %d" % (freemem)

         eds = self.runner.edsDatabase.getEdsByUri(edsUri)
         print "Register map       : %d Registers" % len(eds.registersByIndex)
         print
         pprint(eds.registersByIndex)
         print

      except Exception, e:
         print "Error:", e
      self.transport.loseConnection()


   def connectionMade(self):
      print 'Serial device connected.'
      reactor.callLater(1, self.run)


   def connectionLost(self, reason):
      print 'Serial device disconnected.'
      if self._debug:
         log.msg(reason)
      reactor.stop()


# http://twistedmatrix.com/trac/ticket/1248
# http://stackoverflow.com/a/287293/884770
class SerialPortFix(SerialPort):

   def __init__(self, *args, **kw):
      super(SerialPortFix, self).__init__(*args, **kw)
      self._tempDataBuffer = []

   def writeSomeData(self, data):
      return len(data)



class SrdpToolRunner(object):

   def __init__(self):
      self.options = SrdpToolOptions()
      try:
         self.options.parseOptions()
      except usage.UsageError, errortext:
         print '%s %s\n' % (sys.argv[0], errortext)
         print 'Try %s --help for usage details\n' % sys.argv[0]
         sys.exit(1)

      self.debug = self.options['debug']
      if self.debug:
         log.startLogging(sys.stdout)

      self.mode = str(self.options['mode'])
      self.edsDirectory = os.path.abspath(str(self.options['eds']))

      
   def startService(self):
      if self.mode == 'verify':
         db = SrdpEdsDatabase()
         db.loadFromDir(self.edsDirectory)
         return False

      elif self.mode == 'check':

         self.baudrate = int(self.options['baudrate'])
         self.port = self.options['port']
         try:
            self.port = int(self.port)
         except:
            # on RaspberryPi, Serial-over-USB appears as /dev/ttyACM0
            pass

         print "Loading EDS files from directory %s .." % self.edsDirectory
         self.edsDatabase = SrdpEdsDatabase(debug = self.debug)
         self.edsDatabase.loadFromDir(self.edsDirectory)
         print "EDS database with %d objects initiated." % len(self.edsDatabase._edsByUri)

         print "Connecting to serial port %s at %d baud .." % (self.port, self.baudrate)
         self.serialProtocol = SrdpToolHostProtocol(debug = self.debug)
         self.serialProtocol.runner = self
         self.serialPort = SerialPortFix(self.serialProtocol, self.port, reactor, baudrate = self.baudrate)

         return True

      else:
         raise Exception("logic error")



def run():
   runner = SrdpToolRunner()
   if runner.startService():
      reactor.run()

   
# python srdptool.py -m verify -e ../../../eds/

if __name__ == '__main__':
   run()
