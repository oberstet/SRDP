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


import sys, os, struct, binascii, uuid, json, pkg_resources
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
                 SrdpProtocol, \
                 SrdpStreamProtocol, \
                 SrdpDatagramProtocol, \
                 SrdpFrameHeader, \
                 SrdpException



def splitlen(seq, length):
   """
   Splits a string into fixed size parts.
   """
   return [seq[i:i+length] for i in range(0, len(seq), length)]



def tabify(fields, formats, truncate = 120, filler = ['-', '+']):
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
         r.append(filler[0] * l)
      else:
         raise Exception("invalid field format")

   if m == '+':
      return (filler[0] + filler[1] + filler[0]).join(r)
   else:
      return ' | '.join(r)



class SrdpToolProtocol(SrdpProtocol):

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
         print "SRDP Adapter: Connected Devices"
         print "==============================="
         print
         print "Adapter UUID    : %s" % (binascii.hexlify(im[1]))
         print "Adapter EDS URI : %s" % (em[1])
         print

         LINEFORMAT = ['r7', 'l32', 'l*', 'c9']
         print tabify(None, LINEFORMAT, self.runner._truncate)
         print tabify(["Device", "UUID", "EDS URI", "Registers"], LINEFORMAT, self.runner._truncate)
         print tabify(None, LINEFORMAT, self.runner._truncate)

         for i in sorted(em.keys()):
            if i == 2:
               print tabify(None, LINEFORMAT, self.runner._truncate, filler = ['.', '|'])
            eds = self.runner.edsDatabase.getEdsByUri(em[i])
            print tabify([i, binascii.hexlify(im[i]), em[i], len(eds.registersByIndex)], LINEFORMAT, self.runner._truncate)

         print tabify(None, LINEFORMAT, self.runner._truncate)
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
         print "SRDP Device: Register Map"
         print "========================="
         print
         print "Device Index   : %d" % device
         print "Device UUID    : %s" % (binascii.hexlify(uuid))
         print "Device EDS URI : %s" % (edsUri)
         print

         eds = self.runner.edsDatabase.getEdsByUri(edsUri)
         if eds is None:
            raise Exception("EDS for device not in database")

         if self.runner._with:
            res = self.writeRegisters(device, eds, self.runner._with)

         LINEFORMAT = ["r9", "l30", "l10", "l8", "l8", "l8", "l10", "l*"]

         print tabify(None, LINEFORMAT, self.runner._truncate)
         print tabify(["Register", "Path", "Access", "Optional", "Count", "Type", "Component", "Description"], LINEFORMAT, self.runner._truncate)
         print tabify(None, LINEFORMAT, self.runner._truncate)

         sysRegsDone = False
         for k in sorted(eds.registersByIndex.keys()):

            if not sysRegsDone and k >= 1024:
               print tabify(None, LINEFORMAT, self.runner._truncate, filler = ['.', '|'])
               sysRegsDone = True

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

         print tabify(None, LINEFORMAT, self.runner._truncate)
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
         print "SRDP Device: Register Values"
         print "============================"
         print
         print "Device Index   : %d" % device
         print "Device UUID    : %s" % (binascii.hexlify(uuid))
         print "Device EDS URI : %s" % (edsUri)
         print

         eds = self.runner.edsDatabase.getEdsByUri(edsUri)
         if eds is None:
            raise Exception("EDS for device not in database")

         if self.runner._with:
            res = self.writeRegisters(device, eds, self.runner._with)

         LINEFORMAT = ["r9", "l30", "l*"]

         print tabify(None, LINEFORMAT, self.runner._truncate)
         print tabify(["Register", "Path", "Current Value"], LINEFORMAT, self.runner._truncate)
         print tabify(None, LINEFORMAT, self.runner._truncate)

         sysRegsDone = False
         for k in sorted(eds.registersByIndex.keys()):

            if not sysRegsDone and k >= 1024:
               print tabify(None, LINEFORMAT, self.runner._truncate, filler = ['.', '|'])
               sysRegsDone = True

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

         print tabify(None, LINEFORMAT, self.runner._truncate)
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
         print "SRDP Device: Monitor Registers"
         print "=============================="
         print
         print "Device Index   : %d" % device
         print "Device UUID    : %s" % (binascii.hexlify(uuid))
         print "Device EDS URI : %s" % (edsUri)
         print

         eds = self.runner.edsDatabase.getEdsByUri(edsUri)
         if eds is None:
            raise Exception("EDS for device not in database")

         if self.runner._with:
            res = self.writeRegisters(device, eds, self.runner._with)

         LINEFORMAT = ["r9", "l30", "l*"]
         self.LINES = 0

         def _printHeader():
            print tabify(None, LINEFORMAT, self.runner._truncate)
            print tabify(["Register", "Path", "Current Value"], LINEFORMAT, self.runner._truncate)
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


   def transportReady(self):
      print 'Serial device connected.'

      delay = self.runner.delay
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


   def transportLost(self, reason):
      print 'Serial device disconnected.'
      if self._debug:
         log.msg(reason)
      reactor.stop()


