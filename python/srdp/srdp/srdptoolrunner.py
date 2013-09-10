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

__all__ = ('SrdpToolRunner',)


import sys, os,  uuid, json, pkg_resources, argparse


from twisted.python import log
from twisted.internet.serialport import SerialPort

from _version import __version__

from srdp import SrdpStreamProtocol, SrdpDatagramProtocol
from eds import SrdpEdsDatabase

from srdptoolprovider import SrdpToolProvider



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
         port = s[0].strip()
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


   def startService(self, config, reactor):

      ## do it ..
      ##
      if config['mode'] == 'uuid':

         def splitlen(seq, length):
            ## Splits a string into fixed size parts.
            return [seq[i:i+length] for i in range(0, len(seq), length)]

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

            print "SRDP-over-Serial - connecting to %s at %d baud .." % (config['port'], config['baudrate'])
            
            protocol = SrdpStreamProtocol(provider = srdptool, debug = config['debug'])
            serialPort = SerialPortFix(protocol, config['port'], reactor, baudrate = config['baudrate'])

         elif config['transport'] == 'udp':

            print "SRDP-over UDP - connecting to %s:%d .." % (config['host'], config['port'])

            protocol = SrdpDatagramProtocol(provider = srdptool, addr = (config['host'], config['port']), debug = config['debug'])
            reactor.listenUDP(config['port'], protocol)

         else:
            raise Exception("logic error")

         return True

      else:
         raise Exception("logic error")
