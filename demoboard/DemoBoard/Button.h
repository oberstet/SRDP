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

#ifndef BUTTON_H
#define BUTTON_H

#include <Arduino.h>

class Button {
   public:
      Button();
      void attach(int pin, int debounceInterval = 50);
      bool process();
      int getState() { return _state; };
      long getTime() { return _sampleTime; };
   private:
      int _pin;
      int _state;
      long _sampleTime;
      int _lastState;
      long _changed;
      int _debounceInterval;
};

#endif // BUTTON_H
