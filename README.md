  This is my first project here. 
  It is a real-time realistic Moon phase display, with some additional Moon info accessible by pressing a button.
  This is also the first time I have done something with a Raspberry Pi, or with Python for that matter (I guess 
this 50-year-old nerd still has some potential, especially with a little help from AI).Initially 
  I wanted to make a small aviation radar that I saw on my feed, and I succeeded, but it wasn’t that satisfying. 
  So I came up with the idea to make a realistic Moon tracker, since my wife and I are avid night-sky observers. 
  This is how this project came to be.  
  Now the Moon Monitor sits on my wife’s nightstand, and I’m very proud of how it turned out.

The components are:
- 1x Raspberry Pi Zero 2W with a 32Gb SD Card (can be smaller for this one),
- 1x TFT 1,28" Round Display GC9A01,
- Push button 6x6x11 4 pins (could be 2 pins)
- jumper cables for connections.
- Mini-USB power source (I used an older charger with an old cable that I had)

Connections between components:
Display GC9A01	Raspberry /	GPIO	Obs.
RST	            13 /	GPIO27	    Display reset
CS	            24 /	GPIO8	      SPI0 CE0 (chip select)
DC	            15 /	GPIO22	    Data/Command
SDA	            19	/ GPIO10	    SPI0 MOSI
SCL	            23 /	GPIO11    	SPI0 SCLK
GND	            25 /	GND       	Ground
VCC	            17 /	3.3V      	Display power source
			
Botão push	    Raspberry /	GPIO	Obs.
Side 1	        11	/ GPIO17	    Digital input
Side 2	        9	/ GND	          Ground (use internal pull_up)

   The Python code running is main.py and it uses various different libraries:
import sys
import math
import time
import signal
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageEnhance   # for all the image handling, effects and transformations
import ephem    # for all the astronomical calculations
import RPi.GPIO as GPIO
import GC9A01   # Display driver for GC9A01

  Besides the electronics, I created the case in Fusion 360 (Final-Moon_Fusion360.f3z) and printed it on a 
Bambu Lab A1 Mini (Final-Moon.3mf) with Bambu Lab PLA Light Black filament.
  The assembly was done with 3 M3 screws and brass inserts.
  There are also the individual 3D component .stl files included.
  Since this was a one-time project for me, I did not perfect the 3D parts for easy assembly. 
  It wasn’t all that hard, but it required some patience to secure the display in place and to properly close 
the lid with all the cables tucked in and the Raspberry Pi firmly seated.
  But once it was all done, the final product looks very nice.
