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

SmoothAnalogInput a1, a2;
Button b1, b2;
bool b1_isWatched = true;
bool b2_isWatched = true;

RgbLed l1;

const int led1Pin = 3;
const int led2Pin = 9;

const int pot1Pin = 0;
const int pot2Pin = 1;
const int btn1Pin = 22;
const int btn2Pin = 23;

const char* URI_ADAPTER_EDS = "http://api.somevendor.com/adapter/demoboardv1";
const char* URI_DEVICE_EDS = "http://api.somevendor.com/device/demoboardv1";


srdp_channel_t channel;
  


void setup() {

  Serial.begin(115200); // default SERIAL_8N1
  Serial.setTimeout(10);

  // LED 1
  pinMode(led1Pin, OUTPUT);
  digitalWrite(led1Pin, LOW);

  // LED 2
  pinMode(led2Pin, OUTPUT);
  digitalWrite(led2Pin, LOW);

  // RGB LED (R = 8, G = 6, B = 5/7)
  l1.attach(8, 6, 5, 7);
  
  b1.attach(btn1Pin, "button1", 2);
  b2.attach(btn2Pin, "button2", 2);
  
  a1.attach(pot1Pin, "analog1");
  a1.scale(0, 1000);

  a2.attach(pot2Pin, "analog2");
  a2.scale(0, 1000);

   srdp_init_channel(&channel);
}


void log(const char* msg) {
   Serial.println(msg);
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

               channel->out.data[0] = b1.getState();
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

               channel->out.data[0] = b2.getState();
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


const char* onWriteRegister(srdp_channel_t* channel) {
   // device 1
   //
   if ((channel->in.header.fields.opdev & 0xfff) == 1) {
      switch (channel->in.header.fields.reg) {
         //
         // Register 3: LED 1 (red)
         //
         case 3:
            if (channel->in.header.fields.pos == 0 && channel->in.header.fields.len == 1) {

               if (channel->in.data[0]) {
                  digitalWrite(led1Pin, HIGH);
               } else {
                  digitalWrite(led1Pin, LOW);
               }
            } else {
               return "invalid data position and/or length";
            }
            return 0;

         //
         // Register 4: LED 2 (green)
         //
         case 4:
            if (channel->in.header.fields.pos == 0 && channel->in.header.fields.len == 1) {

               if (channel->in.data[0]) {
                  digitalWrite(led2Pin, HIGH);
               } else {
                  digitalWrite(led2Pin, LOW);
               }
            } else {
               return "invalid data position and/or length";
            }
            return 0;

         //
         // Register 5: LED 3 (RGB)
         //
         case 5:
            if (channel->in.header.fields.pos == 0 && channel->in.header.fields.len == 3) {

               l1.write(channel->in.data[0], channel->in.data[1], channel->in.data[2]);
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

   if (Serial.available() >= SRDP_FRAME_HEADER_LEN) {
    
      Serial.readBytes((char*) channel.in.header.buffer, SRDP_FRAME_HEADER_LEN);

      if (channel.in.header.fields.len > 0) {
         Serial.readBytes((char*) channel.in.data, channel.in.header.fields.len);
      }

      const char* err = 0;

      switch (channel.in.header.fields.opdev >> 12) {

         case OPCODE_READ_REGISTER:
            err = onReadRegister(&channel);
            break;

         case OPCODE_WRITE_REGISTER:
            err = onWriteRegister(&channel);
            break;

         default:
            log("unknown frame");
            break;
      }

      if (err) {
         Serial.println(err);
      }
   }

   if (b1.process() && b1_isWatched) {
      channel.out.data[0] = b1.getState();
      srdp_send_frame(&channel, OPCODE_REGISTER_CHANGE, 1, 6, 0, 1);
   }

   if (b2.process() && b2_isWatched) {
      channel.out.data[0] = b2.getState();
      srdp_send_frame(&channel, OPCODE_REGISTER_CHANGE, 1, 7, 0, 1);
   }

   // limit update frequency to 50Hz
   delay(20);
}
