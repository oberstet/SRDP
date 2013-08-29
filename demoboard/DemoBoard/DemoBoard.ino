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

//
// Arduino "Demoboard" SRDP Driver.
//

#include "SmoothAnalogInput.h"
#include "Button.h"
#include "RgbLed.h"

#include "srdp.h" // SRDP library


// Arduino Pins on the Demoboard
//
#define PIN_LED1    3
#define PIN_LED2    9
#define PIN_LED3_R  8
#define PIN_LED3_G  6
#define PIN_LED3_B1 5
#define PIN_LED3_B2 7
#define PIN_POT1    0
#define PIN_POT2    1
#define PIN_BTN1    22
#define PIN_BTN2    23

// Indices of SRDP Registers the Demoboard will expose
//
#define IDX_DEV         1
#define IDX_REG_LED1    3
#define IDX_REG_LED2    4
#define IDX_REG_LED3    5
#define IDX_REG_BTN1    6
#define IDX_REG_BTN2    7

// URIs of the driver and device electronic datasheet (EDS)
//
#define URI_DRIVER_EDS "FIXME"
#define URI_DEVICE_EDS "FIXME"

// UUIDs of the driver and device
//
#define UUID_DRIVER "FIXME"
#define UUID_DEVICE "FIXME"


// Wrappers for hardware components
//
SmoothAnalogInput pot1, pot2;
Button btn1, btn2;
RgbLed led3;


// SRDP channel to communicate with host
//
srdp_channel_t channel;


// Here we track which registers are watched by the host
// When bit N is set, the host watched register N.
//
int watched = -1;


// Transport reader function used by the SRDP channel
//
ssize_t transport_read (uint8_t* data, size_t len) {
   if (Serial.available() > 0) {
      return Serial.readBytes((char*) data, len);
   } else {
      return 0;
   }
}


// Transport writer function used by the SRDP channel
//
ssize_t transport_write (const uint8_t* data, size_t len) {
   Serial.write(data, len);
   return len;
}


// Register read handler called when host requests to read a register
//
int register_read(int dev, int reg, int pos, int len, uint8_t* data) {
   if (dev == IDX_DEV) {
      switch (reg) {

         // Buttons
         //
         case IDX_REG_BTN1:
         case IDX_REG_BTN2:
            if (pos == 0 && len == 1) {

               if (reg == IDX_REG_BTN1) {
                  data[0] = btn1.getState();
               } else {
                  data[0] = btn2.getState();
               }
               return 1;
            } else {
               return SRDP_ERR_INVALID_REG_POSLEN;
            }

         case IDX_REG_LED1:
         case IDX_REG_LED2:
         case IDX_REG_LED3:
            return SRDP_ERR_INVALID_REG_OP;

         default:
            return SRDP_ERR_NO_SUCH_REGISTER;
      }
   } else {
      return SRDP_ERR_NO_SUCH_DEVICE;
   }
}


// Register write handler called when host requests to write a register
//
int register_write(int dev, int reg, int pos, int len, const uint8_t* data) {
   if (dev == IDX_DEV) {
      switch (reg) {
         
         // LED 1 (red)
         // LED 2 (green)
         //
         case IDX_REG_LED1:
         case IDX_REG_LED2:
            if (pos == 0 && len == 1) {

               int pin = reg == IDX_REG_LED1 ? PIN_LED1 : PIN_LED2;
               if (data[0]) {
                  digitalWrite(pin, HIGH);
               } else {
                  digitalWrite(pin, LOW);
               }
               return len;
            } else {
               return SRDP_ERR_INVALID_REG_POSLEN;
            }

         // LED 3 (RGB)
         //
         case IDX_REG_LED3:
            if (pos == 0 && len == 3) {

               led3.write(data[0], data[1], data[2]);
               return len;
            } else {
               return SRDP_ERR_INVALID_REG_POSLEN;
            }

         case IDX_REG_BTN1:
         case IDX_REG_BTN2:
            return SRDP_ERR_INVALID_REG_OP;

         default:
            return SRDP_ERR_NO_SUCH_REGISTER;
      }
   } else {
      return SRDP_ERR_NO_SUCH_DEVICE;
   }
}


