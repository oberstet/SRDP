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

#ifndef RGBLED_H
#define RGBLED_H

#include <Arduino.h>

class RgbLed {
   public:
      RgbLed();
      void attach(int rPin, int gPin, int b1Pin, int b2Pin);
      void write(int r, int g, int b);
   private:
      int _rPin;
      int _gPin;
      int _b1Pin;
      int _b2Pin;
};

#endif // RGBLED_H
