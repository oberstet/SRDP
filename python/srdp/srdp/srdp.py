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

__all__ = ("SrdpException",
           "SrdpFrameHeader",
           "SrdpProtocol",
           "SrdpStreamProtocol",
           "SrdpDatagramProtocol",)

import zope
from zope.interface import implementer

import struct, binascii
from collections import deque

## https://pypi.python.org/pypi/crcmod
import crcmod

from twisted.python import log
from twisted.internet.protocol import Protocol, DatagramProtocol
from twisted.internet.defer import Deferred 
from twisted.python.failure import Failure

from interfaces import ISrdpProvider, ISrdpChannel


class SrdpException(Exception):

   def __init__(self, data):
      error_code = struct.unpack("<l", data)[0]
      if SrdpFrameHeader.SRDP_ERR_DESC.has_key(error_code):
         error_text = SrdpFrameHeader.SRDP_ERR_DESC[error_code]
      else:
         error_text = "SRDP error %d" % error_code
      Exception.__init__(self, error_code, error_text)



class SrdpFrameHeader:

   SRDP_FT_REQ = 0x01
   SRDP_FT_ACK = 0x02
   SRDP_FT_ERR = 0x03

   SRDP_FT_NAME = {SRDP_FT_REQ: 'REQ',
                   SRDP_FT_ACK: 'ACK',
                   SRDP_FT_ERR: 'ERR'}

   SRDP_OP_SYNC   = 0x00
   SRDP_OP_READ   = 0x01
   SRDP_OP_WRITE  = 0x02
   SRDP_OP_CHANGE = 0x03

   SRDP_OP_NAME = {SRDP_OP_SYNC: 'SYNC',
                   SRDP_OP_READ: 'READ',
                   SRDP_OP_WRITE: 'WRITE',
                   SRDP_OP_CHANGE: 'CHANGE'}

   SRDP_ERR_NOT_IMPLEMENTED    = -1
   SRDP_ERR_NO_SUCH_DEVICE     = -2
   SRDP_ERR_NO_SUCH_REGISTER   = -3
   SRDP_ERR_INVALID_REG_POSLEN = -4
   SRDP_ERR_INVALID_REG_OP     = -5

   SRDP_ERR_DESC = {SRDP_ERR_NOT_IMPLEMENTED: 'not implemented',
                    SRDP_ERR_NO_SUCH_DEVICE: 'no such device',
                    SRDP_ERR_NO_SUCH_REGISTER: 'no such register',
                    SRDP_ERR_INVALID_REG_POSLEN: 'invalid register position and/or length',
                    SRDP_ERR_INVALID_REG_OP: 'invalid register operation'}

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

      self.dataLength = 0
      self.senderAddr = None


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



