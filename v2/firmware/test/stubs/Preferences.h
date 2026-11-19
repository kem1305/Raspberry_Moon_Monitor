#pragma once
#include <Arduino.h>
struct Preferences {
  void begin(const char*, bool) {}
  bool getBool(const char*, bool d) { return d; } String getString(const char*, const char* d) { return d; }
  double getDouble(const char*, double d) { return d; } uint8_t getUChar(const char*, uint8_t d) { return d; }
  uint16_t getUShort(const char*, uint16_t d) { return d; }
  void putBool(const char*, bool) {} void putString(const char*, const String&) {} void putDouble(const char*, double) {}
  void putUChar(const char*, uint8_t) {} void putUShort(const char*, uint16_t) {}
};
