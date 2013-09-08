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

try:
   import argparse
except:
   print "please install the argparse module"
   sys.exit(1)

if sys.platform == 'win32':
   ## on windows, we need to use the following reactor for serial support
   ## http://twistedmatrix.com/trac/ticket/3802
   ##
   from twisted.internet import win32eventreactor
   win32eventreactor.install()

from twisted.internet import reactor
from twisted.python import log
from twisted.python.failure import Failure
from twisted.internet.defer import Deferred, \
                                   DeferredList, \
                                   returnValue, \
                                   inlineCallbacks
from twisted.internet.serialport import SerialPort

from _version import __version__
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



class SrdpToolHostProtocol(SrdpHostProtocol):

   IDX_REG_ID = 1
   IDX_REG_EDS = 2
   IDX_REG_DEVICES = 5


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
      """
      List all devices currently connected to the adapter.
      """
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
   def showDevice(self, device):
      """
      Show information for specified device.
      """
      try:
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


   def writeRegistersAsync(self, device, eds, items):
      dl = []
      for reg, value in items:
         register = eds.getRegister(reg)
         data = eds.serialize(reg, value)
         self.writeRegister(device, register['index'], data)
         dl.append(self.writeRegister(device, register['index'], data))
      return DeferredList(dl)


   #@inlineCallbacks
   def writeRegisters(self, device, eds, items):
      for reg, value in items:
         register = eds.getRegister(reg)
         data = eds.serialize(reg, value)
         #res = yield self.writeRegister(device, register['index'], data)
         self.writeRegister(device, register['index'], data)
         #print "*", res


   @inlineCallbacks
   def readDevice(self, device):
      """
      Read all current values from device registers (that allow to "read").
      """
      try:
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
         if eds is None:
            raise Exception("EDS for device not in database")

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
                  data = yield self.readRegister(device, reg['index'])
               except Exception, e:
                  if reg['optional'] and e.args[0] == SrdpFrameHeader.SRDP_ERR_NO_SUCH_REGISTER:
                     print tabify([k, reg['path'], '- (not implemented)'], LINEFORMAT, self.runner._truncate)
                  else:
                     print tabify([k, reg['path'], 'Error: %s.' % e.args[1]], LINEFORMAT, self.runner._truncate)
               else:
                  val = eds.unserialize(k, data)
                  print tabify([k, reg['path'], val], LINEFORMAT, self.runner._truncate)

         print

      except Exception, e:
         print
         print "Error:", e
         print

      finally:
         self.transport.loseConnection()


   @inlineCallbacks
   def monitorDevice(self, device):
      """
      """
      try:
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
         if eds is None:
            raise Exception("EDS for device not in database")

         print "Watching Registers :"

         LINEFORMAT = ["r10", "l24", "l*"]
         self.LINES = 0

         def _printHeader():
            print
            print tabify(["Register:", "Path", "Current Value"], LINEFORMAT, self.runner._truncate)
            print tabify(None, LINEFORMAT, self.runner._truncate)

         _printHeader()

         def _onRegisterChange(device, register, position, data):
            self.LINES += 1
            if (self.LINES % 40) == 0:
               _printHeader()
            reg = eds.getRegister(register)
            val = eds.unserialize(register, data)
            print tabify([reg['index'], reg['path'], val], LINEFORMAT, self.runner._truncate)

         self.onRegisterChange = _onRegisterChange

         if self.runner._with:
            res = self.writeRegisters(device, eds, self.runner._with)

      except Exception, e:
         print
         print "Error:", e
         print

      #finally:
      #   self.transport.loseConnection()


   def connectionMade(self):
      print 'Serial device connected.'

      delay = 1.0
      print "Giving the device %s seconds to get ready .." % delay

      if self.runner.mode == 'show':
         reactor.callLater(delay, self.showDevice, device = int(self.runner.modeArg))
      elif self.runner.mode == 'read':
         reactor.callLater(delay, self.readDevice, device = int(self.runner.modeArg))
      elif self.runner.mode == 'list':
         reactor.callLater(delay, self.listDevices)
      elif self.runner.mode == 'monitor':
         reactor.callLater(delay, self.monitorDevice, device = int(self.runner.modeArg))
      else:
         raise Exception("mode '%s' not implemented" % self.runner.mode)


   def connectionLost(self, reason):
      print 'Serial device disconnected.'
      if self._debug:
         log.msg(reason)
      reactor.stop()



class SerialPortFix(SerialPort):
   """
   Workaround for the following issue on Windows:

   http://twistedmatrix.com/trac/ticket/1248
   http://stackoverflow.com/a/287293/884770
   """

   def __init__(self, *args, **kw):
      super(SerialPortFix, self).__init__(*args, **kw)
      self._tempDataBuffer = []

   def writeSomeData(self, data):
      return len(data)



