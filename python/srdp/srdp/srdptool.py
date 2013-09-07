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

import sys, os, struct, binascii, uuid
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
from twisted.python.failure import Failure
from twisted.internet.defer import Deferred, DeferredList, returnValue, inlineCallbacks
from twisted.internet.serialport import SerialPort

from srdp import SrdpEdsDatabase, SrdpHostProtocol, SrdpFrameHeader, SrdpException



def splitlen(seq, length):
   """
   Splits a string into fixed size parts.
   """
   return [seq[i:i+length] for i in range(0, len(seq), length)]

def tabify(fields, formats):
   r = []
   for i in xrange(len(formats)):

      N = int(formats[i][1:]) 

      if fields:
         s = str(fields[i])
         if len(s) > N:
            s = s[:N-2] + ".."
         l = N - len(s)
         m = formats[i][0]
      else:
         s = ''
         l = N
         m = '+'

      if m == 'l':
         r.append(s + ' ' * l)
      elif m == 'r':
         r.append(' ' * l + s)
      elif m == 'c':
         c1 = l / 2
         c2 = l - c1
         r.append(' ' * c1 + s + ' ' * c2)
      elif m == '+':
         r.append('-' * l)
      else:
         raise Exception("invalid field format")

   if m == '+':
      return '-+-'.join(r)
   else:
      return ' | '.join(r)


class SrdpToolOptions(usage.Options):

   # Available modes, specified with the --mode (or short: -m) flag.
   ##
   ##
   ## srdptool -p 11 -b 115200 -e ./eds -m listen -w "2:1025, 3:1030"
   ##
   ## srdptool -p 11 -b 115200 -e ./eds -m listen -w "2:/slider#watch, 3:/button#watch"
   ##
   MODES = ['verify', 'check', 'uuid', 'list', 'show', 'listen']

   optParameters = [
      ['mode', 'm', None, 'Mode, one of: %s [required]' % ', '.join(MODES)],
      ['show', 's', None, ''],
      ['list', 'l', None, ''],
      ['eds', 'e', None, 'Path to directory with EDS files (recursively crawled).'],
      ['baudrate', 'b', 115200, 'Serial port baudrate.'],
      ['port', 'p', 11, 'Serial port to use (e.g. "11" for COM12 or "/dev/ttxACM0")'],
   ]

   optFlags = [
      ['debug', 'd', 'Activate debug output.']
   ]

   def postOptions(self):

      return

      if not self['mode']:
         raise usage.UsageError, "a mode must be specified to run!"

      if self['mode'] not in SrdpToolOptions.MODES:
         raise usage.UsageError, "invalid mode %s" % self['mode']

      if self['mode'] in ['verify', 'check', 'list']:
         if not self['eds']:
            raise usage.UsageError, "a directory with EDS files is required!"




