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


// This library compiles under both C89, C99 ("-std=c99" GCC option)
// and C++. At least it should;)


#ifndef SRDP_H
#define SRDP_H


#ifdef __cplusplus
extern "C" {
#endif


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

// SRDP log levels
//
#define SRDP_LOGLEVEL_INFO    1
#define SRDP_LOGLEVEL_WARNING 2
#define SRDP_LOGLEVEL_ERROR   3

// SRDP frame header length (fixed)
//
#define SRDP_FRAME_HEADER_LEN      12

// SDRP frame data maximum length (configurable)
//
// MUST BE < (2^16 - SRDP_FRAME_HEADER_LEN) for UDP and as low
// as < (81 < SRDP_FRAME_HEADER_LEN) for transports such as 6LoWPAN
// over IEEE 802.15.4 with AES-CCM-128 leaving only 81 octets for
// the application layer.
//
#ifndef SRDP_FRAME_DATA_MAX_LEN
#  define SRDP_FRAME_DATA_MAX_LEN  (81 - SRDP_FRAME_HEADER_LEN)
#endif

#define SRDP_UDP_PORT 1910

#include <stddef.h>

#ifdef _MSC_VER
   // Oh well, even "stdint" is missing on VC2008 and older ..
   // http://stackoverflow.com/questions/126279/c99-stdint-h-header-and-ms-visual-studio
   // http://code.google.com/p/msinttypes/
#  include <windows_stdint.h>
#else
#  include <stdint.h>
#endif

#include <string.h>

// signed integer type large enough to hold any size_t value (which
// are unsigned)
typedef long ssize_t; 


// Signature of transport reader function used by the SRDP channel.
// (API level: public)
//
typedef ssize_t (*srdp_transport_read) (void* userdata,
                                        uint8_t* data,
                                        size_t len);

// Signature of transport writer function used by the SRDP channel.
// (API level: public)
//
typedef ssize_t (*srdp_transport_write) (void* userdata,
                                         const uint8_t* data,
                                         size_t len);


// Callback for register read handler fired when host requests to
// read a register. (API level: public)
//
typedef int (*srdp_register_read) (void* userdata,
                                   int dev,
                                   int reg,
                                   int pos,
                                   int len,
                                   uint8_t* data);

// Callback for register write handler fired when host requests to
// write a register. (API level: public)
//
typedef int (*srdp_register_write) (void* userdata,
                                    int dev,
                                    int reg,
                                    int pos,
                                    int len,
                                    const uint8_t* data);


// Optional callback for SRDP library logging
//
typedef void (*srdp_log_message) (const char* msg, int level);



#ifdef SRDP_DEBUG_DUMMY

typedef char srdp_channel_t;

#else // SRDP_DEBUG_DUMMY

// SRDP frame header (API level: private)
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


// SRDP frame (API level: private)
//
typedef struct {
   srdp_frame_header_t header;
   uint8_t data[SRDP_FRAME_DATA_MAX_LEN];
} srdp_frame_t;


// SRDP channel (API level: opaque)
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

   // the number of "SRDP_FT_REQ / SRDP_OP_CHANGE" frames we
   // sent to the host
   //
   uint32_t _sent_reg_change_req;

   // the number of "SRDP_FT_ACK / SRDP_OP_CHANGE" frames we
   // received from the host
   //
   uint32_t _recv_reg_change_ack;

   // the number of "SRDP_FT_ERR / SRDP_OP_CHANGE" frames we
   // received from the host
   //
   uint32_t _recv_reg_change_err;

   // wire level stats
   //
   uint64_t _loops;
   uint64_t _sent_octets;
   uint64_t _recv_octets;
   uint32_t _sent_frames;
   uint32_t _recv_frames;

} srdp_channel_t;

#endif // SRDP_DEBUG_DUMMY


// Initialize SRDP channel. (API level: public)
//
void srdp_init(srdp_channel_t* channel,
               srdp_transport_write transport_write,
               srdp_transport_read  transport_read,
               srdp_register_write  register_write,
               srdp_register_read   register_read,
               srdp_log_message     log_message,
               void* userdata);


// Called by driver when to transmit a register
// change (ie a sensor value change).  (API level: public)
//
int srdp_notify(srdp_channel_t* channel,
                int dev,
                int reg,
                int pos,
                int len);


// Called by driver to let SRDP processing happen.  (API level: public)
//
void srdp_loop(srdp_channel_t* channel);


// Set output frame to string value.
//
int srdp_set_string(uint8_t* data, const char* str);


#ifdef __cplusplus
}
#endif

#endif // SRDP_H
