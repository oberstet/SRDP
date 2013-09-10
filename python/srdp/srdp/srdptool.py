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

from interfaces import ISrdpProvider

import zope
from zope.interface import implementer



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


@implementer(ISrdpProvider)
class SrdpToolProvider(object):

   IDX_REG_ID = 1
   IDX_REG_EDS = 2
   IDX_REG_DEVICES = 5

   def __init__(self, config, edsDb, debug = False):
      self._config = config
      self._edsDb = edsDb
      self._debug = debug


   @inlineCallbacks
   def getUuid(self, device = 1):
      res = yield self.channel.readRegister(device, self.IDX_REG_ID)
      returnValue(res)


   @inlineCallbacks
   def getEdsUri(self, device = 1):
      res = yield self.channel.readRegister(device, self.IDX_REG_EDS)
      returnValue(res[2:])


   @inlineCallbacks
   def getDevices(self):
      res = yield self.channel.readRegister(1, self.IDX_REG_DEVICES)
      count = struct.unpack("<H", res[:2])
      val = list(struct.unpack("<%dH" % count, res[2:]))
      returnValue(val)


   def getDeviceEdsMap(self):
      dret = Deferred()

      d = self.channel.readRegister(1, self.IDX_REG_DEVICES)

      def _getDeviceListSuccess(res):
         count = struct.unpack("<H", res[:2])
         devices = list(struct.unpack("<%dH" % count, res[2:]))
         devices.append(1)

         dl = []
         for i in devices:
            dl.append(self.channel.readRegister(i, self.IDX_REG_EDS))

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

      d = self.channel.readRegister(1, self.IDX_REG_DEVICES)

      def _getDeviceListSuccess(res):
         count = struct.unpack("<H", res[:2])
         devices = list(struct.unpack("<%dH" % count, res[2:]))
         devices.append(1)

         dl = []
         for i in devices:
            dl.append(self.channel.readRegister(i, self.IDX_REG_ID))

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
         print tabify(None, LINEFORMAT, self.LINELENGTH)
         print tabify(["Device", "UUID", "EDS URI", "Registers"], LINEFORMAT, self.LINELENGTH)
         print tabify(None, LINEFORMAT, self.LINELENGTH)

         for i in sorted(em.keys()):
            if i == 2:
               print tabify(None, LINEFORMAT, self.LINELENGTH, filler = ['.', '|'])
            eds = self._edsDb.getEdsByUri(em[i])
            print tabify([i, binascii.hexlify(im[i]), em[i], len(eds.registersByIndex)], LINEFORMAT, self.LINELENGTH)

         print tabify(None, LINEFORMAT, self.LINELENGTH)
         print
      #except Exception, e:
      #   raise e
      finally:
         self.channel.close()


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

         eds = self._edsDb.getEdsByUri(edsUri)
         if eds is None:
            raise Exception("EDS for device not in database")

         if self.runner._with:
            res = self.writeRegisters(device, eds, self.runner._with)

         LINEFORMAT = ["r9", "l30", "l10", "l8", "l8", "l8", "l10", "l*"]

         print tabify(None, LINEFORMAT, self.LINELENGTH)
         print tabify(["Register", "Path", "Access", "Optional", "Count", "Type", "Component", "Description"], LINEFORMAT, self.LINELENGTH)
         print tabify(None, LINEFORMAT, self.LINELENGTH)

         sysRegsDone = False
         for k in sorted(eds.registersByIndex.keys()):

            if not sysRegsDone and k >= 1024:
               print tabify(None, LINEFORMAT, self.LINELENGTH, filler = ['.', '|'])
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
                          self.LINELENGTH)
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
                                self.LINELENGTH)

         print tabify(None, LINEFORMAT, self.LINELENGTH)
         print

      except Exception, e:
         print "Error:", e
      self.channel.close()


   def writeRegistersAsync(self, device, eds, items):
      dl = []
      for reg, value in items:
         register = eds.getRegister(reg)
         data = eds.serialize(reg, value)
         self.channel.writeRegister(device, register['index'], data)
         dl.append(self.channel.writeRegister(device, register['index'], data))
      return DeferredList(dl)


   #@inlineCallbacks
   def writeRegisters(self, device, eds, items):
      for reg, value in items:
         register = eds.getRegister(reg)
         data = eds.serialize(reg, value)
         #res = yield self.writeRegister(device, register['index'], data)
         self.channel.writeRegister(device, register['index'], data)
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

         eds = self._edsDb.getEdsByUri(edsUri)
         if eds is None:
            raise Exception("EDS for device not in database")

         if self.runner._with:
            res = self.writeRegisters(device, eds, self.runner._with)

         LINEFORMAT = ["r9", "l30", "l*"]

         print tabify(None, LINEFORMAT, self.LINELENGTH)
         print tabify(["Register", "Path", "Current Value"], LINEFORMAT, self.LINELENGTH)
         print tabify(None, LINEFORMAT, self.LINELENGTH)

         sysRegsDone = False
         for k in sorted(eds.registersByIndex.keys()):

            if not sysRegsDone and k >= 1024:
               print tabify(None, LINEFORMAT, self.LINELENGTH, filler = ['.', '|'])
               sysRegsDone = True

            reg = eds.registersByIndex[k]
            if reg['access'] in ['read', 'readwrite']:
               try:
                  data = yield self.readRegister(device, reg['index'])
               except Exception, e:
                  if reg['optional'] and e.args[0] == SrdpFrameHeader.SRDP_ERR_NO_SUCH_REGISTER:
                     print tabify([k, reg['path'], '- (not implemented)'], LINEFORMAT, self.LINELENGTH)
                  else:
                     print tabify([k, reg['path'], 'Error: %s.' % e.args[1]], LINEFORMAT, self.LINELENGTH)
               else:
                  val = eds.unserialize(k, data)
                  print tabify([k, reg['path'], val], LINEFORMAT, self.LINELENGTH)

         print tabify(None, LINEFORMAT, self.LINELENGTH)
         print

      except Exception, e:
         print
         print "Error:", e
         print

      finally:
         self.channel.close()


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

         eds = self._edsDb.getEdsByUri(edsUri)
         if eds is None:
            raise Exception("EDS for device not in database")

         if self.runner._with:
            res = self.writeRegisters(device, eds, self.runner._with)

         LINEFORMAT = ["r9", "l30", "l*"]
         self.LINES = 0

         def _printHeader():
            print tabify(None, LINEFORMAT, self.LINELENGTH)
            print tabify(["Register", "Path", "Current Value"], LINEFORMAT, self.LINELENGTH)
            print tabify(None, LINEFORMAT, self.LINELENGTH)

         _printHeader()

         def _onRegisterChange(device, register, position, data):
            self.LINES += 1
            if (self.LINES % 40) == 0:
               _printHeader()
            reg = eds.getRegister(register)
            val = eds.unserialize(register, data)
            print tabify([reg['index'], reg['path'], val], LINEFORMAT, self.LINELENGTH)

         self.onRegisterChange = _onRegisterChange

         if self.runner._with:
            res = self.writeRegisters(device, eds, self.runner._with)

      except Exception, e:
         print
         print "Error:", e
         print

      #finally:
      #   self.loseTransport()


   def onChannelOpen(self, channel):
      print 'Serial device connected.'
      self.channel = channel

      delay = self._config['delay']
      print "Giving the device %s seconds to get ready .." % delay

      mode = self._config['mode']
      modearg = self._config['modearg']

      self.LINELENGTH = self._config['linelength']

      if mode == 'show':
         reactor.callLater(delay, self.showDevice, device = int(modearg))
      elif mode == 'read':
         reactor.callLater(delay, self.readDevice, device = int(modearg))
      elif mode == 'list':
         reactor.callLater(delay, self.listDevices)
      elif mode == 'monitor':
         reactor.callLater(delay, self.monitorDevice, device = int(modearg))
      else:
         raise Exception("mode '%s' not implemented" % mode)


   def onChannelClose(self, reason):
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

   def argparse(self):

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

      ## debug output
      ##
      debug = args.debug
      if debug:
         log.startLogging(sys.stdout)

      ## delay main action
      ##
      delay = args.delay

      ## load EDS files from these directories
      ##
      edsDirectories = []
      if args.eds:
         for e in args.eds:
            edsDirectories.append(os.path.abspath(e))
      edsDirectories.append(pkg_resources.resource_filename("srdp", "eds"))

      ## truncate line length in shell output
      ##
      linelength = int(args.linelength)

      ## write these values to register before main action
      ##
      write = None
      if args.write:
         write = []
         for reg, val in args.write:
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
            write.append([reg, val])

      ## SRDP transport
      ##
      transport = args.transport[0].strip().lower()
      host = None
      port = None
      baudrate = None
      if transport == 'serial':
         s = args.transport[1].split(':')
         port = s[0].strip().lower()
         try:
            port = int(port)
         except:
            # on RaspberryPi, Serial-over-USB appears as /dev/ttyACM0
            pass
         baudrate = 115200
         if len(s) > 1:
            baudrate = int(s[1])
            if baudrate not in [300, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 38400, 57600, 115200, 230400]:
               raise Exception("invalid baudrate")
      elif transport == 'udp':
         s = args.transport[1].split(':')
         host = s[0].strip().lower()
         port = 1910
         if len(s) > 1:
            port = int(s[1])
      else:
         raise Exception("invalid transport %s" % transport)
      
      ## run mode
      ##
      mode = None
      modeArg = None
      if args.uuid:
         mode = 'uuid'
         modeArg = int(args.uuid)
      elif args.check:
         mode = 'check'
      elif args.list:
         mode = 'list'
      elif args.show:
         mode = 'show'
         modeArg = int(args.show)
      elif args.read:
         mode = 'read'
         modeArg = int(args.read)
      elif args.monitor:
         mode = 'monitor'
         modeArg = int(args.monitor)
      else:
         raise Exception("logic error")

      config = {}
      config['debug'] = debug
      config['transport'] = transport
      config['mode'] = mode
      config['modearg'] = modeArg
      config['delay'] = delay
      config['edsdirs'] = edsDirectories
      config['write'] = write
      config['host'] = host
      config['port'] = port
      config['baudrate'] = baudrate
      config['linelength'] = linelength

      return config


   def startService(self):

      config = self.argparse()

      ## do it ..
      ##
      if config['mode'] == 'uuid':

         for i in xrange(config['modearg']):
            u = uuid.uuid4()
            print
            print "UUID    :", u
            print "HEX     :", u.hex
            print "C/C++   :", '{' + ', '.join(['0x' + x for x in splitlen(u.hex, 2)]) + '}'

         return False

      elif config['mode'] in ['check', 'list', 'show', 'read', 'monitor']:

         edsDb = SrdpEdsDatabase(debug = config['debug'])

         total = 0
         for d in config['edsdirs']:
            l = edsDb.loadFromDir(d)
            total += l
            print "Ok: loaded and checked %d EDS files from %s" % (l, d)

         l = edsDb.check()
         print "EDS database with %d objects initiated." % l

         if config['mode'] == 'check':
            return False

         ## complex modes ..
         ##
         srdptool = SrdpToolProvider(config = config, edsDb = edsDb, debug = config['debug'])

         if config['transport'] == 'serial':

            print "Connecting to serial port %s at %d baud .." % (config['port'], config['baudrate'])
            
            protocol = SrdpStreamProtocol(provider = srdptool, debug = config['debug'])
            serialPort = SerialPortFix(protocol, config['port'], reactor, baudrate = config['baudrate'])

         elif config['transport'] == 'udp':

            print "Connecting over UDP transport .."

            protocol = SrdpDatagramProtocol(provider = srdptool, debug = config['debug'])
            protocol._addr = (config['host'], config['port'])
            reactor.listenUDP(config['port'], protocol)

         else:
            raise Exception("logic error")

         return True

      else:
         raise Exception("logic error")



def run():
   runner = SrdpToolRunner()
   if runner.startService():
      reactor.run()



if __name__ == '__main__':
   run()
