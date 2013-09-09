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


// Wrappers for hardware components
//
SmoothAnalogInput pot1, pot2;
Button btn1, btn2;
RgbLed led3;


// EDS URI for the adapter
//
#define ADAPTER_EDS_URI    "http://eds.tavendo.com/adapter/arduino-demoboard"

// Optional adapter information
//
#define ADAPTER_HW_VERSION "Arduino Mega 2560"
#define ADAPTER_SW_VERSION "V1.0"

// EDS URIs for the connected devices
//
#define DEVICE1_EDS_URI "http://eds.tavendo.com/device/arduino-rgb-led"
#define DEVICE2_EDS_URI "http://eds.tavendo.com/device/arduino-combocontrol"
#define DEVICE3_EDS_URI "http://eds.tavendo.com/device/arduino-combocontrol"

// UUID of the adapter
//
static const uint8_t ADAPTER_UUID[] = {0xa4, 0x10, 0x4a, 0x89, 0x8d, 0xf1, 0x46, 0xe5, 0xa6, 0x4c, 0x3b, 0xc7, 0x37, 0xdf, 0xd2, 0xf4};

// UUIDs of the connected devices
//
static const uint8_t DEVICE1_UUID[] = {0xee, 0xce, 0x84, 0x0d, 0x24, 0x46, 0x49, 0x98, 0x85, 0x23, 0xbb, 0xd8, 0x4c, 0x78, 0x1f, 0x93};
static const uint8_t DEVICE2_UUID[] = {0xc0, 0x1a, 0xfa, 0x3d, 0x46, 0x63, 0x4e, 0x82, 0xbb, 0xec, 0xf1, 0x7c, 0x87, 0xa1, 0x16, 0x2f};
static const uint8_t DEVICE3_UUID[] = {0x1f, 0xfd, 0xf7, 0xdb, 0x1d, 0xa5, 0x40, 0xc9, 0xa1, 0x30, 0xab, 0xe6, 0xf2, 0x70, 0x0f, 0x40};

// Device index of adapter
//
#define ADAPTER_DEVICE_INDEX     1

// Device indices of devices
//
#define DEVICE1_DEVICE_INDEX     2
#define DEVICE2_DEVICE_INDEX     3
#define DEVICE3_DEVICE_INDEX     4

// Standard registers for adapter
//
#define ADAPTER_REGISTER_INDEX_UUID          1
#define ADAPTER_REGISTER_INDEX_EDS           2
#define ADAPTER_REGISTER_INDEX_HW_VERSION    3
#define ADAPTER_REGISTER_INDEX_SW_VERSION    4
#define ADAPTER_REGISTER_INDEX_DEVICES       5

// Custom registers for adapter
//
#define ADAPTER_REGISTER_INDEX_FREEMEM       1024
#define ADAPTER_REGISTER_INDEX_USERDATA      1025
#define ADAPTER_REGISTER_INDEX_USERDATA_SIZE 64  // MUST BE <= SRDP_FRAME_DATA_MAX_LEN

// Standard registers for devices
//
#define DEVICE_REGISTER_INDEX_UUID              1
#define DEVICE_REGISTER_INDEX_EDS               2
#define DEVICE_REGISTER_INDEX_HW_VERSION        3
#define DEVICE_REGISTER_INDEX_SW_VERSION        4

// Device registers for "Color Light"
//
#define DEVICE_REGISTER_INDEX_COLOR_LIGHT             1024
//#define DEVICE_REGISTER_INDEX_COLOR_LIGHT_FLASHRATE   1025

