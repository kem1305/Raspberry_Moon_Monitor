#pragma once
#include <Arduino.h>
#include <LittleFS.h>
enum { SPI2_HOST = 1, SPI_DMA_CH_AUTO = 3 };
namespace lgfx {
struct BusCfg { int spi_host, spi_mode, freq_write, freq_read, dma_channel, pin_sclk, pin_mosi, pin_miso, pin_dc; bool spi_3wire, use_lock; };
struct Bus_SPI { BusCfg config() { return BusCfg(); } void config(const BusCfg&) {} };
struct PanelCfg { int pin_cs, pin_rst, pin_busy, panel_width, panel_height, offset_rotation; bool readable, invert, rgb_order, bus_shared; };
struct Panel_GC9A01 { PanelCfg config() { return PanelCfg(); } void config(const PanelCfg&) {} void setBus(Bus_SPI*) {} };
struct LGFX_Device {
  void setPanel(Panel_GC9A01*) {} bool init() { return true; } void setRotation(int) {} void setSwapBytes(bool) {}
  void fillScreen(int) {} void releaseBus() {} void pushImage(int, int, int, int, const uint16_t*) {}
  void qrcode(const char*, int, int, int, int) {} void setTextColor(int) {} void drawCenterString(const char*, int, int) {}
};
}
struct LGFX_Sprite {
  LGFX_Sprite(lgfx::LGFX_Device*) {}
  void setPsram(bool) {} void setColorDepth(int) {} void* createSprite(int, int) { return this; } void fillSprite(int) {}
  bool drawJpgFile(fs::FS&, const char*, int, int) { return true; } void* getBuffer() { return nullptr; }
};