class SrdpToolRunner(object):

   def __init__(self):

      parser = argparse.ArgumentParser(prog = "srdptool",
                                       description = "SRDP Tool v%s" % __version__,
                                       formatter_class = argparse.RawTextHelpFormatter)

      group0 = parser.add_argument_group(title = 'EDS database')
      group0.add_argument("-e",
                          "--eds",
                          type = str,
                          required = True,
                          metavar = "<EDS directory>",
                          help = "Path to EDS directory.")

      group1dummy = parser.add_argument_group(title = 'Run mode (one of the following)')
      group1 = group1dummy.add_mutually_exclusive_group(required = True)

      group1.add_argument(#"-c",
                          "--check",
                          help = "Load and check the EDS database.",
                          action = "store_true")

      group1.add_argument(#"-l",
                          "--list",
                          help = "List the devices currently connected to the adapter.",
                          action = "store_true")

      group1.add_argument(#"-s",
                          "--show",
                          help = "Show information for given device.",
                          metavar = "<device>",
                          type = int,
                          action = "store")

      group1.add_argument(#"-r",
                          "--read",
                          help = "Read current register values for given device (for all register that allow 'read' access).",
                          metavar = "<device>",
                          type = int,
                          action = "store")

      group1.add_argument(#"-m",
                          "--monitor",
                          help = "Monitor the given device for notify events.",
                          metavar = "<device>",
                          type = int,
                          action = "store")

      group1.add_argument(#"-u",
                          "--uuid",
                          type = int,
                          help = "Generate given number of UUIDs.",
                          metavar = "<count>",
                          action = "store")

      group2 = parser.add_argument_group(title = 'Register writing (optional)')
      group2.add_argument(#"-w",
                          "--write",
                          action = "append",
                          metavar = ('<register>', '<value>'),
                          nargs = 2,
                          help = "Write register values before main action. Register can be specified either by index or path.")

      group3 = parser.add_argument_group(title = 'Serial port configuration')
      group3.add_argument("-b",
                          "--baud",
                          type = int,
                          default = 115200,
                          choices = [300, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 38400, 57600, 115200, 230400],
                          metavar = "<serial baudrate>",
                          help = "Serial port baudrate in Bits/s.")

      group3.add_argument("-p",
                          "--port",
                          default = 11,
                          metavar = "<serial port>",
                          help = 'Serial port to use (e.g. "11" for COM12 or "/dev/ttxACM0")')

      group4 = parser.add_argument_group(title = 'Other options')
      group4.add_argument("-t",
                          "--truncate",
                          type = int,
                          default = 120,
                          metavar = "<line length>",
                          help = "Truncate display line length to given number of chars.")

      group4.add_argument("-d",
                          "--debug",
                          help = "Enable debug output.",
                          action = "store_true")

      args = parser.parse_args()

      self.debug = args.debug
      if self.debug:
         log.startLogging(sys.stdout)

      self.edsDirectory = os.path.abspath(str(args.eds))

      self._truncate = int(args.truncate)

      if args.write:
         self._with = []
         for reg, val in args.write:
            print reg, val
            try:
               reg = int(reg)
            except:
               try:
                  reg = str(reg)
               except Exception, e:
                  raise e
            try:
               val = json.loads(val)
            except Exception, e:
               raise e
            self._with.append([reg, val])
      else:
         self._with = None

      self.baudrate = int(args.baud)
      self.port = args.port

      if args.uuid:
         self.mode = 'uuid'
         self.modeArg = int(args.uuid)
      elif args.check:
         self.mode = 'check'
      elif args.list:
         self.mode = 'list'
      elif args.show:
         self.mode = 'show'
         self.modeArg = int(args.show)
      elif args.read:
         self.mode = 'read'
         self.modeArg = int(args.read)
      elif args.monitor:
         self.mode = 'monitor'
         self.modeArg = int(args.monitor)
      else:
         raise Exception("logic error")

      
   def startService(self):

      if self.mode == 'uuid':

         for i in xrange(self.modeArg):
            u = uuid.uuid4()
            print
            print "UUID    :", u
            print "HEX     :", u.hex
            print "C/C++   :", '{' + ', '.join(['0x' + x for x in splitlen(u.hex, 2)]) + '}'
         return False

      elif self.mode == 'check':

         db = SrdpEdsDatabase()
         l = db.loadFromDir(self.edsDirectory)

         print
         print "Ok: loaded and checked %d EDS files from %s" % (l, self.edsDirectory)
         print

         return False

      elif self.mode in ['list', 'show', 'read', 'monitor']:

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

   
if __name__ == '__main__':
   run()
