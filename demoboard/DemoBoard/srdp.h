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

#ifndef SRDP_H
#define SRDP_H

// | FT (2) | OP (3) | DEV (11) |

// SRDP frame types
//
#define SRDP_FT_REQ     0x01
#define SRDP_FT_ACK     0x02
#define SRDP_FT_ERROR   0x03

// SRDP operations
//
#define SRDP_OP_SYNC    0x01
#define SRDP_OP_READ    0x02
#define SRDP_OP_WRITE   0x03
#define SRDP_OP_WATCH   0x04
#define SRDP_OP_UNWATCH 0x05
#define SRDP_OP_CHANGE  0x06



#define OPCODE_SYNCHRONIZE      0x00
#define OPCODE_READ_REGISTER    0x01
#define OPCODE_READ_ACK         0x02
#define OPCODE_WRITE_REGISTER   0x03
#define OPCODE_WRITE_ACK        0x04
#define OPCODE_WATCH_REGISTER   0x05
#define OPCODE_WATCH_ACK        0x06
#define OPCODE_UNWATCH_REGISTER 0x07
#define OPCODE_UNWATCH_ACK      0x08
#define OPCODE_REGISTER_CHANGE  0x09
#define OPCODE_CHANGE_ACK       0x0A
#define OPCODE_ERROR            0x0B


#define SRDP_FRAME_HEADER_LEN  12
#define SRDP_FRAME_DATA_MAX_LEN 100

#define SRDP_ERR_NO_SUCH_DEVICE -1
#define SRDP_ERR_NO_SUCH_REGISTER -2
#define SRDP_ERR_INVALID_REG_POSLEN -3


#include <unistd.h> 
#include <sys/types.h>

typedef long ssize_t;


typedef ssize_t (*srdp_transport_write) (const uint8_t* data, size_t len);

typedef ssize_t (*srdp_transport_read) (uint8_t* data, size_t len);

typedef int (*srdp_register_write) (int dev, int reg, int pos, int len, const uint8_t* data);

typedef int (*srdp_register_read) (int dev, int reg, int pos, int len, uint8_t* data);


typedef union {
   uint8_t buffer[SRDP_FRAME_HEADER_LEN];
   struct {
      uint16_t seq;
      uint16_t opdev;
      uint16_t reg;
      uint16_t pos;
      uint16_t len;
      uint16_t crc16;
   } fields;
} srdp_frame_header_t;


typedef struct {
   srdp_frame_header_t header;
   uint8_t data[SRDP_FRAME_DATA_MAX_LEN];
} srdp_frame_t;


typedef struct {
   srdp_frame_t in;
   srdp_frame_t out;

   int needed;

   uint16_t _seq_in;
   uint16_t _seq_out;

   uint32_t reg_change_acks;
   uint32_t reg_change_errs;

   srdp_transport_write transport_write;
   srdp_transport_read transport_read;
   srdp_register_write register_write;
   srdp_register_read register_read;
} srdp_channel_t;


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

}

#endif // SRDP_H
