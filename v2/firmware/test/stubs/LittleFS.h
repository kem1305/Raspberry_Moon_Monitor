#pragma once
namespace fs { struct FS { bool begin(bool) { return true; } }; }
static fs::FS LittleFS;
