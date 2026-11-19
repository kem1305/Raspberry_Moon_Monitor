// Minimal host-side stand-ins for the Arduino-ESP32 API: just enough to type-check src/main.cpp on a PC
// (g++ -fsyntax-only, see ../check_syntax.sh). They do nothing at run time.
#pragma once
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <string>
#include <time.h>
#define PROGMEM
#define F(x) x
#define FPSTR(x) String(x)
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
class String {
  std::string s;
 public:
  String() {}
  String(const char* c) : s(c ? c : "") {}
  String(char c) : s(1, c) {}
  String(int v) : s(std::to_string(v)) {}
  String(unsigned v) : s(std::to_string(v)) {}
  String(long v) : s(std::to_string(v)) {}
  String(double v, int dec = 2) { char b[40]; snprintf(b, sizeof b, "%.*f", dec, v); s = b; }
  const char* c_str() const { return s.c_str(); }
  unsigned length() const { return s.size(); }
  void trim() {}
  void replace(const String&, const String&) {}
  void replace(char, char) {}
  int indexOf(char c) const { return (int)s.find(c); }
  String substring(int a, int b = -1) const { return String(s.substr(a, b < 0 ? std::string::npos : b - a).c_str()); }
  double toDouble() const { return atof(s.c_str()); }
  long toInt() const { return atol(s.c_str()); }
  String& operator+=(const String& o) { s += o.s; return *this; }
  String& operator+=(char c) { s += c; return *this; }
  String operator+(const String& o) const { String r(*this); r += o; return r; }
  bool operator==(const String& o) const { return s == o.s; }
  bool operator!=(const String& o) const { return s != o.s; }
  const char* begin() const { return s.c_str(); }
  const char* end() const { return s.c_str() + s.size(); }
};
inline String operator+(const char* a, const String& b) { return String(a) + b; }
inline void pinMode(int, int) {}
inline void digitalWrite(int, int) {}
inline int digitalRead(int) { return 1; }
inline uint32_t millis() { return 0; }
inline void delay(uint32_t) {}
inline void* ps_malloc(size_t n) { return malloc(n); }
inline void configTzTime(const char*, const char*, const char* = nullptr, const char* = nullptr) {}
struct SerialStub { void begin(int) {} void println(const char*) {} };
static SerialStub Serial;
struct EspStub { void restart() {} };
static EspStub ESP;