// Device registers for "Combo Control"
//
#define DEVICE_REGISTER_INDEX_COMBO_CONTROL_LIGHT           1024
#define DEVICE_REGISTER_INDEX_COMBO_CONTROL_BUTTON          1025
#define DEVICE_REGISTER_INDEX_COMBO_CONTROL_BUTTON_WATCH    1026
#define DEVICE_REGISTER_INDEX_COMBO_CONTROL_SLIDER          1027
#define DEVICE_REGISTER_INDEX_COMBO_CONTROL_SLIDER_MAX      1028
#define DEVICE_REGISTER_INDEX_COMBO_CONTROL_SLIDER_WATCH    1029
#define DEVICE_REGISTER_INDEX_COMBO_CONTROL_SLIDER_URATE    1030
//#define DEVICE_REGISTER_INDEX_COMBO_CONTROL_SLIDER_SMOOTH   1031


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

   switch (dev) {

      case ADAPTER_DEVICE_INDEX:
         switch (reg) {

            // mandatory adapter register with adapter UUID
            //
            case ADAPTER_REGISTER_INDEX_UUID:
               memcpy(data, ADAPTER_UUID, sizeof(ADAPTER_UUID));
               return sizeof(ADAPTER_UUID);

            // mandatory adapter register with adapter EDS URI
            //
            case ADAPTER_REGISTER_INDEX_EDS:
               return srdp_set_string(data, ADAPTER_EDS_URI);

            // optional adapter register with hardware version
            //
            case ADAPTER_REGISTER_INDEX_HW_VERSION:
               return srdp_set_string(data, ADAPTER_HW_VERSION);

            // optional adapter register with software version
            //
            case ADAPTER_REGISTER_INDEX_SW_VERSION:
               return srdp_set_string(data, ADAPTER_SW_VERSION);

            // mandatory adapter register with list of connected devices
            //
            case ADAPTER_REGISTER_INDEX_DEVICES:
               // for our board, the list of connected devices is fixed/static
               *((uint16_t*) (data + 0)) = 3;
               *((uint16_t*) (data + 2)) = DEVICE1_DEVICE_INDEX;
               *((uint16_t*) (data + 4)) = DEVICE2_DEVICE_INDEX;
               *((uint16_t*) (data + 6)) = DEVICE3_DEVICE_INDEX;
               return 8;

            // custom adapter register: current free RAM
            //
            case ADAPTER_REGISTER_INDEX_FREEMEM:
               *((uint32_t*) data) = freeRam();
               return 4;

            // custom adapter register: arbitrary, persistent user data
            //
            case ADAPTER_REGISTER_INDEX_USERDATA:
               if (len == 0) {
                  *((uint16_t*) data) = ADAPTER_REGISTER_INDEX_USERDATA_SIZE;
                  return 2;
               }
               else if (pos + len <= ADAPTER_REGISTER_INDEX_USERDATA_SIZE) {
                  readEEPROM(0 + pos, data, len);
                  return len;
               } else {
                  return SRDP_ERR_INVALID_REG_POSLEN;
               }

            default:
               return SRDP_ERR_NO_SUCH_REGISTER;
         }

      case DEVICE1_DEVICE_INDEX:
         switch (reg) {

            // mandatory device register with device UUID
            //
            case DEVICE_REGISTER_INDEX_UUID:
               memcpy(data, DEVICE1_UUID, sizeof(DEVICE1_UUID));
               return sizeof(DEVICE1_UUID);

            // mandatory device register with device EDS URI
            //
            case DEVICE_REGISTER_INDEX_EDS:
               return srdp_set_string(data, DEVICE1_EDS_URI);

            // the LED is "write-only"
            //
            case DEVICE_REGISTER_INDEX_COLOR_LIGHT:
               return SRDP_ERR_INVALID_REG_OP;

            default:
               return SRDP_ERR_NO_SUCH_REGISTER;
         }

      case DEVICE2_DEVICE_INDEX:
      case DEVICE3_DEVICE_INDEX:
         {
            Button* btn             = dev == DEVICE2_DEVICE_INDEX ? &btn1 : &btn2;
            SmoothAnalogInput* pot  = dev == DEVICE2_DEVICE_INDEX ? &pot1 : &pot2;
            const uint8_t* uuid     = dev == DEVICE2_DEVICE_INDEX ? DEVICE2_UUID : DEVICE3_UUID;
            const char* edsUri      = dev == DEVICE2_DEVICE_INDEX ? DEVICE2_EDS_URI : DEVICE3_EDS_URI;

            switch (reg) {

               // mandatory device register with device UUID
               //
               case DEVICE_REGISTER_INDEX_UUID:
                  memcpy(data, uuid, 16);
                  return 16;

               // mandatory device register with device EDS URI
               //
               case DEVICE_REGISTER_INDEX_EDS:
                  return srdp_set_string(data, edsUri);

               case DEVICE_REGISTER_INDEX_COMBO_CONTROL_LIGHT:
                  return SRDP_ERR_INVALID_REG_OP;

               case DEVICE_REGISTER_INDEX_COMBO_CONTROL_BUTTON:
                  *((uint32_t*) (data + 0)) = btn->getTime();
                  *((uint8_t*) (data + 4)) = btn->getState();
                  return 5;

               case DEVICE_REGISTER_INDEX_COMBO_CONTROL_BUTTON_WATCH:
                  *((uint8_t*) data) = btn->isWatched();
                  return 1;

               case DEVICE_REGISTER_INDEX_COMBO_CONTROL_SLIDER:
                  *((uint32_t*) (data + 0)) = pot->getTime();
                  *((uint16_t*) (data + 4)) = pot->getState();
                  return 6;

               case DEVICE_REGISTER_INDEX_COMBO_CONTROL_SLIDER_MAX:
                  *((uint16_t*) data) = pot->getMax();
                  return 2;

               case DEVICE_REGISTER_INDEX_COMBO_CONTROL_SLIDER_WATCH:
                  *((uint8_t*) data) = pot->isWatched();
                  return 1;

               case DEVICE_REGISTER_INDEX_COMBO_CONTROL_SLIDER_URATE:
                  *((float*) data) = pot->getUpdateRate();
                  return 4;

               default:
                  return SRDP_ERR_NO_SUCH_REGISTER;
            }
         }

      default:
         return SRDP_ERR_NO_SUCH_DEVICE;
   }
}