@implementer(ISrdpChannel)
class SrdpProtocol(object):

   def __init__(self, provider, debug = False):
      if not ISrdpProvider.providedBy(provider):
         raise Exception("provider must implement ISrdpProvider")

      self._provider = provider
      self._debug = debug
      self._isConnected = None
      self._seq = 0
      self._pending = {}


   def _logFrame(self, msg, header, data):
      if data:
         d = binascii.hexlify(data)
      else:
         d = ''
      if len(d) > 64:
         d = d[:64] + ".."
      log.msg("%s [%s, data = '%s']" % (msg, header, d))


   def _frameReceived(self, frameHeader, frameData):
      if self._debug:
         self._logFrame("SRDP frame received", frameHeader, frameData)

      ## check frame CRC
      ##
      crc16 = frameHeader.computeCrc(frameData)
      if crc16 != frameHeader.crc16:
         print "CRC Error: computed = %s, received = %s" % (binascii.hexlify(struct.pack("<H", crc16)), binascii.hexlify(struct.pack("<H", self._srdpFrameHeader.crc16)))
         # FIXME: send ERR
      
      self._processFrame(frameHeader, frameData)


   def readRegister(self, device, register, position = 0, length = 0):
      if not self._isConnected:
         raise Exception("cannot send register read request when not connected")

      self._seq += 1
      frame = SrdpFrameHeader(seq = self._seq,
                              frametype = SrdpFrameHeader.SRDP_FT_REQ,
                              opcode = SrdpFrameHeader.SRDP_OP_READ,
                              device = device,
                              register = register,
                              position = position,
                              length = length)
      self._sendFrame(frame)
      d = Deferred()
      self._pending[self._seq] = d
      return d


   def writeRegister(self, device, register, data, position = 0):
      if not self._isConnected:
         raise Exception("cannot send register write request when not connected")

      self._seq += 1
      frame = SrdpFrameHeader(self._seq,
                              frametype = SrdpFrameHeader.SRDP_FT_REQ,
                              opcode = SrdpFrameHeader.SRDP_OP_WRITE,
                              device = device,
                              register = register,
                              position = position,
                              length = len(data))
      self._sendFrame(frame, data)
      d = Deferred()
      self._pending[self._seq] = d
      return d


   def notifyRegister(self, device, register, position, length):

      if not self._isConnected:
         raise Exception("cannot send register change notification when not connected")

      pass # FIXME: process and potential send ACK


   def _processFrame(self, header, data):
      if header.frametype == SrdpFrameHeader.SRDP_FT_REQ:

         if header.opcode == SrdpFrameHeader.SRDP_OP_CHANGE:
            res = self.onRegisterChange(header.device, header.register, header.position, data)

         elif header.opcode == SrdpFrameHeader.SRDP_OP_READ:
            pass

         elif header.opcode == SrdpFrameHeader.SRDP_OP_WRITE:
            pass


      elif header.frametype in [SrdpFrameHeader.SRDP_FT_ACK, SrdpFrameHeader.SRDP_FT_ERR]:
         if self._pending.has_key(header.seq):
            if header.frametype == SrdpFrameHeader.SRDP_FT_ACK:
               self._pending[header.seq].callback(data)
            else:
               self._pending[header.seq].errback(Failure(SrdpException(data)))
            del self._pending[header.seq]
         else:
            log.msg("NO SUCH SEQ!")

      else:
         raise Exception("logic error")



class SrdpDatagramProtocol(DatagramProtocol, SrdpProtocol):

   def __init__(self, provider, addr = None, debug = False):
      SrdpProtocol.__init__(self, provider, debug = debug)
      self._addr = addr


   def close(self):
      self.transport.loseConnection()


   def startProtocol(self):
      if self._addr:
         self.transport.connect(*self._addr)
         self._isConnected = True
      else:
         self._isConnected = False
      self._provider.onChannelOpen(self)

   def stopProtocol(self):
      self._provider.onChannelClose(None)


   def _sendFrame(self, header, data = None):
      header.crc16 = header.computeCrc(data)

      if data:
         wireData = header.serialize() + data
      else:
         wireData = header.serialize()

      if self._addr:
         ## if this UDP socket is connected, our peer is fixed
         ## and we don't provide a receiver address
         ##
         self.transport.write(wireData)
      elif header.senderAddr:
         ## if 
         self.transport.write(wireData, header.senderAddr)
      else:
         raise Exception("logic error")

      if self._debug:
         self._logFrame("SRDP frame sent", header, data)


   def datagramReceived(self, datagram, addr):   
      if self._debug:
         log.msg("Octets received [data = %s]" % binascii.hexlify(data))

      if len(datagram) < SrdpFrameHeader.SRDP_FRAME_HEADER_LEN:
         raise Exception("invalid SRDP datagram (shorter than header)")

      header = SrdpFrameHeader()
      header.parse(datagram[0:SrdpFrameHeader.SRDP_FRAME_HEADER_LEN])

      if (header.frametype, header.opcode) \
         in [(SrdpFrameHeader.SRDP_FT_REQ, SrdpFrameHeader.SRDP_OP_SYNC),
             (SrdpFrameHeader.SRDP_FT_REQ, SrdpFrameHeader.SRDP_OP_READ),
             (SrdpFrameHeader.SRDP_FT_ACK, SrdpFrameHeader.SRDP_OP_WRITE)]:
         header.dataLength = 0
      else:
         header.dataLength = header.length

      if len(datagram) < SrdpFrameHeader.SRDP_FRAME_HEADER_LEN + header.dataLength:
         raise Exception("invalid SRDP datagram (shorter than header+payload)")

      data = datagram[SrdpFrameHeader.SRDP_FRAME_HEADER_LEN:]

      ## note the datagram sender, so we can set the receiver in
      ## the reply later
      ##
      header.senderAddr = addr

      self._frameReceived(header, data)



