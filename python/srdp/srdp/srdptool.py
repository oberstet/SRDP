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

__all__ = ('run',)


import sys, os, struct, binascii, uuid, json
from pprint import pprint

if sys.platform == 'win32':
   ## on windows, we need to use the following reactor for serial support
   ## http://twistedmatrix.com/trac/ticket/3802
   ##
   from twisted.internet import win32eventreactor
   win32eventreactor.install()

from twisted.internet import reactor
from twisted.python import log, usage
from twisted.python.failure import Failure
from twisted.internet.defer import Deferred, \
                                   DeferredList, \
                                   returnValue, \
                                   inlineCallbacks
from twisted.internet.serialport import SerialPort

from srdp import SrdpEdsDatabase, \
                 SrdpHostProtocol, \
                 SrdpFrameHeader, \
                 SrdpException



def splitlen(seq, length):
   """
   Splits a string into fixed size parts.
   """
   return [seq[i:i+length] for i in range(0, len(seq), length)]


def tabify(fields, formats, truncate = 120):
   """
   Tabified output formatting.
   """

   ## compute total length of all fields
   ##
   totalLen = 0
   flexIndicators = 0
   flexIndicatorIndex = None
   for i in xrange(len(formats)):
      ffmt = formats[i][1:]
      if ffmt != "*":
         totalLen += int(ffmt)
      else:
         flexIndicators += 1
         flexIndicatorIndex = i

   if flexIndicators > 1:
      raise Exception("more than 1 flex field indicator")

   ## reserve space for column separators (" | " or " + ")
   ##
   totalLen += 3 * (len(formats) - 1)

   if totalLen > truncate:
      raise Exception("cannot fit content in truncate length %d" % truncate)

   r = []
   for i in xrange(len(formats)):

      if i == flexIndicatorIndex:
         N = truncate - totalLen
      else:
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

   MODES = ['verify', 'check', 'uuid', 'list', 'show', 'listen']

   optParameters = [
      ['mode', 'm', None, 'Mode, one of: %s [required]' % ', '.join(MODES)],
      ['show', 's', None, ''],
      ['read', 'r', None, ''],
      ['list', 'l', None, ''],
      ['with', 'w', None, ''],
      ['eds', 'e', None, 'Path to directory with EDS files (recursively crawled).'],
      ['baudrate', 'b', 115200, 'Serial port baudrate.'],
      ['port', 'p', 11, 'Serial port to use (e.g. "11" for COM12 or "/dev/ttxACM0")'],
      ['truncate', 't', 110, 'Truncate output line length.'],
   ]

   optFlags = [
      ['debug', 'd', 'Activate debug output.']
   ]

   def postOptions(self):

      #print "XX", self['write']
      #sys.exit(0)

      return

      if not self['mode']:
         raise usage.UsageError, "a mode must be specified to run!"

      if self['mode'] not in SrdpToolOptions.MODES:
         raise usage.UsageError, "invalid mode %s" % self['mode']

      if self['mode'] in ['verify', 'check', 'list', 'read']:
         if not self['eds']:
            raise usage.UsageError, "a directory with EDS files is required!"


SRDP_STYPE_TO_PTYPE = {'int8': 'b',
                       'uint8': 'b',
                       'int16': 'h',
                       'uint16': 'H',
                       'int32': 'l',
                       'uint32': 'L',
                       'int64': 'q',
                       'uint64': 'Q',
                       'float': 'f',
                       'double': 'd'
                       }


def parse(reg, data):
   ## string
   ##
   if reg['type']  == 'char' and reg['count'] in ['uint8', 'uint16']:
      if reg['count'] == 'uint8':
         return data[1:].decode('utf8')
      elif reg['count'] == 'uint16':
         return data[2:].decode('utf8')

   elif type(reg['type']) == list:
      o = {}
      td = '<'
      for field in reg['type']:
         td += SRDP_STYPE_TO_PTYPE[field['type']]
      tval = list(struct.unpack(td, data))
      for i in xrange(len(tval)):
         o[str(reg['type'][i]['field'])] = tval[i]

      return o

   elif type(reg['count']) == int:
      if reg['count'] == 1:
         fmt = SRDP_STYPE_TO_PTYPE[reg['type']]
         tval = struct.unpack(fmt, data)[0]
         return tval
      else:
         if reg['type'] == 'uint8':
            return '0x' + binascii.hexlify(data)

   else:
      return '?'


