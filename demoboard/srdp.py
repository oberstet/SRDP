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

__all__ = ("SrdpProtocol", "SrdpHostProtocol",)

import struct, binascii
from collections import deque

## https://pypi.python.org/pypi/crcmod
import crcmod

from twisted.python import log
from twisted.internet.protocol import Protocol
from twisted.internet import reactor



class SrdpFrameHeader:

   SRDP_FT_REQ     = 0x01
   SRDP_FT_ACK     = 0x02
   SRDP_FT_ERROR   = 0x03

   SRDP_FT_NAME = {SRDP_FT_REQ: 'REQ', SRDP_FT_ACK: 'ACK', SRDP_FT_ERROR: 'ERR'}

   SRDP_OP_SYNC    = 0x00
   SRDP_OP_READ    = 0x01
   SRDP_OP_WRITE   = 0x02
   SRDP_OP_CHANGE  = 0x03

   SRDP_OP_NAME = {SRDP_OP_SYNC: 'SYNC', SRDP_OP_READ: 'READ', SRDP_OP_WRITE: 'WRITE', SRDP_OP_CHANGE: 'CHANGE'}

   SRDP_FRAME_HEADER_LEN = 12

   def __init__(self,
                seq = 0,
                frametype = 0,
                opcode = 0,
                device = 0,
                register = 0,
                position = 0,
                length = 0,
                crc16 = 0):
      self.seq = seq
      self.frametype = frametype
      self.opcode = opcode
      self.device = device
      self.register = register
      self.position = position
      self.length = length
      self.crc16 = crc16


   def reset(self):
      self.seq = 0
      self.frametype = 0
      self.opcode = 0
      self.device = 0
      self.register = 0
      self.position = 0
      self.length = 0
      self.crc16 = 0


   def __str__(self):
      return "seq = %d, frametype = %s, opcode = %s, device = %d, register = %d, position = %d, length = %d, crc = 0x%04x" % (self.seq, SrdpFrameHeader.SRDP_FT_NAME[self.frametype], SrdpFrameHeader.SRDP_OP_NAME[self.opcode], self.device, self.register, self.position, self.length, self.crc16)


   def computeCrc(self, data = None):

      crc = crcmod.predefined.PredefinedCrc("xmodem")

      header = struct.pack("<HHHHHH",
                           ((self.frametype & 0x03) << 14) | ((self.opcode & 0x03) << 12) | (self.device & 0x0fff),
                           self.seq,
                           self.register,
                           self.position,
                           self.length,
                           0)
      crc.update(header)

      if data:
         crc.update(data)

      return crc.crcValue


   def serialize(self):
      return struct.pack("<HHHHHH",
                         ((self.frametype & 0x03) << 14) | ((self.opcode & 0x03) << 12) | (self.device & 0x0fff),
                         self.seq,
                         self.register,
                         self.position,
                         self.length,
                         self.crc16)
   

   def parse(self, data):
      t = struct.unpack("<HHHHHH", data[0:SrdpFrameHeader.SRDP_FRAME_HEADER_LEN])
      self.frametype = (t[0] >> 14) & 0x03
      self.opcode = (t[0] >> 12) & 0x03
      self.device = t[0] & 0xfff
      self.seq = t[1]
      self.register = t[2]
      self.position = t[3]
      self.length = t[4]
      self.crc16 = t[5]


class SrdpProtocol(Protocol):

   def __init__(self, debug = False):
      self._debug = debug
      self._chopup = False
      self._seq = 0
      self._pending = {}

      self._received = []
      self._receivedNum = 0
      self._needed = SrdpFrameHeader.SRDP_FRAME_HEADER_LEN

      self._srdpFrameHeader = None
      self._srdpFrameData = None

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


   def _write(self, data):
      if self._debug:
         log.msg("Octets sent [data = %s]" % binascii.hexlify(data))

      if self._chopup:
         for c in data:
            self._send_queue.append(c)
         self._trigger()
      else:
         self.transport.write(data)


   def dataReceived(self, data):
      if self._debug:
         log.msg("Octets received [data = %s]" % binascii.hexlify(data))
      self._received.append(data)
      self._receivedNum += len(data)
      if self._receivedNum >= self._needed:
         data = ''.join(self._received)
         self._received = []
         self._receiveFrame(data)


   def _receiveFrame(self, data):
      if self._srdpFrameHeader is None:
         self._srdpFrameHeader = SrdpFrameHeader()
         self._srdpFrameHeader.parse(data[0:SrdpFrameHeader.SRDP_FRAME_HEADER_LEN])
         rest = data[SrdpFrameHeader.SRDP_FRAME_HEADER_LEN:]
         if False and (self._srdpFrameHeader.frametype, self._srdpFrameHeader.opcode) \
            in [(SrdpFrameHeader.SRDP_FT_REQ, SrdpFrameHeader.SRDP_OP_SYNC),
                (SrdpFrameHeader.SRDP_FT_REQ, SrdpFrameHeader.SRDP_OP_READ),
                (SrdpFrameHeader.SRDP_FT_ACK, SrdpFrameHeader.SRDP_OP_WRITE)]:
            self._srdpFrameHeader.dataLength = 0
         else:
            self._srdpFrameHeader.dataLength = self._srdpFrameHeader.length
         self._needed = self._srdpFrameHeader.dataLength
      else:
         if self._srdpFrameHeader.dataLength > 0:
            self._srdpFrameData = data[0:self._srdpFrameHeader.dataLength]
            rest = data[self._srdpFrameHeader.dataLength:]
         else:
            self._srdpFrameData = None
            rest = data
         self._frameReceived()

      if len(rest) < self._needed:
         self._received.append(rest)
         self._receivedNum = len(rest)
         # need to receive more data
      else:
         self._receiveFrame(rest)


   def _logFrame(self, msg, header, data):
      if data:
         d = binascii.hexlify(data)
      else:
         d = ''
      if len(d) > 64:
         d = d[:64] + ".."
      log.msg("%s [%s, data = '%s']" % (msg, header, d))


   def _frameReceived(self):
      if self._debug:
         self._logFrame("SRDP frame received", self._srdpFrameHeader, self._srdpFrameData)

      ## check frame CRC
      ##
      crc16 = self._srdpFrameHeader.computeCrc(self._srdpFrameData)
      if crc16 != self._srdpFrameHeader.crc16:
         print "CRC Error: computed = %s, received = %s" % (binascii.hexlify(struct.pack("<H", crc16)), binascii.hexlify(struct.pack("<H", self._srdpFrameHeader.crc16)))
         # FIXME: send ERR
      else:
         self._processFrame(self._srdpFrameHeader, self._srdpFrameData)

      ## reset incoming frame
      ##
      self._srdpFrameHeader = None
      self._srdpFrameData = None
      self._needed = SrdpFrameHeader.SRDP_FRAME_HEADER_LEN


   def _sendFrame(self, header, data = None):
      if header.frametype == SrdpFrameHeader.SRDP_FT_REQ:
         self._seq += 1
         header.seq = self._seq
         #self._pending[self._seq] = None # FIXME: return Deferred that yields read result
         header.crc16 = header.computeCrc(data)
         if data:
            wireData = header.serialize() + data
         else:
            wireData = header.serialize()
         self._write(wireData)

         if self._debug:
            self._logFrame("SRDP frame sent", header, data)



