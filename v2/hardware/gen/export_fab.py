#!/usr/bin/env python3
"""Fabrication outputs: Gerbers + drill (zip), JLCPCB BOM / CPL, schematic PDF, STEP model."""
import csv, os, re, subprocess, sys, zipfile, shutil
import design as D
HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.join(HERE, "..")
FAB = os.path.join(HW, "fab")
PCB = os.path.join(HW, "moonmonitor.kicad_pcb")
G = os.path.join(FAB, "gerbers")
shutil.rmtree(G, ignore_errors=True); os.makedirs(G)
run = lambda *a: subprocess.run(a, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
run("kicad-cli", "pcb", "export", "gerbers", "-o", G + "/", "--layers",
    "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts", "--subtract-soldermask", PCB)
run("kicad-cli", "pcb", "export", "drill", "-o", G + "/", "--format", "excellon", "--excellon-separate-th", "--generate-map", "--map-format", "pdf", PCB)
with zipfile.ZipFile(os.path.join(FAB, "moonmonitor-gerbers.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(G)):
        if not f.endswith(".pdf") and not f.endswith(".gbrjob"):
            z.write(os.path.join(G, f), f)
run("kicad-cli", "sch", "export", "pdf", "-o", os.path.join(FAB, "schematic.pdf"), os.path.join(HW, "moonmonitor.kicad_sch"))
run("kicad-cli", "pcb", "export", "pos", "-o", os.path.join(FAB, "pos_raw.csv"), "--format", "csv", "--units", "mm", "--side", "front", PCB)

HAND = {"J2", "SW1", "H1", "H2", "TP1", "TP2", "JP1", "JP2", "JP3", "JP4"}     # not placed by the assembly house
# BOM (JLCPCB format), grouped by value+footprint
groups = {}
for ref, (lib, fp, value, u, v, rot, nets, lcsc, desc) in D.PARTS.items():
    if ref.startswith(("H", "TP", "JP")):
        continue
    groups.setdefault((value, fp, lcsc, desc), []).append(ref)
with open(os.path.join(FAB, "bom.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "Description", "Assembly"])
    for (value, fp, lcsc, desc), refs in sorted(groups.items(), key=lambda g: g[1][0]):
        w.writerow([value, ",".join(refs), fp, lcsc, desc, "hand-solder" if refs[0] in HAND else "SMT"])
# CPL (JLCPCB format)
rows = list(csv.DictReader(open(os.path.join(FAB, "pos_raw.csv"))))
with open(os.path.join(FAB, "cpl.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for r in rows:
        if r["Ref"] in HAND:
            continue
        w.writerow([r["Ref"], "%.3fmm" % float(r["PosX"]), "%.3fmm" % float(r["PosY"]), "Top", "%g" % float(r["Rot"])])
os.remove(os.path.join(FAB, "pos_raw.csv"))
try:
    subprocess.run(["kicad-cli", "pcb", "export", "step", "-o", os.path.join(FAB, "moonmonitor-pcb.step"), "--subst-models", "--force", PCB],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
except Exception as e:
    print("STEP export failed:", e)
shutil.rmtree(G)
print("\n".join(sorted(os.listdir(FAB))))
