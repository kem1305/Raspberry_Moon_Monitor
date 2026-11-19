#!/bin/sh
# Type-check the firmware on a PC against minimal Arduino stubs (catches typos without the ESP32 toolchain).
cd "$(dirname "$0")" && g++ -std=gnu++17 -fsyntax-only -Wall -Wextra -Wno-unused-parameter -Wno-unused-function -Wno-unused-variable -Istubs -I../src ../src/main.cpp && echo "syntax OK"