class SrdpToolHostProtocol(SrdpHostProtocol):

   IDX_REG_ID = 1
   IDX_REG_EDS = 2
   IDX_REG_HW_VERSION = 3
   IDX_REG_SW_VERSION = 4
   IDX_REG_DEVICES = 5
   IDX_REG_FREE_RAM = 1024


   @inlineCallbacks
   def getUuid(self, device = 1):
      res = yield self.readRegister(device, self.IDX_REG_ID)
      returnValue(res)


   @inlineCallbacks
   def getEdsUri(self, device = 1):
      res = yield self.readRegister(device, self.IDX_REG_EDS)
      returnValue(res[2:])


   @inlineCallbacks
   def getDevices(self):
      res = yield self.readRegister(1, self.IDX_REG_DEVICES)
      count = struct.unpack("<H", res[:2])
      val = list(struct.unpack("<%dH" % count, res[2:]))
      returnValue(val)


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

         print
         print "SRDP Adapter Information"
         print "========================"
         print
         print "Adapter UUID       : %s" % (binascii.hexlify(im[1]))
         print "Adapter EDS URI    : %s" % (em[1])
         print "Connected Devices  :"

         LINEFORMAT = ['r8', 'l32', 'l*', 'r9']
         print
         print tabify(["Device:", "UUID", "EDS URI", "Registers"], LINEFORMAT, self.runner._truncate)
         print tabify(None, LINEFORMAT, self.runner._truncate)
         for i in sorted(em.keys()):
            eds = self.runner.edsDatabase.getEdsByUri(em[i])
            print tabify([i, binascii.hexlify(im[i]), em[i], len(eds.registersByIndex)], LINEFORMAT, self.runner._truncate)
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

         print
         print "SRDP Device Information"
         print "======================="
         print
         print "Device Index       : %d" % device
         print "Device UUID        : %s" % (binascii.hexlify(uuid))
         print "Device EDS URI     : %s" % (edsUri)

         eds = self.runner.edsDatabase.getEdsByUri(edsUri)
         print "Register Map       :"
         print

         LINEFORMAT = ["r10", "l24", "l10", "l8", "l8", "l8", "l10", "l*"]

         print tabify(["Register:", "Path", "Access", "Optional", "Count", "Type", "Component", "Description"], LINEFORMAT, self.runner._truncate)
         print tabify(None, LINEFORMAT, self.runner._truncate)

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
                          reg['desc']],
                          LINEFORMAT,
                          self.runner._truncate)
            if rtype == 'dict:':
               for att in reg['type']:
                  print tabify(["",
                                "",
                                "",
                                "",
                                "",
                                "  " + att["type"],
                                att["field"],
                                att["desc"]],
                                LINEFORMAT,
                                self.runner._truncate)
         print

      except Exception, e:
         print "Error:", e
      self.transport.loseConnection()


   #@inlineCallbacks
   def writeRegisters(self, device, eds, items):
      for reg, data in items:
         if type(reg) == int:
            index = eds.registersByIndex.get(reg, None)['index']
         elif type(reg) in [str, unicode]:
            index = eds.registersByPath.get(reg, None)['index']
         else:
            raise Exception("no such register")
         #print device, index, data
         # unparse + writeregister
         #returnValue(None)


   @inlineCallbacks
   def readDevice(self):
      try:
         device = int(self.runner.modeArg)
         uuid = yield self.getUuid(device)
         edsUri = yield self.getEdsUri(device)
         eds = self.runner.edsDatabase.getEdsByUri(edsUri)

         print
         print "SRDP Device Information"
         print "======================="
         print
         print "Device Index       : %d" % device
         print "Device UUID        : %s" % (binascii.hexlify(uuid))
         print "Device EDS URI     : %s" % (edsUri)

         eds = self.runner.edsDatabase.getEdsByUri(edsUri)

         if self.runner._with:
            res = self.writeRegisters(device, eds, self.runner._with)

         print "Register Values    :"
         print

         LINEFORMAT = ["r10", "l24", "l*"]

         print tabify(["Register:", "Path", "Current Value"], LINEFORMAT, self.runner._truncate)
         print tabify(None, LINEFORMAT, self.runner._truncate)

         for k in sorted(eds.registersByIndex.keys()):
            reg = eds.registersByIndex[k]
            if reg['access'] in ['read', 'readwrite']:
               try:
                  val = yield self.readRegister(device, reg['index'])
               except Exception, e:
                  if reg['optional'] and e.args[0] == SrdpFrameHeader.SRDP_ERR_NO_SUCH_REGISTER:
                     print tabify([k, reg['path'], '- (not implemented)'], LINEFORMAT, self.runner._truncate)
                  else:
                     print tabify([k, reg['path'], 'Error: %s.' % e.args[1]], LINEFORMAT, self.runner._truncate)
               else:
                  val = parse(reg, val)
                  print tabify([k, reg['path'], val], LINEFORMAT, self.runner._truncate)

         print

      except Exception, e:
         print "Error:", e
      self.transport.loseConnection()



   def connectionMade(self):
      print 'Serial device connected.'

      delay = 1
      modeMap = {'list': self.listDevices,
                 'show': self.showDevice,
                 'read': self.readDevice}

      if modeMap.has_key(self.runner.mode):
         print "Giving the device %s seconds to get ready .." % delay
         reactor.callLater(delay, modeMap[self.runner.mode])
      else:
         raise Exception("mode '%s' not implemented" % self.runner.mode)


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

      self._truncate = int(self.options['truncate'])

      if self.options['with']:
         try:
            self._with = json.loads(self.options['with'])
            if type(self._with) != list:
               raise Exception("--with value must be a JSON list")
            for l in self._with:
               if type(l) != list or len(l) != 2:
                  raise Exception("--with value must be a JSON list of pairs (lists of length 2)")
            print self._with
         except Exception, e:
            raise Exception("Syntax error in 'with' JSON value [%s]" % e)
      else:
         self._with = None

      print "SRDP Tool running X command"
      #self.mode = str(self.options['mode'])
      if self.options['show']:
         self.mode = 'show'
         self.modeArg = self.options['show']
      elif self.options['list']:
         self.mode = 'list'
         self.modeArg = self.options['list']
      elif self.options['read']:
         self.mode = 'read'
         self.modeArg = self.options['read']
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

      elif self.mode in ['check', 'list', 'show', 'read']:
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
# python srdptool.py -e ../../../eds/ -p 11 --read 4 --with '[["/slider#watch", 1], ["/slider#urate", 13.9]]'

if __name__ == '__main__':
   run()
