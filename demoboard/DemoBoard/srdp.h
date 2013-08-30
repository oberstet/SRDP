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


// SRDP frame types
//
#define SRDP_FT_REQ     0x01
#define SRDP_FT_ACK     0x02
#define SRDP_FT_ERR     0x03

// SRDP operations
//
#define SRDP_OP_SYNC    0x00
#define SRDP_OP_READ    0x01
#define SRDP_OP_WRITE   0x02
#define SRDP_OP_CHANGE  0x03

// SRDP errors
//
#define SRDP_ERR_NOT_IMPLEMENTED       -1
#define SRDP_ERR_NO_SUCH_DEVICE        -2
#define SRDP_ERR_NO_SUCH_REGISTER      -3
#define SRDP_ERR_INVALID_REG_POSLEN    -4
#define SRDP_ERR_INVALID_REG_OP        -5

// SRDP limits
//
#define SRDP_FRAME_HEADER_LEN    12    // Fixed!

#ifndef SRDP_FRAME_DATA_MAX_LEN
#  define SRDP_FRAME_DATA_MAX_LEN  256 // MUST BE < 2^16 - SRDP_FRAME_HEADER_LEN
#endif


#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

// signed integer type large enough to hold any size_t value (which are unsigned)
typedef long ssize_t; 


// Signature of transport reader function used by the SRDP channel.
//
typedef ssize_t (*srdp_transport_read) (void* userdata, uint8_t* data, size_t len);

// Signature of transport writer function used by the SRDP channel-
//
typedef ssize_t (*srdp_transport_write) (void* userdata, const uint8_t* data, size_t len);


// Callback for register read handler fired when host requests to read a register-
//
typedef int (*srdp_register_read) (void* userdata, int dev, int reg, int pos, int len, uint8_t* data);

// Callback for register write handler fired when host requests to write a register.
//
typedef int (*srdp_register_write) (void* userdata, int dev, int reg, int pos, int len, const uint8_t* data);


// Optional callback for logging purposes.
//
typedef void (*srdp_log_message) (void* userdata, const char* msg, int level);



// SRDP frame header
//
typedef union {
   uint8_t buffer[SRDP_FRAME_HEADER_LEN];
   struct {
      uint16_t opdev;
      uint16_t seq;
      uint16_t reg;
      uint16_t pos;
      uint16_t len;
      uint16_t crc16;
   } fields;
} srdp_frame_header_t;


// SRDP frame
//
typedef struct {
   srdp_frame_header_t header;
   uint8_t data[SRDP_FRAME_DATA_MAX_LEN];
} srdp_frame_t;


// SRDP channel
//
typedef struct {
   // callbacks
   //
   srdp_transport_write transport_write;
   srdp_transport_read transport_read;
   srdp_register_write register_write;
   srdp_register_read register_read;
   srdp_log_message log_message;

   // arbitrary userdata forwarded to each callback
   //
   void* userdata;

   // incoming/outgoing frame
   //
   srdp_frame_t in;
   srdp_frame_t out;

   // incoming/outgoing frame sequence number
   //
   uint16_t _seq_in;
   uint16_t _seq_out;

   // currently received incoming data length
   //
   int _bytes_received;

} srdp_channel_t;


// Initialize SRDP channel.
//
void srdp_init_channel(srdp_channel_t* channel);


// Called by driver when to transmit a register change (ie a sensor value change).
//
int srdp_register_change(srdp_channel_t* channel, int dev, int reg, int pos, int len, const uint8_t* data);


// Called by driver to let SRDP processing happen.
//
void srdp_loop(srdp_channel_t* channel);


#endif // SRDP_H
