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

#ifndef SMOOTHANALOGINPUT_H
#define SMOOTHANALOGINPUT_H

#include <Arduino.h>

#define SMOOTH_ANALOG_INPUT_SIZE 16

class SmoothAnalogInput {
    public:
        SmoothAnalogInput();
        void attach(int pin, int min, int max);
        void scale(int min, int max);
        int read();
        int raw();
        bool process();
    private:
        int _samples[SMOOTH_ANALOG_INPUT_SIZE];
        int _pin;
        int _index;
        int _mapMin;
        int _mapMax;
        int _res;
        int _last;
        long _sampleTime;
};

#endif // SMOOTHANALOGINPUT_H

