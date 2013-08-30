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

__all__ = ("SrdpFrameHeader",)

import struct, binascii

## https://pypi.python.org/pypi/crcmod
import crcmod


class SrdpFrameHeader:

   SRDP_FT_REQ     = 0x01
   SRDP_FT_ACK     = 0x02
   SRDP_FT_ERROR   = 0x03

   SRDP_OP_SYNC    = 0x00
   SRDP_OP_READ    = 0x01
   SRDP_OP_WRITE   = 0x02
   SRDP_OP_CHANGE  = 0x03

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
      return "FT = %x, OP = %x, DEV = %d, REG = %d, POS = %d, LEN = %d" % (self.frametype, self.opcode, self.device, self.register, self.position, self.length)


   def computeCrc(self, data = None):
      if data:
         self.length = len(data)
      else:
         self.length = 0

      crc = crcmod.predefined.PredefinedCrc("crc-16")

      header = struct.pack("<HHHHH",
                           ((self.frametype & 0x03) << 14) | ((self.opcode & 0x03) << 12) | (self.device & 0x0fff),
                           self.seq,
                           self.register,
                           self.position,
                           self.length)
      crc.update(header)

      if self.length:
         crc.update(data)

      self.crc16 = crc.crcValue


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


   def checkCrc(self, data = None):
      crc = crcmod.predefined.PredefinedCrc("crc-16")
      header = struct.pack("<HHHHH",
                           ((self.frametype & 0x03) << 14) | ((self.opcode & 0x03) << 12) | (self.device & 0x0fff),
                           self.seq,
                           self.register,
                           self.position,
                           self.length)
      crc.update(header)
      if self.length:
         crc.update(data)
      return self.crc16 == crc.crcValue



if __name__ == '__main__':

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
