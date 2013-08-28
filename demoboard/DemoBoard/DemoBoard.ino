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

#include "SmoothAnalogInput.h"
#include "Button.h"
#include "RgbLed.h"

#include "srdp.h"


// Demoboard hardware
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


// Wrappers for hardware components
//
SmoothAnalogInput pot1, pot2;
Button btn1, btn2;
RgbLed led3;


// SRDP channel to communicate with host
//
srdp_channel_t channel;
  

// transport writer function used by the SRDP channel
//
ssize_t transport_write (const uint8_t* data, size_t len) {
   Serial.write(data, len);
   return len;
}


// transport reader function used by the SRDP channel
//
ssize_t transport_read (uint8_t* data, size_t len) {
   if (Serial.available() > 0) {
      return Serial.readBytes((char*) data, len);
   } else {
      return 0;
   }
}


// register read handler called when host requests to read a register
//
int register_read(int dev, int reg, int pos, int len, uint8_t* data) {
   //
   // Device 1
   //
   if (dev == 1) {
      switch (reg) {
         //
         // Register 6: Button 1 (left)
         // Register 7: Button 2 (right)
         //
         case 6:
         case 7:
            if (pos == 0 && len == 1) {
               if (reg == 6) {
                  data[0] = btn1.getState();
               } else {
                  data[0] = btn2.getState();
               }
               return 1;
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


// register write handler called when host requests to write a register
//
int register_write(int dev, int reg, int pos, int len, const uint8_t* data) {
   //
   // Device 1
   //
   if (dev == 1) {
      switch (reg) {
         //
         // Register 3: LED 1 (red)
         // Register 4: LED 2 (green)
         //
         case 3:
         case 4:
            if (pos == 0 && len == 1) {
               int pin = reg == 3 ? PIN_LED1 : PIN_LED2;
               if (data[0]) {
                  digitalWrite(pin, HIGH);
               } else {
                  digitalWrite(pin, LOW);
               }
               return len;
            } else {
               return SRDP_ERR_INVALID_REG_POSLEN;
            }
         //
         // Register 5: LED 3 (RGB)
         //
         case 5:
            if (pos == 0 && len == 3) {
               led3.write(data[0], data[1], data[2]);
               return len;
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


// setup function executed once after reset
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
   channel.transport_write = transport_write;
   channel.transport_read = transport_read;
   channel.register_write = register_write;
   channel.register_read = register_read;

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




const char* onReadRegister(srdp_channel_t* channel) {
   // device 1
   //
   if ((channel->in.header.fields.opdev & 0xfff) == 1) {
      switch (channel->in.header.fields.reg) {
         //
         // Register 6: Button 1 (left)
         //
         case 6:
            if (channel->in.header.fields.pos == 0 && channel->in.header.fields.len == 0) {

               channel->out.data[0] = btn1.getState();
               srdp_send_frame(channel, OPCODE_READ_ACK, 1, 6, 0, 1);
            } else {
               return "invalid data position and/or length";
            }
            return 0;

         //
         // Register 7: Button 2 (right)
         //
         case 7:
            if (channel->in.header.fields.pos == 0 && channel->in.header.fields.len == 0) {

               channel->out.data[0] = btn2.getState();
               srdp_send_frame(channel, OPCODE_READ_ACK, 1, 7, 0, 1);
            } else {
               return "invalid data position and/or length";
            }
            return 0;

         default:
            return "no such register";
      }
   } else {
      return "no such device";
   }
}



void loop() {

/*
   if (Serial.available() >= channel.needed) {
      srdp_loop(&channel);
   }
*/

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


   if (btn1.process()) {
      uint8_t data = btn1.getState();
      srdp_register_change(&channel, 1, 6, 0, 1, &data);
   }

   if (btn2.process()) {
      uint8_t data = btn2.getState();
      srdp_register_change(&channel, 1, 7, 0, 1, &data);
   }

   // limit update frequency to 50Hz
   delay(20);
}
