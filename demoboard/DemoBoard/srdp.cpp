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


#define LOG(MSG, LLEVEL) { if (channel->log_message) channel->log_message(MSG, LLEVEL); }



void srdp_init_channel(srdp_channel_t* channel) {
   channel->_seq_in = 0;
   channel->_seq_out = 0;

   channel->_bytes_received = 0;

   channel->transport_read = 0;
   channel->transport_write = 0;

   channel->register_read = 0;
   channel->register_write = 0;

   channel->uri_driver_eds = 0;
   channel->uri_device_eds = 0;

   channel->log_message = 0;
}


void srdp_send_frame(srdp_channel_t* channel, int ft, int op, int dev, int reg, size_t pos, size_t len) {

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
   channel->transport_write(channel->out.header.buffer, SRDP_FRAME_HEADER_LEN + len);
/*
   channel->transport_write(channel->out.header.buffer, SRDP_FRAME_HEADER_LEN);
   if (len > 0) {
      channel->transport_write(channel->out.data, len);
   }
*/   
}


int srdp_register_change(srdp_channel_t* channel, int dev, int reg, int pos, int len, const uint8_t* data) {
   if (true) {
      for (int i = 0; i < len; ++i) {
         channel->out.data[i] = data[i];
      }
      srdp_send_frame(channel, SRDP_FT_REQ, SRDP_OP_CHANGE, dev, reg, pos, len);
   }
}


#include <Arduino.h>


void process_incoming_frame(srdp_channel_t* channel) {

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
               if (channel->register_read) {
                  res = channel->register_read(dev, reg, pos, len, channel->out.data);
                  if (res < 0) {
                     // FIXME: send error
                  } else {
                     srdp_send_frame(channel, SRDP_FT_ACK, SRDP_OP_READ, dev, reg, pos, res);
                  }
               } else {
                  // FIXME: send error
               }
               break;

            // register write
            //
            case SRDP_OP_WRITE:
               if (channel->register_write) {
                  res = channel->register_write(dev, reg, pos, len, channel->in.data);
                  if (res < 0) {
                     // FIXME: send error
                  } else {
                     srdp_send_frame(channel, SRDP_FT_ACK, SRDP_OP_WRITE, dev, reg, pos, res);
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
         break;

      case SRDP_FT_ERR:
         break;

      default:
         break;
   }
}


void srdp_loop(srdp_channel_t* channel) {

   uint8_t* rptr = channel->in.header.buffer + channel->_bytes_received;
   int got = channel->transport_read(rptr, SRDP_FRAME_HEADER_LEN + SRDP_FRAME_DATA_MAX_LEN - channel->_bytes_received);
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

/*
void srdp_loop_old(srdp_channel_t* channel) {

   // srdp_send_frame(channel, OPCODE_READ_ACK, 1, 6, 0, 1);
   LOG("srdp_loop", 0);

   int rest_received = 0;

   while (true) {

      uint8_t* rptr = channel->in.header.buffer + channel->_bytes_received;
      int got = channel->transport_read(rptr, SRDP_FRAME_HEADER_LEN + SRDP_FRAME_DATA_MAX_LEN - channel->_bytes_received);

      Serial.println("GOT:");
      Serial.println(got);

      if (got > 0 || rest_received > 0) {
         channel->_bytes_received += got;

         if (channel->_bytes_received >= SRDP_FRAME_HEADER_LEN) {

            int total_frame_len = SRDP_FRAME_HEADER_LEN + channel->in.header.fields.len;

            if (channel->_bytes_received >= total_frame_len) {

               // complete frame received
               LOG("frame received", 0);
               process_incoming_frame(channel);

               // if there is a rest left, move that to front of frame buffer
               //
               rest_received = channel->_bytes_received - total_frame_len;
               if (rest_received > 0) {
                  uint8_t* src = channel->in.header.buffer + total_frame_len;
                  uint8_t* dest = channel->in.header.buffer;
                  for (int i = 0; i < rest_received; ++i) {
                     dest[i] = src[i];
                  }
                  LOG("frame rest > 0", 0);
                  Serial.println(rest_received);
               }

               channel->_bytes_received = rest_received;

            } else {
//               channel->_bytes_received += got;
               LOG("need more frame data", 0);
            }
         } else {
            // need more data for frame header
            LOG("need more frame header", 0);
         }
      } else {
         break;
      }
   }   
}
*/