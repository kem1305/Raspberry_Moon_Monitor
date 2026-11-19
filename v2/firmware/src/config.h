// config.h — hardware mapping of the Moon Monitor v2 PCB (see hardware/README.md)
#pragma once

// ---- display header J2 -------------------------------------------------------------------------
// The 7 header positions P1..P7 are wired to these GPIOs. Which signal sits on which position
// depends on which way round your GC9A01 module's pins are, so there are two wirings:
//
//   DISPLAY_REVERSED 0 :  P1=RST P2=CS  P3=DC  P4=SDA P5=SCL P6=GND P7=VCC   (close JP_B: "GND6" + "VCC7")
//   DISPLAY_REVERSED 1 :  P1=VCC P2=GND P3=SCL P4=SDA P5=DC  P6=CS  P7=RST   (close JP_A: "VCC1" + "GND2")
//
// Look at the silkscreen of your module once it is seated on the PCB and pick the matching line.
#ifndef DISPLAY_REVERSED
#define DISPLAY_REVERSED 0
#endif

#define PIN_P1 21
#define PIN_P2 14
#define PIN_P3 13
#define PIN_P4 12
#define PIN_P5 11
#define PIN_P6 10
#define PIN_P7 9

#if DISPLAY_REVERSED
#define PIN_LCD_RST PIN_P7
#define PIN_LCD_CS  PIN_P6
#define PIN_LCD_DC  PIN_P5
#define PIN_LCD_SDA PIN_P4
#define PIN_LCD_SCL PIN_P3
#else
#define PIN_LCD_RST PIN_P1
#define PIN_LCD_CS  PIN_P2
#define PIN_LCD_DC  PIN_P3
#define PIN_LCD_SDA PIN_P4
#define PIN_LCD_SCL PIN_P5
#endif

#define PIN_LCD_POWER 47      // P-MOSFET gate: LOW = display powered, HIGH = display (and backlight) off
#define PIN_BUTTON 0          // to GND, external pull-up. Held at power-up = USB download mode

// ---- behaviour ---------------------------------------------------------------------------------
#define DISPLAY_ROTATION 1            // default 0..3 (x90 degrees); the module sits sideways in the case. Changeable in the setup page
#define INFO_TIMEOUT_MS 30000         // info screen falls back to the Moon after 30 s
#define LONG_PRESS_MS 5000            // hold 5 s -> setup portal
#define PORTAL_TIMEOUT_MS 600000      // setup portal closes by itself after 10 min (if already configured)
#define MOON_REFRESH_MS 60000
#define AP_SSID_PREFIX "MoonMonitor-"
