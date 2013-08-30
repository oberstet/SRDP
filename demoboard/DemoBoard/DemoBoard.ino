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

#include <string.h>

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
#define IDX_DEV               1

#define IDX_REG_ID            1
#define IDX_REG_EDS           2

#define IDX_REG_LED1          1024
#define IDX_REG_LED2          1025
#define IDX_REG_LED3          1026

#define IDX_REG_BTN1          1027
#define IDX_REG_BTN1_WATCH    1028

#define IDX_REG_BTN2          1029
#define IDX_REG_BTN2_WATCH    1030

#define IDX_REG_POT1          1031
#define IDX_REG_POT1_MAX      1032
#define IDX_REG_POT1_WATCH    1033
#define IDX_REG_POT1_URATE    1034

#define IDX_REG_POT2          1035
#define IDX_REG_POT2_MAX      1036
#define IDX_REG_POT2_WATCH    1037
#define IDX_REG_POT2_URATE    1038


// URIs of the driver and device electronic datasheet (EDS)
//
#define URI_DRIVER_EDS "http://eds.device.tavendo.de/arduino/demoboard"
#define URI_DEVICE_EDS "http://eds.device.tavendo.de/arduino/demoboard"

// UUIDs of the driver and device
//
static const uint8_t UUID_DRIVER[] = {0x6B, 0x32, 0xA0, 0x7A, 0x7F, 0xC8, 0x47, 0xBB, 0x9D, 0x81, 0xF1, 0x41, 0x55, 0x0F, 0x60, 0x4F};
static const uint8_t UUID_DEVICE[] = {0x93, 0xA0, 0x1C, 0x71, 0x03, 0xFC, 0x4D, 0x9E, 0x85, 0x2E, 0xBD, 0x2D, 0x8C, 0x82, 0x4D, 0xE8};


// Wrappers for hardware components
//
SmoothAnalogInput pot1, pot2;
Button btn1, btn2;
RgbLed led3;


// SRDP channel to communicate with host
//
srdp_channel_t channel;


// Transport reader function used by the SRDP channel
//
ssize_t transport_read (void* userdata, uint8_t* data, size_t len) {
   if (Serial.available() > 0) {
      return Serial.readBytes((char*) data, len);
   } else {
      return 0;
   }
}


// Transport writer function used by the SRDP channel
//
ssize_t transport_write (void* userdata, const uint8_t* data, size_t len) {
   Serial.write(data, len);
   return len;
}


