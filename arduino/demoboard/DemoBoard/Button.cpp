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

#include "Button.h"

Button::Button() {
}

void Button::attach(int pin, int debounceInterval) {
   _pin = pin;
   _state = -1;
   _lastState = -1;
   _debounceInterval = debounceInterval;
   pinMode(_pin, INPUT);
}

bool Button::process() {
   int val = digitalRead(_pin) ? 0 : 1;
   //unsigned long now = millis();
   unsigned long now = micros();

   if (val != _lastState) {
      _changed = now;
   }
  
   _lastState = val;
 
   if ((now - _changed) > _debounceInterval && _state != val) {
      _state = val;
      _sampleTime = now;
      return true;
   } else {
      return false;
   }
}
