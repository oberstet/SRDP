//////////////////////////////////////////////////////////////////////////////
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
//////////////////////////////////////////////////////////////////////////////

//
// Arduino "Demoboard" SRDP Driver.
//

#include <Arduino.h>
#include <EEPROM.h>

#include <string.h>

#include "SmoothAnalogInput.h"
#include "Button.h"
#include "RgbLed.h"

//#define SRDP_DUMMY
//#define SRDP_CRC16_BIG_AND_FAST
//#define SRDP_FRAME_DATA_MAX_LEN 512
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

// URIs of the driver and device electronic datasheet (EDS)
//
#define URI_ADAPTER_EDS "http://eds.tavendo.com/adapter/arduino-demoboard"
#define URI_DEVICE_EDS "http://eds.device.tavendo.de/arduino/demoboard"

// UUIDs of the driver and device
//
static const uint8_t UUID_ADAPTER[] = {0x6B, 0x32, 0xA0, 0x7A, 0x7F, 0xC8, 0x47, 0xBB, 0x9D, 0x81, 0xF1, 0x41, 0x55, 0x0F, 0x60, 0x4F};
static const uint8_t UUID_DEVICE[] = {0x93, 0xA0, 0x1C, 0x71, 0x03, 0xFC, 0x4D, 0x9E, 0x85, 0x2E, 0xBD, 0x2D, 0x8C, 0x82, 0x4D, 0xE8};


// Indices of SRDP Registers the Demoboard will expose
//
#define IDX_DEV               1

// Custom registers for driver (aka "device 0")
//
#define IDX_REG_FREE_RAM      1024

// Registers of device 1 (our demoboard hardware)
//
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

#define IDX_REG_USERSTORE     1039
#define SIZ_REG_USERSTORE     64    // MUST BE <= SRDP_FRAME_DATA_MAX_LEN

// Wrappers for hardware components
//
SmoothAnalogInput pot1, pot2;
Button btn1, btn2;
RgbLed led3;


// Little function that returns free ram on Arduino.
// From here: http://jeelabs.org/2011/05/22/atmega-memory-use/
//
int freeRam () {
   extern int __heap_start, *__brkval; 
   int v; 
   return (int) &v - (__brkval == 0 ? (int) &__heap_start : (int) __brkval); 
}


void readEEPROM(int offset, uint8_t* data, int length) {
   for (int i = 0; i < length; ++i) {
      data[i] = EEPROM.read(offset + i);
   }
}

void writeEEPROM(int offset, const uint8_t* data, int length) {
   for (int i = 0; i < length; ++i) {
      EEPROM.write(offset + i, data[i]);
   }
}

void log_message(const char* msg, int level) {
   Serial.println(msg);
}


