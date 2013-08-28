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

#include "RgbLed.h"

RgbLed::RgbLed() {
}

void RgbLed::attach(int rPin, int gPin, int b1Pin, int b2Pin) {
  _rPin = rPin;
  _gPin = gPin;
  _b1Pin = b1Pin;
  _b2Pin = b2Pin;
  pinMode(_rPin, OUTPUT);
  pinMode(_gPin, OUTPUT);
  pinMode(_b1Pin, OUTPUT);
  pinMode(_b2Pin, OUTPUT);
  write(0,0,0);
}

void RgbLed::write(int r, int g, int b) {
  analogWrite(_rPin, r);
  analogWrite(_gPin, g);
  analogWrite(_b1Pin, b);
  analogWrite(_b2Pin, b);
}

