#!/usr/bin/env python3
"""Render firmware screens on the PC.  python3 sim.py OUT.png "2026-11-19 21:30" LAT LON TZ moon|info"""
import os, subprocess, sys, tempfile, glob
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
from PIL import Image, ImageDraw
here = os.path.dirname(os.path.abspath(__file__))
exe = os.path.join(here, "sim")
cache = os.path.join(tempfile.gettempdir(), "moon565")

def prepare():
    subprocess.check_call(["g++", "-O2", "-std=c++11", "-Wall", "-o", exe, os.path.join(here, "sim.cpp")])
    os.makedirs(cache, exist_ok=True)
    for j in sorted(glob.glob(os.path.join(here, "..", "data", "m", "*.jpg"))):
        o = os.path.join(cache, os.path.basename(j)[:-4] + ".565")
        if not os.path.exists(o):
            a = np.asarray(Image.open(j).convert("RGB")).astype(np.uint16)
            ((a[..., 0] >> 3 << 11) | (a[..., 1] >> 2 << 5) | (a[..., 2] >> 3)).astype("<u2").tofile(o)

def render(out, when, lat, lon, tz, mode):
    t = datetime.strptime(when, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(tz)).timestamp()
    raw = out + ".rgb"
    env = dict(os.environ, TZ=tz)
    info = subprocess.run([exe, cache, raw, str(t), str(lat), str(lon), mode], env=env, capture_output=True, text=True, check=True).stdout
    im = Image.frombytes("RGB", (240, 240), open(raw, "rb").read()); os.remove(raw)
    mask = Image.new("L", (960, 960), 0); ImageDraw.Draw(mask).ellipse((0, 0, 959, 959), fill=255)
    im.putalpha(mask.resize((240, 240), Image.LANCZOS))            # round display
    im.save(out)
    return info.strip()

if __name__ == "__main__":
    prepare()
    print(render(sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5], sys.argv[6]))
