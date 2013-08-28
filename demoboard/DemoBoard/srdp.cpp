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


void srdp_init_channel(srdp_channel_t* channel) {
   channel->_seq_in = 0;
   channel->_seq_out = 0;
   channel->needed = SRDP_FRAME_HEADER_LEN;
}


void srdp_send_frame(srdp_channel_t* channel, int op, int dev, int reg, size_t pos, size_t len) {

   if (op == OPCODE_REGISTER_CHANGE) {
      // for adapter initiated frames, we have an outgoing
      // frame sequence number
      channel->_seq_out += 1;
      channel->out.header.fields.seq = channel->_seq_out;
   } else {
      // for host initiated frames, we echo back the frame
      // sequence number of the frame received from the host
      channel->out.header.fields.seq = channel->_seq_in;
   }

   // set other frame header fields
   channel->out.header.fields.opdev = ((op & 0xf) << 12) | (dev & 0xfff);
   channel->out.header.fields.reg = reg;
   channel->out.header.fields.pos = pos;
   channel->out.header.fields.len = len;

   // FIXME: compute CRC
   channel->out.header.fields.crc16 = 0;

   // now transmit frame header and data
   channel->transport_write(channel->out.header.buffer, SRDP_FRAME_HEADER_LEN);
   if (len > 0) {
      channel->transport_write(channel->out.data, len);
   }
}


int srdp_register_change(srdp_channel_t* channel, int dev, int reg, int pos, int len, const uint8_t* data) {
   if (true) {
      for (int i = 0; i < len; ++i) {
         channel->out.data[i] = data[i];
      }
      srdp_send_frame(channel, OPCODE_REGISTER_CHANGE, dev, reg, pos, len);
   }
}


void srdp_loop(srdp_channel_t* channel) {

   // srdp_send_frame(channel, OPCODE_READ_ACK, 1, 6, 0, 1);
}