class SrdpToolHostProtocol(SrdpHostProtocol):

   IDX_REG_ID = 1
   IDX_REG_EDS = 2
   IDX_REG_HW_VERSION = 3
   IDX_REG_SW_VERSION = 4
   IDX_REG_DEVICES = 5
   IDX_REG_FREE_RAM = 1024


   @inlineCallbacks
   def getFreeMem(self):
      res = yield self.readRegister(1, self.IDX_REG_FREE_RAM)
      res = struct.unpack("<L", res)[0]
      returnValue(res)


   @inlineCallbacks
   def getUuid(self, device = 1):
      res = yield self.readRegister(device, self.IDX_REG_ID)
      returnValue(res)


   @inlineCallbacks
   def getEdsUri(self, device = 1):
      res = yield self.readRegister(device, self.IDX_REG_EDS)
      returnValue(res[2:])


   @inlineCallbacks
   def getHardwareVersion(self):
      res = yield self.readRegister(1, self.IDX_REG_HW_VERSION)
      returnValue(res[2:])


   @inlineCallbacks
   def getSoftwareVersion(self):
      res = yield self.readRegister(1, self.IDX_REG_SW_VERSION)
      returnValue(res[2:])


   @inlineCallbacks
   def getDevices(self):
      res = yield self.readRegister(1, self.IDX_REG_DEVICES)
      count = struct.unpack("<H", res[:2])
      val = list(struct.unpack("<%dH" % count, res[2:]))
      returnValue(val)


   @inlineCallbacks
   def printDeviceIds(self):
      devices = {}
      devs = yield self.getDevices()
      dl = []
      for i in devs:
         dl.append(self.readRegister(i, self.IDX_REG_ID))

      def println(res):
         print "res:", res

      DeferredList(dl).addBoth(println)


   @inlineCallbacks
   def printDeviceIds2(self):
      devices = yield self.getDevices()
      for i in devices:
         uuid = yield self.getUuid(i)
         print i, binascii.hexlify(uuid)


   @inlineCallbacks
   def printDeviceEdsUris(self):
      devices = yield self.getDevices()
      for i in devices:
         edsUri = yield self.getEdsUri(i)
         print i, edsUri


   def getDeviceEdsMap2(self):
      dret = Deferred()
      ret = {}

      d = self.readRegister(1, self.IDX_REG_DEVICES)

      def _getDeviceListSuccess(res):
         count = struct.unpack("<H", res[:2])
         devices = list(struct.unpack("<%dH" % count, res[2:]))
         devices.append(1)
         for d in devices:
            ret[d] = {}

         # get EDS URIs
         #
         dl1 = []
         for i in devices:
            dl1.append(self.readRegister(i, self.IDX_REG_EDS))

         dlist1 = DeferredList(dl1)

         def _getDeviceEdsListSuccess1(res):
            #print res
            for i in xrange(len(res)):
               ret[devices[i]]['eds'] = res[i][1][2:]

            dret.callback(ret)

         dlist1.addCallback(_getDeviceEdsListSuccess1)

         ## get UUIDs
         ##
         dl2 = []
         for i in devices:
            dl2.append(self.readRegister(i, self.IDX_REG_ID))

         dlist2 = DeferredList(dl2)

         def _getDeviceEdsListSuccess2(res):
            #print res
            for i in xrange(len(res)):
               ret[devices[i]]['uuid'] = res[i][1]

            dret.callback(ret)

         dlist2.addCallback(_getDeviceEdsListSuccess2)

         #def _done():
         #   dret.callback(ret)

         #DeferredList([dlist1, dlist2]).addCallback(_done)

      d.addCallback(_getDeviceListSuccess)

      return dret



   def getDeviceEdsMap(self):
      dret = Deferred()

      d = self.readRegister(1, self.IDX_REG_DEVICES)

      def _getDeviceListSuccess(res):
         count = struct.unpack("<H", res[:2])
         devices = list(struct.unpack("<%dH" % count, res[2:]))
         devices.append(1)

         dl = []
         for i in devices:
            dl.append(self.readRegister(i, self.IDX_REG_EDS))

         dlist = DeferredList(dl)

         def _getDeviceEdsListSuccess1(res):
            ret = {}
            for i in xrange(len(res)):
               ret[devices[i]] = res[i][1][2:]

            dret.callback(ret)

         dlist.addCallback(_getDeviceEdsListSuccess1)

      d.addCallback(_getDeviceListSuccess)

      return dret


   def getDeviceUuidMap(self):
      dret = Deferred()

      d = self.readRegister(1, self.IDX_REG_DEVICES)

      def _getDeviceListSuccess(res):
         count = struct.unpack("<H", res[:2])
         devices = list(struct.unpack("<%dH" % count, res[2:]))
         devices.append(1)

         dl = []
         for i in devices:
            dl.append(self.readRegister(i, self.IDX_REG_ID))

         dlist = DeferredList(dl)

         def _getDeviceEdsListSuccess1(res):
            ret = {}
            for i in xrange(len(res)):
               ret[devices[i]] = res[i][1]

            dret.callback(ret)

         dlist.addCallback(_getDeviceEdsListSuccess1)

      d.addCallback(_getDeviceListSuccess)

      return dret


   @inlineCallbacks
   def listDevices(self):
      try:
         em = yield self.getDeviceEdsMap()
         im = yield self.getDeviceUuidMap()
         LINEFORMAT = ['r8', 'l32', 'l60', 'r9']
         print
         print tabify(["Device:", "UUID", "EDS URI", "Registers"], LINEFORMAT)
         print tabify(None, LINEFORMAT)
         for i in sorted(em.keys()):
            eds = self.runner.edsDatabase.getEdsByUri(em[i])
            print tabify([i, binascii.hexlify(im[i]), em[i], len(eds.registersByIndex)], LINEFORMAT)
         print
      except Exception, e:
         raise e
      finally:
         self.transport.loseConnection()


   @inlineCallbacks
   def showDevice(self):
      try:
         device = int(self.runner.modeArg)
         uuid = yield self.getUuid(device)
         edsUri = yield self.getEdsUri(device)
         #devices = yield self.getDevices()
         #swVersion = yield self.getSoftwareVersion()
         #hwVersion = yield self.getHardwareVersion()
         #freemem = yield self.getFreeMem()

         print "Device Information:"
         print
         print "UUID               : %s" % (binascii.hexlify(uuid))
         print "EDS URI            : %s" % (edsUri)
         #print "Harware Version    : %s" % hwVersion
         #print "Software Version   : %s" % swVersion
         #print "Devices            : %s" % (str(devices))
         #print "Free memory (bytes): %d" % (freemem)

         eds = self.runner.edsDatabase.getEdsByUri(edsUri)
         print "Register Map       : %d Registers" % len(eds.registersByIndex)
         print

         LINEFORMAT = ["r8", "l24", "l10", "l8", "l8", "l8", "l10", "l40"]

         print tabify(["Index", "Path", "Access", "Optional", "Count", "Type", "Component", "Description"], LINEFORMAT)
         print tabify(None, LINEFORMAT)

         for k in sorted(eds.registersByIndex.keys()):
            reg = eds.registersByIndex[k]
            if type(reg['type']) == list:
               rtype = 'dict:'
            else:
               rtype = reg['type']
            print tabify([reg['index'],
                          reg['path'],
                          reg['access'],
                          reg['optional'],
                          reg['count'],
                          rtype,
                          "",
                          reg['desc']], LINEFORMAT)
            if rtype == 'dict:':
               for att in reg['type']:
                  print tabify(["", "", "", "", "", "  " + att["type"], att["field"], att["desc"]], LINEFORMAT)

         print

      except Exception, e:
         print "Error:", e
      self.transport.loseConnection()



   def connectionMade(self):
      print 'Serial device connected.'
      modeMap = {'list': self.listDevices, 'show': self.showDevice}
      if modeMap.has_key(self.runner.mode):
         reactor.callLater(1, modeMap[self.runner.mode])
      else:
         raise Exception("mode '%s' not implemented" % self.runner.mode)
      #reactor.callLater(1, self.printDeviceEdsUris)
      #reactor.callLater(1, self.printDeviceEdsUris2)
      #reactor.callLater(1, self.printDeviceIds)
      #reactor.callLater(1, self.printDeviceIds2)


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

      #self.mode = str(self.options['mode'])
      if self.options['show']:
         self.mode = 'show'
         self.modeArg = self.options['show']
      elif self.options['list']:
         self.mode = 'list'
         self.modeArg = self.options['list']
      else:
         self.mode = None
         self.modeArg = None

      self.edsDirectory = os.path.abspath(str(self.options['eds']))

      
   def startService(self):
      if self.mode == 'uuid':
         u = uuid.uuid4()
         print u
         print u.hex
         print '{' + ', '.join(['0x' + x for x in splitlen(u.hex, 2)]) + '}'
         return False

      elif self.mode == 'verify':
         db = SrdpEdsDatabase()
         db.loadFromDir(self.edsDirectory)
         return False

      elif self.mode in ['check', 'list', 'show']:
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