// Register watch handler called when host requests to watch/unwatch a register
//
int register_watch(int dev, int reg, bool enable) {
   if (dev == IDX_DEV) {
      switch (reg) {
         case IDX_REG_BTN1:
         case IDX_REG_BTN2:
            if (enable) {
               watched |= 1 << reg;
            } else {
               watched &= ~(1 << reg);
            }
            return 0;
         case IDX_REG_LED1:
         case IDX_REG_LED2:
         case IDX_REG_LED3:
            return SRDP_ERR_INVALID_REG_OP;
         default:
            return SRDP_ERR_NO_SUCH_REGISTER;
      }
   } else {
      return SRDP_ERR_NO_SUCH_DEVICE;
   }
}


// Arduino setup function executed once after reset
//
void setup() {

   // configure serial interface
   //
   Serial.begin(115200); // default SERIAL_8N1
   Serial.setTimeout(10);
   Serial.flush();

   // setup SRDP channel over serial
   //
   srdp_init_channel(&channel);
   channel.transport_read = transport_read;
   channel.transport_write = transport_write;
   channel.register_read = register_read;
   channel.register_write = register_write;
   channel.register_watch = register_watch;
   channel.uri_driver_eds = URI_DRIVER_EDS;
   channel.uri_device_eds = URI_DEVICE_EDS;

   // LED 1
   pinMode(PIN_LED1, OUTPUT);
   digitalWrite(PIN_LED1, LOW);

   // LED 2
   pinMode(PIN_LED2, OUTPUT);
   digitalWrite(PIN_LED2, LOW);

   // LED 3
   led3.attach(PIN_LED3_R, PIN_LED3_G, PIN_LED3_B1, PIN_LED3_B2);
  
   // Buttons
   btn1.attach(PIN_BTN1, 2);
   btn2.attach(PIN_BTN2, 2);
  
   // Potis
   pot1.attach(PIN_POT1, 0, 1000);
   pot2.attach(PIN_POT2, 0, 1000);
}


// Arduino main run loop
//
void loop() {

/*
   if (Serial.available() >= channel.needed) {
      srdp_loop(&channel);
   }
*/
/*
   if (Serial.available() >= SRDP_FRAME_HEADER_LEN) {
    
      Serial.readBytes((char*) channel.in.header.buffer, SRDP_FRAME_HEADER_LEN);

      if (channel.in.header.fields.len > 0) {
         Serial.readBytes((char*) channel.in.data, channel.in.header.fields.len);
      }

      const char* err = 0;

      switch (channel.in.header.fields.opdev >> 12) {

         case OPCODE_READ_REGISTER:
            //err = onReadRegister(&channel);
            break;

         case OPCODE_WRITE_REGISTER:
            register_write(channel.in.header.fields.opdev & 0xfff,
                           channel.in.header.fields.reg,
                           channel.in.header.fields.pos,
                           channel.in.header.fields.len,
                           channel.in.data);
            break;

         default:
            //log("unknown frame");
            break;
      }

      if (err) {
         Serial.println(err);
      }
   }
*/

   // process buttons
   //
   if (btn1.process() && (watched & 1 << IDX_REG_BTN1)) {
      // OR: simply trigger a read register .. code only once.

      // when button changed, report change to SRDP
      uint8_t data = btn1.getState();
      srdp_register_change(&channel, IDX_DEV, IDX_REG_BTN1, 0, 1, &data);
   }

   if (btn2.process() && (watched & 1 << IDX_REG_BTN2)) {
      uint8_t data = btn2.getState();
      srdp_register_change(&channel, IDX_DEV, IDX_REG_BTN2, 0, 1, &data);
   }

   // limit update frequency
   //
   delay(20);
}
