#!/usr/bin/env python3
"""Generate the schematic (KiCad 7) from design.py: one symbol per part, every pin tied to a global label.

The board is produced from the very same net list (build_pcb.py), so schematic and PCB cannot diverge.
"""
import os, re, uuid
import design as D

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "moonmonitor.kicad_sch")
SYMDIR = "/usr/share/kicad/symbols/"

SYMBOL = {   # ref prefix / ref -> (library, symbol)
    "U1": ("RF_Module", "ESP32-S3-WROOM-1"), "U2": ("Regulator_Linear", "AP2112K-3.3"),
    "U3": ("Power_Protection", "USBLC6-2SC6"), "Q1": ("Transistor_FET", "AO3401A"),
    "J1": ("Connector", "USB_C_Receptacle_USB2.0_16P"), "J2": ("Connector_Generic", "Conn_01x07"),
    "SW1": ("Switch", "SW_Push"), "F1": ("Device", "Polyfuse"), "R": ("Device", "R"), "C": ("Device", "C"),
    "JP": ("Jumper", "SolderJumper_2_Open"), "TP": ("Connector", "TestPoint"), "H": ("Mechanical", "MountingHole"),
}
# sheet position (mm) of every part, grouped by function
POS = {
    "J1": (45, 70), "F1": (85, 40), "U3": (95, 95), "R1": (75, 120), "R2": (90, 120),
    "U2": (130, 45), "C1": (112, 60), "C2": (150, 60), "TP1": (165, 40), "TP2": (165, 60),
    "U1": (225, 95), "C3": (180, 60), "C4": (192, 60), "R3": (180, 95), "C5": (180, 120),
    "SW1": (190, 150), "R4": (175, 150), "C6": (205, 160),
    "Q1": (300, 45), "R5": (285, 60), "C7": (320, 60),
    "J2": (340, 105), "JP1": (310, 90), "JP3": (310, 100), "JP4": (310, 120), "JP2": (310, 130),
    "H1": (300, 160), "H2": (315, 160),
}
TITLES = [(30, 25, "USB-C power input, ESD protection"), (110, 25, "3.3 V regulator"), (175, 25, "ESP32-S3 module, reset, button"),
          (280, 25, "Display power switch"), (290, 78, "Display header J2 - close JP1+JP3 or JP4+JP2 (see README)")]