// Register write handler called when host requests to write a register
//
int register_write(void* userdata, int dev, int reg, int pos, int len, const uint8_t* data) {

   switch (dev) {

      case ADAPTER_DEVICE_INDEX:
         switch (reg) {

            case ADAPTER_REGISTER_INDEX_UUID:
            case ADAPTER_REGISTER_INDEX_EDS:
            case ADAPTER_REGISTER_INDEX_FREEMEM:
               return SRDP_ERR_INVALID_REG_OP;

            case ADAPTER_REGISTER_INDEX_USERDATA:
               if (pos + len <= ADAPTER_REGISTER_INDEX_USERDATA_SIZE) {
                  writeEEPROM(0 + pos, data, len);
                  return len;
               } else {
                  return SRDP_ERR_INVALID_REG_POSLEN;
               }

            default:
               return SRDP_ERR_NO_SUCH_REGISTER;
         }

      case DEVICE1_DEVICE_INDEX:
         switch (reg) {

            case DEVICE_REGISTER_INDEX_COLOR_LIGHT:
               led3.write(data[0], data[1], data[2]);
               return 3;

            default:
               return SRDP_ERR_NO_SUCH_REGISTER;
         }

      case DEVICE2_DEVICE_INDEX:
      case DEVICE3_DEVICE_INDEX:
         {
            Button* btn = dev == DEVICE2_DEVICE_INDEX ? &btn1 : &btn2;
            SmoothAnalogInput* pot = dev == DEVICE2_DEVICE_INDEX ? &pot1 : &pot2;
            int pin = dev == DEVICE2_DEVICE_INDEX ? PIN_LED1 : PIN_LED2;

            switch (reg) {

               case DEVICE_REGISTER_INDEX_COMBO_CONTROL_LIGHT:
                  digitalWrite(pin, data[0] ? HIGH : LOW);
                  return 1;

               case DEVICE_REGISTER_INDEX_COMBO_CONTROL_BUTTON:
                  return SRDP_ERR_INVALID_REG_OP;

               case DEVICE_REGISTER_INDEX_COMBO_CONTROL_BUTTON_WATCH:
                  btn->setWatched(data[0] != 0);
                  return 1;

               case DEVICE_REGISTER_INDEX_COMBO_CONTROL_SLIDER:
                  return SRDP_ERR_INVALID_REG_OP;

               case DEVICE_REGISTER_INDEX_COMBO_CONTROL_SLIDER_MAX:
                  pot->scale(0, *((const uint16_t*) data));
                  return 2;

               case DEVICE_REGISTER_INDEX_COMBO_CONTROL_SLIDER_WATCH:
                  pot->setWatched(data[0] != 0);
                  return 1;

               case DEVICE_REGISTER_INDEX_COMBO_CONTROL_SLIDER_URATE:
                  pot->setUpdateRate(*((const float*) data));
                  return 4;

               default:
                  return SRDP_ERR_NO_SUCH_REGISTER;
            }
         }

      default:
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
             transport_write, transport_read,
             register_write, register_read,
             0,
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
      srdp_notify(&channel, DEVICE2_DEVICE_INDEX, DEVICE_REGISTER_INDEX_COMBO_CONTROL_BUTTON, 0, 0);
   }

   if (btn2.process() && btn2.isWatched()) {
      srdp_notify(&channel, DEVICE3_DEVICE_INDEX, DEVICE_REGISTER_INDEX_COMBO_CONTROL_BUTTON, 0, 0);
   }

   // process potis
   //
   if (pot1.process() && pot1.isWatched()) {
      srdp_notify(&channel, DEVICE2_DEVICE_INDEX, DEVICE_REGISTER_INDEX_COMBO_CONTROL_SLIDER, 0, 0);
   }

   if (pot2.process() && pot2.isWatched()) {
      srdp_notify(&channel, DEVICE3_DEVICE_INDEX, DEVICE_REGISTER_INDEX_COMBO_CONTROL_SLIDER, 0, 0);
   }

   // limit update frequency
   //
   delay(10);
}
