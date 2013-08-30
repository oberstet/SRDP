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

SmoothAnalogInput::SmoothAnalogInput() {
    _pin = -1;
    _index = -1;
    _mapMax = 1024;
    _mapMin = 0;
    _res = 1;
    _last = -1;
    _watched = false;
}

bool SmoothAnalogInput::process() {
  int value = read();
  if (value != _last) {
    _last = value;
    return true;
  } else {
    return false;
  }
}

void SmoothAnalogInput::attach(int pin, int min, int max) {

    scale(min, max);

    _pin = pin;
    _index = 0;

    int start = analogRead(pin);
    _sampleTime = millis();
    
    for(int i = 0; i < SMOOTH_ANALOG_INPUT_SIZE; i++) {
        _samples[i] = start;
    }
}

void SmoothAnalogInput::scale(int min, int max) {
    if (max <= min) {
        return;
    }

    _mapMin = min;
    _mapMax = max;
    _last = min - 1; // impossible value

    _res = 1024 / (max - min) * 2;
}

int SmoothAnalogInput::raw() {
    if (_pin == -1) {
        return -1;
    }

    int value = analogRead(_pin);
    _sampleTime = millis();
    
    int last = _samples[_index];
    if (abs(value - last) <= _res) {
        value = last;
    }

    _index = (_index + 1) % SMOOTH_ANALOG_INPUT_SIZE;
    _samples[_index] = value;

    return value;
}

int SmoothAnalogInput::read() {
    raw();

    int total = 0;
    for(int i = 0; i < SMOOTH_ANALOG_INPUT_SIZE; i++) {
        total += _samples[i];
    }

    int current = total / SMOOTH_ANALOG_INPUT_SIZE;
    return map(current, 0, 1024, _mapMin, _mapMax);
}
