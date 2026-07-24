# Moon Monitor – Real-time Moon Phase Display

A real-time realistic Moon phase display with additional Moon information accessible via a push button.  
Built with a Raspberry Pi Zero 2W and a 1.28" round TFT display.

This is my first project ever with a Raspberry Pi (and with Python). I'm a 50-year-old nerd who still has some potential left — especially with a little help from AI.

I originally wanted to build a small aviation radar I saw on my feed. I succeeded, but it wasn't that satisfying.  
Since my wife and I are avid night-sky observers, I came up with the idea of a realistic Moon tracker instead.  
This is how the **Moon Monitor** was born.

The finished unit now sits proudly on my wife's nightstand.

---

## Hardware Components

- 1× Raspberry Pi Zero 2W with 32 GB SD Card (a smaller card is also fine)
- 1× 1.28" Round TFT Display **GC9A01**
- 1× Push button 6×6×11 (4 pins — can also use a 2-pin version)
- Jumper cables for connections
- Mini-USB power source (I used an older charger with an old cable)

---

## Wiring / Connections

### Display (GC9A01)

| Display Pin | Raspberry Pi GPIO | Notes                  |
|-------------|-------------------|------------------------|
| RST         | GPIO27            | Display reset          |
| CS          | GPIO8             | SPI0 CE0 (chip select) |
| DC          | GPIO22            | Data/Command           |
| SDA         | GPIO10            | SPI0 MOSI              |
| SCL         | GPIO11            | SPI0 SCLK              |
| GND         | GND               | Ground                 |
| VCC         | 3.3V              | Display power          |

### Push Button

| Button Side | Raspberry Pi GPIO | Notes                        |
|-------------|-------------------|------------------------------|
| Side 1      | GPIO17            | Digital input                |
| Side 2      | GND               | Ground (use internal pull-up)|

---

## Software

The main program is `main.py`.

### Required libraries

```python
import sys
import math
import time
import signal
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageEnhance   # image handling, effects & transformations
import ephem                                               # astronomical calculations
import RPi.GPIO as GPIO
import GC9A01                                              # display driver for GC9A01

---

## 3D Printed Case

The enclosure was designed in **Fusion 360** and printed on a **Bambu Lab A1 Mini** using **Bambu Lab PLA Light Black** filament.

### Files included

| File | Description |
|------|-------------|
| [`3D/Final-Moon_Fusion.f3z`](3D/Final-Moon_Fusion.f3z) | Full Fusion 360 project |
| [`3D/Final-Moon.3mf`](3D/Final-Moon.3mf) | Bambu Studio project |
| [`3D/*.stl`](3D/) | Individual printable parts |

Assembly uses M3 screws and brass inserts. 

> **Note**  
> This was a one-time personal project, so the parts are not optimized for super-easy assembly. A bit of patience is needed to seat the display and route the cables cleanly. Once closed, the final result looks very nice.