// Register read handler called when host requests to read a register
//
int register_read (void* userdata, int dev, int reg, int pos, int len, uint8_t* data) {
   if (dev == IDX_DEV) {
      int l;

      switch (reg) {

         // Device UUID
         //
         case IDX_REG_ID:
            l = sizeof(UUID_DEVICE);
            if (pos == 0 && (len == l || len == 0)) {
               memcpy(data, UUID_DEVICE, l);
               return l;
            } else {
               return SRDP_ERR_INVALID_REG_POSLEN;
            }

         // Device EDS
         //
         case IDX_REG_EDS:
            l = sizeof(URI_DEVICE_EDS);
            if (pos == 0 && (len == l || len == 0)) {
               strncpy((char*) data, URI_DEVICE_EDS, l);
               return l;
            } else {
               return SRDP_ERR_INVALID_REG_POSLEN;
            }

         // Buttons
         //
         case IDX_REG_BTN1:
         case IDX_REG_BTN2:
            if (pos == 0 && (len == 1 || len == 0)) {

               if (reg == IDX_REG_BTN1) {
                  data[0] = btn1.getState();
               } else {
                  data[0] = btn2.getState();
               }
               return 1;
            } else {
               return SRDP_ERR_INVALID_REG_POSLEN;
            }

         // Potis
         //
         case IDX_REG_POT1:
         case IDX_REG_POT2:
            if (pos == 0 && (len == 2 || len == 0)) {

               if (reg == IDX_REG_POT1) {
                  *((uint16_t*) data) = pot1.getState();
               } else {
                  *((uint16_t*) data) = pot2.getState();
               }
               return 2;
            } else {
               return SRDP_ERR_INVALID_REG_POSLEN;
            }

         // Poti 1/2, Button 1/2 : #watch
         //
         case IDX_REG_POT1_WATCH:
         case IDX_REG_POT2_WATCH:
         case IDX_REG_BTN1_WATCH:
         case IDX_REG_BTN2_WATCH:
            if (pos == 0 && len == 1) {
               switch (reg) {
                  case IDX_REG_POT1_WATCH:
                     *((uint8_t*) data) = pot1.isWatched();
                     break;
                  case IDX_REG_POT2_WATCH:
                     *((uint8_t*) data) = pot2.isWatched();
                     break;
                  case IDX_REG_BTN1_WATCH:
                     *((uint8_t*) data) = btn1.isWatched();
                     break;
                  case IDX_REG_BTN2_WATCH:
                     *((uint8_t*) data) = btn2.isWatched();
                     break;
                  default:
                     // should not arrive here
                     break;
               }
               return 1;
            } else {
               return SRDP_ERR_INVALID_REG_POSLEN;
            }         

         // Poti 1/2 : #max
         //
         case IDX_REG_POT1_MAX:
         case IDX_REG_POT2_MAX:
            if (pos == 0 && len == 2) {
               switch (reg) {
                  case IDX_REG_POT1_MAX:
                     *((uint16_t*) data) = pot1.getMax();
                     break;
                  case IDX_REG_POT2_MAX:
                     *((uint16_t*) data) = pot2.getMax();
                     break;
                  default:
                     // should not arrive here
                     break;
               }
               return 2;
            } else {
               return SRDP_ERR_INVALID_REG_POSLEN;
            }         

         // Poti 1/2 : #updateRate
         //
         case IDX_REG_POT1_URATE:
         case IDX_REG_POT2_URATE:
            if (pos == 0 && len == 2) {
               switch (reg) {
                  case IDX_REG_POT1_URATE:
                     *((uint16_t*) data) = pot1.getUpdateRate();
                     break;
                  case IDX_REG_POT2_URATE:
                     *((uint16_t*) data) = pot2.getUpdateRate();
                     break;
                  default:
                     // should not arrive here
                     break;
               }
               return 2;
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
int register_write(void* userdata, int dev, int reg, int pos, int len, const uint8_t* data) {

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

         // Poti 1/2, Button 1/2 : #watch
         //
         case IDX_REG_POT1_WATCH:
         case IDX_REG_POT2_WATCH:
         case IDX_REG_BTN1_WATCH:
         case IDX_REG_BTN2_WATCH:
            if (pos == 0 && len == 1) {
               switch (reg) {
                  case IDX_REG_POT1_WATCH:
                     pot1.setWatched(data[0] != 0);
                     break;
                  case IDX_REG_POT2_WATCH:
                     pot2.setWatched(data[0] != 0);
                     break;
                  case IDX_REG_BTN1_WATCH:
                     btn1.setWatched(data[0] != 0);
                     break;
                  case IDX_REG_BTN2_WATCH:
                     btn2.setWatched(data[0] != 0);
                     break;
                  default:
                     // should not arrive here
                     break;
               }
               return 1;
            } else {
               return SRDP_ERR_INVALID_REG_POSLEN;
            }         

         // Poti 1/2 : #max
         //
         case IDX_REG_POT1_MAX:
         case IDX_REG_POT2_MAX:
            if (pos == 0 && len == 2) {
               uint16_t max = *((const uint16_t*) data);
               switch (reg) {
                  case IDX_REG_POT1_MAX:
                     pot1.scale(0, max);
                     break;
                  case IDX_REG_POT2_MAX:
                     pot2.scale(0, max);
                     break;
                  default:
                     // should not arrive here
                     break;
               }
               return 2;
            } else {
               return SRDP_ERR_INVALID_REG_POSLEN;
            }         

         // Poti 1/2 : #updateRate
         //
         case IDX_REG_POT1_URATE:
         case IDX_REG_POT2_URATE:
            if (pos == 0 && len == 2) {
               uint16_t urate = *((const uint16_t*) data);
               switch (reg) {
                  case IDX_REG_POT1_URATE:
                     pot1.setUpdateRate(urate);
                     break;
                  case IDX_REG_POT2_URATE:
                     pot2.setUpdateRate(urate);
                     break;
                  default:
                     // should not arrive here
                     break;
               }
               return 2;
            } else {
               return SRDP_ERR_INVALID_REG_POSLEN;
            }         

         case IDX_REG_BTN1:         
         case IDX_REG_BTN2:
         case IDX_REG_POT1:
         case IDX_REG_POT2:
            return SRDP_ERR_INVALID_REG_OP;

         default:
            return SRDP_ERR_NO_SUCH_REGISTER;
      }
   } else {
      return SRDP_ERR_NO_SUCH_DEVICE;
   }
}


void log_message(void* userdata, const char* msg, int level) {
   Serial.println(msg);
}


// Arduino setup function executed once after reset
//
void setup() {

   // configure serial interface
   //
   Serial.begin(115200); // default SERIAL_8N1
   Serial.setTimeout(10);
   //Serial.flush();

   // setup SRDP channel over serial
   //
   srdp_init_channel(&channel);
   channel.transport_read = transport_read;
   channel.transport_write = transport_write;
   channel.register_read = register_read;
   channel.register_write = register_write;
   channel.log_message = log_message;

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

   // process SRDP
   //
   while (Serial.available()) {
      srdp_loop(&channel);
   }


   // process buttons
   //
   if (btn1.process() && btn1.isWatched()) {
      // OR: simply trigger a read register .. code only once.

      // when button changed, report change to SRDP
      uint8_t data = btn1.getState();
      srdp_register_change(&channel, IDX_DEV, IDX_REG_BTN1, 0, sizeof(data), (const uint8_t*) &data);
   }

   if (btn2.process() && btn2.isWatched()) {
      uint8_t data = btn2.getState();
      srdp_register_change(&channel, IDX_DEV, IDX_REG_BTN2, 0, sizeof(data), (const uint8_t*) &data);
   }


   // process potis
   //
   if (pot1.process() && pot1.isWatched()) {
      uint16_t data = pot1.getState();
      srdp_register_change(&channel, IDX_DEV, IDX_REG_POT1, 0, sizeof(data), (const uint8_t*) &data);
   }

   if (pot2.process() && pot2.isWatched()) {
      uint16_t data = pot2.getState();
      srdp_register_change(&channel, IDX_DEV, IDX_REG_POT2, 0, sizeof(data), (const uint8_t*) &data);
   }


   // limit update frequency
   //
   delay(20);
}
