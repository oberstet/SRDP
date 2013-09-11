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

__all__ = ('SrdpToolProvider',)

import struct, binascii

import zope
from zope.interface import implementer

from twisted.internet import reactor
from twisted.python import log
from twisted.internet.defer import Deferred, \
                                   DeferredList, \
                                   returnValue, \
                                   inlineCallbacks

from srdp import SrdpFrameHeader
from interfaces import ISrdpProvider



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
   def listDevices(self, modearg):
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
      finally:
         self.channel.close()


   @inlineCallbacks
   def showDevice(self, modearg):
      """
      Show information for specified device.
      """
      try:
         device = int(modearg)
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

         if self._config['write']:
            res = self.writeRegisters(device, eds, self._config['write'])

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
      finally:
         self.channel.close()


   def writeRegistersAsync(self, device, eds, items):
      dl = []
      for reg, value in items:
         register, data = eds.serialize(reg, value)
         self.channel.writeRegister(device, register['index'], data)
         dl.append(self.channel.writeRegister(device, register['index'], data))
      return DeferredList(dl)


   #@inlineCallbacks
   def writeRegisters(self, device, eds, items):
      for reg, value in items:
         register, data = eds.serialize(reg, value)
         #res = yield self.writeRegister(device, register['index'], data)
         self.channel.writeRegister(device, register['index'], data)
         #print "*", res


   @inlineCallbacks
   def readDevice(self, modearg):
      """
      Read all current values from device registers (that allow to "read").
      """
      try:
         device = int(modearg)
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

         if self._config['write']:
            res = self.writeRegisters(device, eds, self._config['write'])

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
                  data = yield self.channel.readRegister(device, reg['index'])
               except Exception, e:
                  if reg['optional'] and e.args[0] == SrdpFrameHeader.SRDP_ERR_NO_SUCH_REGISTER:
                     print tabify([k, reg['path'], '- (not implemented)'], LINEFORMAT, self.LINELENGTH)
                  else:
                     print tabify([k, reg['path'], 'Error: %s.' % e.args[1]], LINEFORMAT, self.LINELENGTH)
               else:
                  _, val = eds.unserialize(k, data)
                  print tabify([k, reg['path'], val], LINEFORMAT, self.LINELENGTH)

         print tabify(None, LINEFORMAT, self.LINELENGTH)
         print

      finally:
         self.channel.close()


   @inlineCallbacks
   def monitorDevice(self, modearg):
      """
      """
      try:
         device = int(modearg)
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

         if self._config['write']:
            res = self.writeRegisters(device, eds, self._config['write'])

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
            reg, val = eds.unserialize(register, data)
            print tabify([reg['index'], reg['path'], val], LINEFORMAT, self.LINELENGTH)

         self.onRegisterChange = _onRegisterChange

         if self._config['write']:
            res = self.writeRegisters(device, eds, self._config['write'])

      except Exception, e:
         print
         print "Error:", e
         print
         self.channel.close()


   def onChannelOpen(self, channel):
      print 'Channel open ..'
      self.channel = channel

      if self._config['transport'] == 'serial':
         delay = self._config['delay']
      else:
         delay = None

      mode = self._config['mode']
      modearg = self._config['modearg']

      self.LINELENGTH = self._config['linelength']

      cmdmap = {'show': self.showDevice,
                'read': self.readDevice,
                'list': self.listDevices,
                'monitor': self.monitorDevice}

      if cmdmap.has_key(mode):
         if delay:
            print "Giving the device %s seconds to get ready .." % delay
            reactor.callLater(delay, cmdmap[mode], modearg)
         else:
            cmdmap[mode](modearg)
      else:
         raise Exception("mode '%s' not implemented" % mode)


   def onChannelClose(self, reason):
      print 'Channel closed.'
      if self._debug:
         log.msg(reason)
      reactor.stop()