class SrdpHostProtocol(SrdpProtocol):

   def readRegister(self, device, register, position = 0, length = 0):
      frame = SrdpFrameHeader(frametype = SrdpFrameHeader.SRDP_FT_REQ,
                              opcode = SrdpFrameHeader.SRDP_OP_READ,
                              device = device,
                              register = register,
                              position = position,
                              length = length)
      self._sendFrame(frame)


   def writeRegister(self, device, register, data, position = 0):
      frame = SrdpFrameHeader(frametype = SrdpFrameHeader.SRDP_FT_REQ,
                              opcode = SrdpFrameHeader.SRDP_OP_WRITE,
                              device = device,
                              register = register,
                              position = position,
                              length = len(data))
      self._sendFrame(frame, data)


   def  onRegisterChange(self, device, register, position, data):
      pass


   def _processFrame(self, header, data):
      if header.frametype == SrdpFrameHeader.SRDP_FT_REQ and \
         header.opcode == SrdpFrameHeader.SRDP_OP_CHANGE:
         res = self.onRegisterChange(header.device, header.register, header.position, data)



class SrdpDriverProtocol(SrdpProtocol):

   def onRegisterRead(self, device, register, position, length):
      pass


   def onRegisterWrite(self, device, register, position, data):
      pass


   def changeRegister(self, device, register, position, data):
      pass



if __name__ == '__main__':

   # http://www.ross.net/crc/download/crc_v3.txt
   #http://www.mcgougan.se/universal_crc/

   # http://www.lammertbies.nl/comm/info/crc-calculation.html

   # CRCs for test string "123456789":
   #
   # 1 byte checksum      221
   # CRC-16               0xBB3D
   # CRC-16 (Modbus)      0x4B37
   # CRC-16 (Sick)        0x56A6
   # CRC-CCITT (XModem)   0x31C3
   # CRC-CCITT (0xFFFF)   0x29B1
   # CRC-CCITT (0x1D0F)   0xE5CC
   # CRC-CCITT (Kermit)   0x8921
   # CRC-DNP              0x82EA
   # CRC-32               0xCBF43926   

   crc = crcmod.predefined.PredefinedCrc("xmodem")
   #crc.update("123456789")
   crc.update("1234")
   crc.update("56789")
   print crc.crcValue, binascii.hexlify(struct.pack(">H", crc.crcValue))
   
   import sys
   sys.exit(0)

   ## Assume we (the adapter) have received a READ_REGISTER frame for
   ## device = 1, register = 2 ("/device/1/location/position").
   ## We want to assmble a SRDP READ_ACK frame with the requested data.

   ## sensor data
   ##
   timestamp = 8762345
   longitude = -34.98124
   latitude = 9.12354
   mode = 'C'

   ## According to our example EDS, the register has format "<Iffc"
   data = struct.pack("<Iffc", timestamp, longitude, latitude, mode)


   ## construct READ_ACK frame to send
   ##
   f1 = SrdpFrameHeader(1, 0x02, 1, 2, 0, len(data))
   f1.computeCrc(data)

   wireData = f1.serialize() + data

   ## send frame header and data
   print binascii.hexlify(wireData)


   f2 = SrdpFrameHeader()
   f2.parse(wireData)

   payload = wireData[10:10+f2.length]

   ## check CRC
   print f2.checkCrc(payload)

   print f2.opcode, f2.device, f2.register, f2.position, f2.length

   t = struct.unpack("<Iffc", payload)
   print t
