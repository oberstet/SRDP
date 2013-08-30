//////////////////////////////////////////////////////////////////////////////#
//
//  Copyright 2013 Tavendo GmbH
//
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
//
//////////////////////////////////////////////////////////////////////////////#

#include "srdp.h"

#define LOG(MSG, LLEVEL) { if (channel->log_message) channel->log_message(channel->userdata, MSG, LLEVEL); }



void send_frame(srdp_channel_t* channel, int ft, int op, int dev, int reg, size_t pos, size_t len) {

   // | FT (2) | OP (2) | DEV (12) |
   //
   channel->out.header.fields.opdev = ((ft & 0x03) << 14) | ((op & 0x03) << 12) | (dev & 0x0fff);

   // frame sequence number
   //
   if (op == SRDP_OP_CHANGE) {
      // for adapter initiated frames, we have an outgoing
      // frame sequence number
      channel->_seq_out += 1;
      channel->out.header.fields.seq = channel->_seq_out;
   } else {
      // for host initiated frames, we echo back the frame
      // sequence number of the frame received from the host
      channel->out.header.fields.seq = channel->_seq_in;
   }

   // other frame header fields
   //
   channel->out.header.fields.reg = reg;
   channel->out.header.fields.pos = pos;
   channel->out.header.fields.len = len;

   // FIXME: compute CRC
   channel->out.header.fields.crc16 = 0;

   // now transmit frame header and data
   channel->transport_write(channel->userdata, channel->out.header.buffer, SRDP_FRAME_HEADER_LEN + len);
}


// Read handler for driver builtin registers
//
int driver_register_read (void* userdata, int dev, int reg, int pos, int len, uint8_t* data) {

   srdp_channel_t* channel = (srdp_channel_t*) userdata;

   if (dev == 0) {
      int l;

      switch (reg) {

         // Stats: Register Changes
         //
         case 4:
            if (pos == 0 && (len == 12 || len == 0)) {
               *((uint32_t*) (data + 0)) = channel->_sent_reg_change_req;
               *((uint32_t*) (data + 4)) = channel->_recv_reg_change_ack;
               *((uint32_t*) (data + 8)) = channel->_recv_reg_change_err;
               return 12;
            } else {
               return SRDP_ERR_INVALID_REG_POSLEN;
            }

         default:
            return SRDP_ERR_NO_SUCH_REGISTER;
      }
   } else {
      return SRDP_ERR_NO_SUCH_DEVICE;
   }
}


void process_incoming_frame (srdp_channel_t* channel) {

   int ft = (channel->in.header.fields.opdev >> 14) & 0x3;
   int op = (channel->in.header.fields.opdev >> 12) & 0x3;
   int dev = channel->in.header.fields.opdev & 0x0fff;
   int reg = channel->in.header.fields.reg;
   int pos = channel->in.header.fields.pos;
   int len = channel->in.header.fields.len;

   int res = SRDP_ERR_NOT_IMPLEMENTED;

   switch (ft) {
      case SRDP_FT_REQ:
         switch (op) {            

            // register read
            //
            case SRDP_OP_READ:
               if (dev == 0 && reg < 1024) {
                  // driver builtin register
                  res = driver_register_read(channel, dev, reg, pos, len, channel->out.data);
               }
               else if (channel->register_read) {
                  res = channel->register_read(channel->userdata, dev, reg, pos, len, channel->out.data);
               } else {
                  // FIXME: send error
               }

               if (res < 0) {
                  // FIXME: send error
               } else {
                  send_frame(channel, SRDP_FT_ACK, SRDP_OP_READ, dev, reg, pos, res);
               }
               break;

            // register write
            //
            case SRDP_OP_WRITE:
               if (channel->register_write) {
                  res = channel->register_write(channel->userdata, dev, reg, pos, len, channel->in.data);
                  if (res < 0) {
                     // FIXME: send error
                  } else {
                     channel->out.data[0] = 7;
                     send_frame(channel, SRDP_FT_ACK, SRDP_OP_WRITE, dev, reg, pos, res);
                  }
               } else {
                  // FIXME: send error
               }
               break;

            // unknown operation
            //
            default:
               // FIXME: send error
               break;
         }
         break;

      case SRDP_FT_ACK:
         if (op == SRDP_OP_CHANGE) {
            channel->_recv_reg_change_ack += 1;
         } else {
            // FIXME: error
         }         
         break;

      case SRDP_FT_ERR:
         if (op == SRDP_OP_CHANGE) {
            channel->_recv_reg_change_err += 1;
         } else {
            // FIXME: error
         }         
         break;

      default:
         break;
   }
}


void srdp_init_channel(srdp_channel_t* channel) {

   channel->transport_read = 0;
   channel->transport_write = 0;

   channel->register_read = 0;
   channel->register_write = 0;

   channel->log_message = 0;

   channel->userdata = 0;

   channel->_seq_in = 0;
   channel->_seq_out = 0;

   channel->_bytes_received = 0;

   channel->_sent_reg_change_req = 0;
   channel->_recv_reg_change_ack = 0;
   channel->_recv_reg_change_err = 0;
}


int srdp_register_change(srdp_channel_t* channel, int dev, int reg, int pos, int len, const uint8_t* data) {
   if (true) {
      for (int i = 0; i < len; ++i) {
         channel->out.data[i] = data[i];
      }
      send_frame(channel, SRDP_FT_REQ, SRDP_OP_CHANGE, dev, reg, pos, len);
      channel->_sent_reg_change_req += 1;
   }
}


void srdp_loop(srdp_channel_t* channel) {

   uint8_t* rptr = channel->in.header.buffer + channel->_bytes_received;
   int got = channel->transport_read(channel->userdata, rptr, SRDP_FRAME_HEADER_LEN + SRDP_FRAME_DATA_MAX_LEN - channel->_bytes_received);
   int rest = 0;

   if (got > 0) {
      channel->_bytes_received += got;

      do {

         // we need at least the frame header to determine frame data length ..
         //
         if (channel->_bytes_received >= SRDP_FRAME_HEADER_LEN) {

            int total_frame_len = SRDP_FRAME_HEADER_LEN + channel->in.header.fields.len;

            // now that we know frame data length, we want at least the complete frame ..
            //
            if (channel->_bytes_received >= total_frame_len) {

               // complete frame received
               //
               process_incoming_frame(channel);

               // if there is a rest left (octets for a subsequent frame), move that
               // to front of frame buffer
               //
               rest = channel->_bytes_received - total_frame_len;
               if (rest > 0) {
                  uint8_t* src = channel->in.header.buffer + total_frame_len;
                  uint8_t* dest = channel->in.header.buffer;
                  for (int i = 0; i < rest; ++i) {
                     dest[i] = src[i];
                  }
               }
               channel->_bytes_received = rest;

            } else {
               // need more frame data octets ..
            }
         } else {
            // need more frame header octets ..
         }

      } while (rest > 0); // consume everything received
   }
}