class SrdpStreamProtocol(Protocol, SrdpProtocol):

   def __init__(self, provider, debug = False):
      SrdpProtocol.__init__(self, provider, debug = debug)

      self._received = []
      self._receivedNum = 0
      self._needed = SrdpFrameHeader.SRDP_FRAME_HEADER_LEN

      self._srdpFrameHeader = None
      self._srdpFrameData = None

      self._chopup = False
      self._send_queue = deque()
      self._send_queue_triggered = False


   def close(self):
      self.transport.loseConnection()


   def connectionMade(self):
      self._isConnected = True
      self._provider.onChannelOpen(self)


   def connectionLost(self, reason):
      self._isConnected = False
      self._provider.onChannelClose(reason)


   def _send(self):
      if len(self._send_queue) > 0:
         d = self._send_queue.popleft()
         self.transport.write(d)
         #FIXME
         #reactor.callLater(0.1, self._send)
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


   def _sendFrame(self, header, data = None):
      header.crc16 = header.computeCrc(data)
      if data:
         wireData = header.serialize() + data
      else:
         wireData = header.serialize()
      self._write(wireData)

      if self._debug:
         self._logFrame("SRDP frame sent", header, data)



   def dataReceived(self, data):

      if self._debug:
         log.msg("Octets received [data = %s]" % binascii.hexlify(data))

      ## buffer up received octets ..
      ##
      self._received.append(data)
      self._receivedNum += len(data)

      ## .. until we have enough to begin processing the frame
      ##
      if self._receivedNum >= self._needed:
         data = ''.join(self._received)
         self._received = []
         self._receiveFrame(data)


   def _receiveFrame(self, data):

      if self._srdpFrameHeader is None:

         ## awaiting frame header ..
         ##
         self._srdpFrameHeader = SrdpFrameHeader()
         self._srdpFrameHeader.parse(data[0:SrdpFrameHeader.SRDP_FRAME_HEADER_LEN])

         rest = data[SrdpFrameHeader.SRDP_FRAME_HEADER_LEN:]

         if (self._srdpFrameHeader.frametype, self._srdpFrameHeader.opcode) \
            in [(SrdpFrameHeader.SRDP_FT_REQ, SrdpFrameHeader.SRDP_OP_SYNC),
                (SrdpFrameHeader.SRDP_FT_REQ, SrdpFrameHeader.SRDP_OP_READ),
                (SrdpFrameHeader.SRDP_FT_ACK, SrdpFrameHeader.SRDP_OP_WRITE)]:
            self._srdpFrameHeader.dataLength = 0
         else:
            self._srdpFrameHeader.dataLength = self._srdpFrameHeader.length

         self._needed = self._srdpFrameHeader.dataLength

      else:

         ## got complete frame data. frame is ready to be processed.
         ##
         if self._srdpFrameHeader.dataLength > 0:
            self._srdpFrameData = data[0:self._srdpFrameHeader.dataLength]
            rest = data[self._srdpFrameHeader.dataLength:]
         else:
            self._srdpFrameData = None
            rest = data

         ## process SRDP frame and reset everything
         ##
         self._frameReceived(self._srdpFrameHeader, self._srdpFrameData)
         self._srdpFrameHeader = None
         self._srdpFrameData = None
         self._needed = SrdpFrameHeader.SRDP_FRAME_HEADER_LEN

      if len(rest) < self._needed:
         ## need to receive more data to continue ..
         ##
         self._received.append(rest)
         self._receivedNum = len(rest)
      else:
         ## process the rest of already received data
         ##
         self._receiveFrame(rest)