// SRDP channel to communicate with host.
//
// Note: the SRDP channel (and all it's internals) is designed to be
// able to resides on heap or stack. In our example here, the channel
// and all it's internal stuff resides on the stack (which is great
// for use on tiny embedded platforms like Arduino).
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

      switch (reg) {

         // Device UUID
         //
         case IDX_REG_ID:
            memcpy(data, UUID_DEVICE, sizeof(UUID_DEVICE));
            return sizeof(UUID_DEVICE);

         // Device EDS
         //
         case IDX_REG_EDS:
            strncpy((char*) data, URI_DEVICE_EDS, sizeof(URI_DEVICE_EDS));
            return sizeof(URI_DEVICE_EDS);

         // Buttons
         //
         case IDX_REG_BTN1:
            *((uint32_t*) (data + 0)) = btn1.getTime();
            *((uint8_t*) (data + 4)) = btn1.getState();
            return 5;
         case IDX_REG_BTN2:
            *((uint32_t*) (data + 0)) = btn2.getTime();
            *((uint8_t*) (data + 4)) = btn2.getState();
            return 5;

         // Potis
         //
         case IDX_REG_POT1:
            *((uint32_t*) (data + 0)) = pot1.getTime();
            *((uint16_t*) (data + 4)) = pot1.getState();
            return 6;
         case IDX_REG_POT2:
            *((uint32_t*) (data + 0)) = pot2.getTime();
            *((uint16_t*) (data + 4)) = pot2.getState();
            return 6;

         // Poti 1/2, Button 1/2 : #watch
         //
         case IDX_REG_POT1_WATCH:
            *((uint8_t*) data) = pot1.isWatched();
            return 1;
         case IDX_REG_POT2_WATCH:
            *((uint8_t*) data) = pot2.isWatched();
            return 1;
         case IDX_REG_BTN1_WATCH:
            *((uint8_t*) data) = btn1.isWatched();
            return 1;
         case IDX_REG_BTN2_WATCH:
            *((uint8_t*) data) = btn2.isWatched();
            return 1;

         // Poti 1/2 : #max
         //
         case IDX_REG_POT1_MAX:
            *((uint16_t*) data) = pot1.getMax();
            return 2;
         case IDX_REG_POT2_MAX:
            *((uint16_t*) data) = pot2.getMax();
            return 2;

         // Poti 1/2 : #updateRate
         //
         case IDX_REG_POT1_URATE:
            *((uint16_t*) data) = pot1.getUpdateRate();
            return 2;
         case IDX_REG_POT2_URATE:
            *((uint16_t*) data) = pot2.getUpdateRate();
            return 2;

         // persistent register (type "B*" - a vector of uint8s)
         //
         case IDX_REG_USERSTORE:
            if (len == 0) {
               *((uint16_t*) data) = SIZ_REG_USERSTORE;
               return 2;
            }
            else if (pos + len <= SIZ_REG_USERSTORE) {
               readEEPROM(0 + pos, data, len);
               return len;
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
   } else if (dev == 0) {

      // custom registers for driver (aka "device 0")
      //
      switch (reg) {

         // Device UUID
         //
         case IDX_REG_ID:
            memcpy(data, UUID_ADAPTER, sizeof(UUID_ADAPTER));
            return sizeof(UUID_ADAPTER);

         // Device EDS
         //
         case IDX_REG_EDS:
            strncpy((char*) data, URI_ADAPTER_EDS, sizeof(URI_ADAPTER_EDS));
            return sizeof(URI_ADAPTER_EDS);

         // current free memory
         //
         case IDX_REG_FREE_RAM:
            *((uint32_t*) data) = freeRam();
            return 4;

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
            digitalWrite(IDX_REG_LED1, data[0] ? HIGH : LOW);
            return 1;

         case IDX_REG_LED2:
            digitalWrite(IDX_REG_LED2, data[0] ? HIGH : LOW);
            return 1;

         // LED 3 (RGB)
         //
         case IDX_REG_LED3:
            led3.write(data[0], data[1], data[2]);
            return 3;

         // Poti 1/2, Button 1/2 : #watch
         //
         case IDX_REG_POT1_WATCH:
            pot1.setWatched(data[0] != 0);
            return 1;
         case IDX_REG_POT2_WATCH:
            pot2.setWatched(data[0] != 0);
            return 1;
         case IDX_REG_BTN1_WATCH:
            btn1.setWatched(data[0] != 0);
            return 1;
         case IDX_REG_BTN2_WATCH:
            btn2.setWatched(data[0] != 0);
            return 1;

         // Poti 1/2 : #max
         //
         case IDX_REG_POT1_MAX:
            pot1.scale(0, *((const uint16_t*) data));
            return 2;
         case IDX_REG_POT2_MAX:
            pot2.scale(0, *((const uint16_t*) data));
            return 2;

         // Poti 1/2 : #updateRate
         //
         case IDX_REG_POT1_URATE:
            pot1.setUpdateRate(*((const uint16_t*) data));
            return 2;
         case IDX_REG_POT2_URATE:
            pot2.setUpdateRate(*((const uint16_t*) data));
            return 2;

         // persistent register
         //
         case IDX_REG_USERSTORE:
            if (pos + len <= SIZ_REG_USERSTORE) {
               writeEEPROM(0 + pos, data, len);
               return len;
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


// Arduino setup function executed once after reset
//
void setup() {

   // configure serial interface
   //
   Serial.begin(115200); // default SERIAL_8N1
   Serial.setTimeout(0);
   //Serial.setTimeout(10);

   // setup SRDP channel over serial
   //
   srdp_init(&channel,
             transport_write,
             transport_read,
             register_write,
             register_read,
             log_message,
             0);

   // LED 1
   pinMode(PIN_LED1, OUTPUT);
   digitalWrite(PIN_LED1, LOW);

   // LED 2
   pinMode(PIN_LED2, OUTPUT);
   digitalWrite(PIN_LED2, LOW);

   // LED 3
   led3.attach(PIN_LED3_R, PIN_LED3_G, PIN_LED3_B1, PIN_LED3_B2);
  
   // Buttons
   btn1.attach(PIN_BTN1);
   btn2.attach(PIN_BTN2);
  
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
      // when button changed, trigger sending of SRDP change frame
      srdp_notify(&channel, IDX_DEV, IDX_REG_BTN1, 0, 0);
   }

   if (btn2.process() && btn2.isWatched()) {
      srdp_notify(&channel, IDX_DEV, IDX_REG_BTN2, 0, 0);
   }

   // process potis
   //
   if (pot1.process() && pot1.isWatched()) {
      srdp_notify(&channel, IDX_DEV, IDX_REG_POT1, 0, 0);
   }

   if (pot2.process() && pot2.isWatched()) {
      srdp_notify(&channel, IDX_DEV, IDX_REG_POT2, 0, 0);
   }

   // limit update frequency
   //
   delay(20);
}