# ---- minimal s-expression reader/writer -------------------------------------------------------
def parse(text):
    tok = re.findall(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+', text)
    pos = 0
    def rd():
        nonlocal pos
        t = tok[pos]; pos += 1
        if t == "(":
            lst = []
            while tok[pos] != ")":
                lst.append(rd())
            pos += 1
            return lst
        return t
    return rd()


def dump(x, ind=0):
    if isinstance(x, str):
        return x
    inner = " ".join(dump(i, ind + 1) for i in x)
    if len(inner) < 100:
        return "(" + inner + ")"
    return "(" + dump(x[0]) + "".join("\n" + "  " * (ind + 1) + dump(i, ind + 1) for i in x[1:]) + "\n" + "  " * ind + ")"


_libs = {}
def lib(name):
    if name not in _libs:
        _libs[name] = parse(open(SYMDIR + name + ".kicad_sym").read())
    return _libs[name]


def find_symbol(libname, sym):
    for e in lib(libname)[1:]:
        if isinstance(e, list) and e[0] == "symbol" and e[1] == '"%s"' % sym:
            return e
    raise KeyError(sym)


def flatten(libname, sym):
    """library symbol with 'extends' resolved, renamed to "Lib:Name" for embedding"""
    e = find_symbol(libname, sym)
    ext = [c for c in e if isinstance(c, list) and c[0] == "extends"]
    if ext:
        base = flatten(libname, ext[0][1].strip('"'))
        bname = ext[0][1].strip('"')
        out = ["symbol", '"%s:%s"' % (libname, sym)]
        props = {c[1]: c for c in e if isinstance(c, list) and c[0] == "property"}
        for c in base[2:]:
            if isinstance(c, list) and c[0] == "property":
                out.append(props.pop(c[1], c))
            elif isinstance(c, list) and c[0] == "symbol":
                out.append(["symbol", c[1].replace(bname + "_", sym + "_", 1)] + c[2:])
            else:
                out.append(c)
        return out
    return ["symbol", '"%s:%s"' % (libname, sym)] + [c for c in e[2:]]


def pins_of(symdef):
    pins = []
    for c in symdef:
        if isinstance(c, list) and c[0] == "symbol":
            for p in c:
                if isinstance(p, list) and p[0] == "pin":
                    at = [q for q in p if isinstance(q, list) and q[0] == "at"][0]
                    num = [q for q in p if isinstance(q, list) and q[0] == "number"][0][1].strip('"')
                    pins.append((num, float(at[1]), float(at[2]), int(float(at[3])) if len(at) > 3 else 0))
    return pins


def uid():
    return str(uuid.uuid4())


root = uid()
libsyms, body = {}, []
for ref, (flib, fname, value, u, v, rot, padnets, lcsc, desc) in D.PARTS.items():
    key = ref if ref in SYMBOL else re.match(r"[A-Z]+", ref).group(0)
    slib, sname = SYMBOL[key]
    lid = "%s:%s" % (slib, sname)
    if lid not in libsyms:
        libsyms[lid] = flatten(slib, sname)
    x, y = POS[ref]
    pins = pins_of(libsyms[lid])
    s = ["symbol", ["lib_id", '"%s"' % lid], ["at", str(x), str(y), "0"], ["unit", "1"], ["in_bom", "no" if key == "H" else "yes"],
         ["on_board", "yes"], ["dnp", "no"], ["uuid", uid()],
         ["property", '"Reference"', '"%s"' % ref, ["at", str(x), str(y - 2.54 if key in ("R", "C") else y - 8), "0"],
          ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", "left"]]],
         ["property", '"Value"', '"%s"' % value, ["at", str(x), str(y + 2.54 if key in ("R", "C") else y - 6), "0"],
          ["effects", ["font", ["size", "1.27", "1.27"]], ["justify", "left"]]],
         ["property", '"Footprint"', '"%s:%s"' % (flib, fname), ["at", str(x), str(y), "0"],
          ["effects", ["font", ["size", "1.27", "1.27"]], "hide"]],
         ["property", '"LCSC"', '"%s"' % lcsc, ["at", str(x), str(y), "0"], ["effects", ["font", ["size", "1.27", "1.27"]], "hide"]],
         ["property", '"Description"', '"%s"' % desc, ["at", str(x), str(y), "0"], ["effects", ["font", ["size", "1.27", "1.27"]], "hide"]]]
    # big symbols: put reference/value above the body
    ys = [py for (_, _, py, _) in pins] or [0]
    if key not in ("R", "C"):
        top = y - max(ys) - 6
        s[8][3] = ["at", str(x - 5), str(round(top, 2)), "0"]
        s[9][3] = ["at", str(x - 5), str(round(top + 2.2, 2)), "0"]
    seen = set()
    for num, px, py, ang in pins:
        if num in seen:
            continue
        seen.add(num)
        s.append(["pin", '"%s"' % num, ["uuid", uid()]])
        X, Y = round(x + px, 2), round(y - py, 2)
        netname = padnets.get(num)
        if netname is None and ref == "J1" and num in ("A8", "B8"):
            netname = None
        if netname:
            lang = {0: 180, 180: 0, 90: 270, 270: 90}[ang]
            just = "right" if lang in (180, 270) else "left"
            body.append(["global_label", '"%s"' % netname, ["shape", "passive"], ["at", str(X), str(Y), str(lang)],
                         ["fields_autoplaced"], ["effects", ["font", ["size", "1.1", "1.1"]], ["justify", just]], ["uuid", uid()],
                         ["property", '"Intersheetrefs"', '"${INTERSHEET_REFS}"', ["at", "0", "0", "0"],
                          ["effects", ["font", ["size", "1.27", "1.27"]], "hide"]]])
        else:
            body.append(["no_connect", ["at", str(X), str(Y)], ["uuid", uid()]])
    s.append(["instances", ["project", '"moonmonitor"', ["path", '"/%s"' % root, ["reference", '"%s"' % ref], ["unit", "1"]]]])
    body.append(s)

for (x, y, t) in TITLES:
    body.append(["text", '"%s"' % t, ["at", str(x), str(y), "0"], ["effects", ["font", ["size", "2", "2"], "bold"], ["justify", "left", "bottom"]], ["uuid", uid()]])

sch = ["kicad_sch", ["version", "20230121"], ["generator", "moonmonitor_gen"], ["uuid", root], ["paper", '"A3"'],
       ["title_block", ["title", '"Moon Monitor v2"'], ["rev", '"2.0"'], ["comment", "1", '"Generated from hardware/gen/design.py"']],
       ["lib_symbols"] + list(libsyms.values())] + body + [["sheet_instances", ["path", '"/"', ["page", '"1"']]]]
open(OUT, "w").write(dump(sch) + "\n")
print("wrote", OUT, "symbols:", len(D.PARTS))
