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
#define SRDP_FRAME_HEADER_LEN    12
#define SRDP_FRAME_DATA_MAX_LEN  100 // MUST BE < 2^16 - SRDP_FRAME_HEADER_LEN


#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

typedef long ssize_t;


// Signature of transport reader function used by the SRDP channel.
//
typedef ssize_t (*srdp_transport_read) (uint8_t* data, size_t len);

// Signature of transport writer function used by the SRDP channel
//
typedef ssize_t (*srdp_transport_write) (const uint8_t* data, size_t len);


// Callback for register read handler fired when host requests to read a register
//
typedef int (*srdp_register_read) (int dev, int reg, int pos, int len, uint8_t* data);

// Callback for register write handler fired when host requests to write a register
//
typedef int (*srdp_register_write) (int dev, int reg, int pos, int len, const uint8_t* data);


typedef void (*srdp_log_message) (const char* msg, int level);



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
   srdp_log_message log_message;

   const char* uri_driver_eds;
   const char* uri_device_eds;

   int _bytes_received;

} srdp_channel_t;


// Initialize SRDP channel
//
void srdp_init_channel(srdp_channel_t* channel);


// Send a SRDP frame
//
//void srdp_send_frame(srdp_channel_t* channel, int op, int dev, int reg, size_t pos, size_t len);


// Called by driver when a register changes (ie a sensor value has changed)
//
int srdp_register_change(srdp_channel_t* channel, int dev, int reg, int pos, int len, const uint8_t* data);


// Called by driver to let SRDP processing happen.
//
void srdp_loop(srdp_channel_t* channel);

#endif // SRDP_H