class SrdpToolStreamProtocol(SrdpToolProtocol, SrdpStreamProtocol):

   def __init__(self, *args, **kwargs):
      SrdpToolProtocol.__init__(self, *args, **kwargs)
      SrdpStreamProtocol.__init__(self, *args, **kwargs)


class SrdpToolDatagramProtocol(SrdpToolProtocol, SrdpDatagramProtocol):

   def __init__(self, *args, **kwargs):
      SrdpToolProtocol.__init__(self, *args, **kwargs)
      SrdpDatagramProtocol.__init__(self, *args, **kwargs)


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



from twisted.internet.protocol import DatagramProtocol


class UdpClient(DatagramProtocol):

   def __init__(self, ip, port, num = 10000, debug = False):
      self._ip = ip
      self._port = port
      self._debug = debug
      self._count = 0
      self._num = num

   def startProtocol(self):
      print "started"
      self.sendHello()

   def sendHello(self):
      for i in xrange(1):
         self.transport.write("Hello!", (self._ip, self._port))
         print "Hello!", (self._ip, self._port)
      print
      reactor.callLater(1, self.sendHello)

   def datagramReceived(self, data, (host, port)):
      if self._debug:
         print "received %r from %s:%d" % (data, host, port)
      if self._count < self._num:
         self.transport.write(data, (host, port))
         self._count += 1
         if self._count % 1000 == 0:
            print self._count
      else:
         reactor.stop()



class SrdpToolRunner(object):

   def startService(self):

      ## parse command line args
      ##
      parser = argparse.ArgumentParser(prog = "srdptool",
                                       description = "SRDP Tool v%s" % __version__)

      group0 = parser.add_argument_group(title = 'SRDP transport and EDS directories')
      group0.add_argument("-t",
                          "--transport",
                          required = True,
                          nargs = 2,
                          metavar = ('<transport>', '<transport parameters>'),
                          action = "store",
                          help = "SRDP transport to use. Eg. 'serial /dev/ttxACM0:19200' or 'serial com3:115200'")

      group0.add_argument("-e",
                          "--eds",
                          type = str,
                          action = "append",
                          metavar = "<directory path>",
                          help = "Path to EDS directory.")

      group1dummy = parser.add_argument_group(title = 'Run mode (one of the following)')
      group1 = group1dummy.add_mutually_exclusive_group(required = True)

      group1.add_argument("--check",
                          help = "Load and check the EDS database.",
                          action = "store_true")

      group1.add_argument("--list",
                          help = "List the devices currently connected to the adapter.",
                          action = "store_true")

      group1.add_argument("--show",
                          help = "Show information for given device.",
                          metavar = "<device>",
                          type = int,
                          action = "store")

      group1.add_argument("--read",
                          help = "Read current register values for given device (for all register that allow 'read' access).",
                          metavar = "<device>",
                          type = int,
                          action = "store")

      group1.add_argument("--monitor",
                          help = "Monitor the given device for notify events.",
                          metavar = "<device>",
                          type = int,
                          action = "store")

      group1.add_argument("--uuid",
                          type = int,
                          help = "Generate given number of UUIDs.",
                          metavar = "<count>",
                          action = "store")

      group2 = parser.add_argument_group(title = 'Register writing (optional)')
      group2.add_argument("--write",
                          action = "append",
                          metavar = ('<register>', '<value>'),
                          nargs = 2,
                          help = "Write register values before main action. Register can be specified either by index or path.")

      group3 = parser.add_argument_group(title = 'Other options')
      group3.add_argument("--delay",
                          help = "Delay to wait for (serial) device to get ready (seconds|float).",
                          type = float,
                          default = 1.0,
                          action = "store")

      group3.add_argument("--linelength",
                          type = int,
                          default = 120,
                          metavar = "<line length>",
                          help = "Truncate display line length to given number of chars.")

      group3.add_argument("-d",
                          "--debug",
                          help = "Enable debug output.",
                          action = "store_true")

      args = parser.parse_args()

      self.delay = args.delay

      self.debug = args.debug
      if self.debug:
         log.startLogging(sys.stdout)

      self.edsDirectories = []

      if args.eds:
         for e in args.eds:
            self.edsDirectories.append(os.path.abspath(e))

      self.edsDirectories.append(pkg_resources.resource_filename("srdp", "eds"))

      self._truncate = int(args.linelength)

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


      self._transportType = args.transport[0].strip().lower()

      if self._transportType == 'serial':
         s = args.transport[1].split(':')
         self.port = s[0].strip().lower()
         if len(s) > 1:
            self.baudrate = int(s[1])
            if self.baudrate not in [300, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 38400, 57600, 115200, 230400]:
               raise Exception("invalid baudrate")
      elif self._transportType == 'udp':
         s = args.transport[1].split(':')
         self.host = s[0].strip().lower()
         if len(s) > 1:
            self.port = int(s[1])
      else:
         raise Exception("invalid transport %s" % self._transportType)
      

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

      
      if self.mode == 'uuid':

         for i in xrange(self.modeArg):
            u = uuid.uuid4()
            print
            print "UUID    :", u
            print "HEX     :", u.hex
            print "C/C++   :", '{' + ', '.join(['0x' + x for x in splitlen(u.hex, 2)]) + '}'
         return False

      elif self.mode in ['check', 'list', 'show', 'read', 'monitor']:

         self.edsDatabase = SrdpEdsDatabase(debug = self.debug)

         total = 0
         for d in self.edsDirectories:
            l = self.edsDatabase.loadFromDir(d)
            total += l
            print "Ok: loaded and checked %d EDS files from %s" % (l, d)

         l = self.edsDatabase.check()
         print "EDS database with %d objects initiated." % l

         if self.mode == 'check':
            return False

         try:
            self.port = int(self.port)
         except:
            # on RaspberryPi, Serial-over-USB appears as /dev/ttyACM0
            pass


         if self._transportType == 'serial':

            print "Connecting to serial port %s at %d baud .." % (self.port, self.baudrate)
            
            self.protocol = SrdpToolStreamProtocol(debug = self.debug)
            self.protocol.runner = self
            self.serialPort = SerialPortFix(self.protocol, self.port, reactor, baudrate = self.baudrate)

         elif self._transportType == 'udp':

            print "Connecting over UDP transport .."

            self.protocol = SrdpToolDatagramProtocol(debug = self.debug)
            self.protocol.runner = self
            self.serialPort = None
            reactor.listenUDP(1910, self.protocol)

         else:
            raise Exception("invalid transport %s" % self._transportType)

         return True

      else:
         raise Exception("logic error")



def run():
   runner = SrdpToolRunner()
   if runner.startService():
      reactor.run()

   
if __name__ == '__main__':
   run()
