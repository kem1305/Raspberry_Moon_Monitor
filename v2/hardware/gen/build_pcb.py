#!/usr/bin/python3
"""Generate the Moon Monitor v2 board (KiCad 7): placement, outline, routing, ground pours, DRC.

Run with the Python that ships KiCad's `pcbnew` module:   /usr/bin/python3 build_pcb.py
Output: ../moonmonitor.kicad_pcb  (+ DRC report in ../fab/drc.rpt)
"""
import faulthandler, heapq, math, os, sys
faulthandler.enable()
import numpy as np
import pcbnew
from pcbnew import FromMM, ToMM, VECTOR2I

import design as D

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "moonmonitor.kicad_pcb")
FPDIR = "/usr/share/kicad/footprints/"
CX, CY = 100.0, 100.0                       # board centre in KiCad coordinates


def P(u, v):
    return VECTOR2I(FromMM(CX + u), FromMM(CY - v))


# ------------------------------------------------------------------------------------------------
# board, rules, footprints
# ------------------------------------------------------------------------------------------------
board = pcbnew.BOARD()
ds = board.GetDesignSettings()
ds.m_MinClearance = FromMM(0.15)
ds.m_TrackMinWidth = FromMM(0.15)
ds.m_ViasMinSize = FromMM(0.5)
ds.m_ViasMinAnnularWidth = FromMM(0.1)
ds.m_MinThroughDrill = FromMM(0.3)
ds.m_CopperEdgeClearance = FromMM(0.3)
ds.m_HoleClearance = FromMM(0.2)
ds.m_HoleToHoleMin = FromMM(0.25)
ds.m_SilkClearance = FromMM(0.0)
nc = ds.m_NetSettings.m_DefaultNetClass
nc.SetClearance(FromMM(0.15))
nc.SetTrackWidth(FromMM(D.DEFAULT_WIDTH))
nc.SetViaDiameter(FromMM(0.6))
nc.SetViaDrill(FromMM(0.3))

nets = {}


def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n
    return nets[name]


fps = {}
for ref, (lib, name, value, u, v, rot, padnets, lcsc, desc) in D.PARTS.items():
    fp = pcbnew.FootprintLoad(FPDIR + lib + ".pretty", name)
    assert fp is not None, name
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    board.Add(fp)
    fp.SetPosition(P(u, v))
    fp.SetOrientationDegrees(rot)
    if ref == "J2":                            # radial-tolerance plated slots instead of round holes
        for pad in fp.Pads():
            pad.SetShape(pcbnew.PAD_SHAPE_OVAL)
            pad.SetSize(VECTOR2I(FromMM(D.J2_PAD[0]), FromMM(D.J2_PAD[1])))
            pad.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_OBLONG)
            pad.SetDrillSize(VECTOR2I(FromMM(D.J2_SLOT[0]), FromMM(D.J2_SLOT[1])))
        for g in list(fp.GraphicalItems()):
            if g.GetLayer() in (pcbnew.F_SilkS, pcbnew.F_CrtYd, pcbnew.F_Fab):
                fp.Remove(g)
    if ref == "U1":                            # thermal vias of the library footprint: 0.2 -> 0.3 mm drill
        for pad in fp.Pads():
            if pad.GetNumber() == "41" and pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                pad.SetDrillSize(VECTOR2I(FromMM(0.3), FromMM(0.3)))
    if ref.startswith(("H", "TP", "JP")):
        fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    for pad in fp.Pads():
        n = padnets.get(pad.GetNumber())
        if n:
            pad.SetNet(net(n))
    if lcsc:
        fp.SetProperty("LCSC", lcsc)
    fp.SetProperty("Description", desc)
    fps[ref] = fp

# reference designators: small, readable, next to the part
REF_POS = {"U1": (-3, 9), "J1": (-6.2, -16.6), "SW1": (5.6, 25.0), "U2": (-12.3, -8.4), "U3": (6.6, -8.9), "Q1": (16.2, 19.6),
           "F1": (-8.6, -17.2), "R1": (-2.6, -8.0), "R2": (6.2, -18.0), "R3": (-4.6, -6.4), "R4": (10.9, 17.6), "R5": (12.6, 23.4),
           "C1": (-12.3, -12.6), "C2": (-4.6, -10.6), "C3": (-12.6, -7.9), "C4": (-9.3, -3.75), "C5": (-8.0, -6.4), "C6": (10.9, 19.4),
           "C7": (17.6, 17.4), "J2": (23.5, 10.3)}
for ref, (u, v) in REF_POS.items():
    t = fps[ref].Reference()
    t.SetPosition(P(u, v))
    t.SetTextSize(VECTOR2I(FromMM(0.8), FromMM(0.8)))
    t.SetTextThickness(FromMM(0.13))
    t.SetTextAngleDegrees(0)
    t.SetLayer(pcbnew.F_SilkS)
    t.SetVisible(ref not in ("C4", "C3"))


def silk(text, u, v, size=0.9, layer=pcbnew.F_SilkS, bold=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(P(u, v))
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
    t.SetTextThickness(FromMM(size * (0.2 if bold else 0.15)))
    t.SetLayer(layer)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)


silk("VCC1", 18.6, 14.3, 0.8)
silk("GND2", 13.6, 14.8, 0.8)
silk("GND6", 14.2, -11.3, 0.8)
silk("VCC7", 18.6, -13.3, 0.8)
silk("P1", 20.3, 9.7, 0.8)
silk("P7", 20.3, -9.6, 0.8)
silk("3V3", 9.0, -21.3, 0.8)
silk("GND", 14.9, -20.5, 0.8)
silk("MOON MONITOR v2", 4.0, -19.0, 1.2, pcbnew.B_SilkS, True)
silk("display side", 4.0, -21.0, 0.9, pcbnew.B_SilkS)

# ------------------------------------------------------------------------------------------------
# outline
# ------------------------------------------------------------------------------------------------
R = D.BOARD_R
uL, vB = D.FLAT_LEFT_U, D.FLAT_BOTTOM_V
vL = math.sqrt(R * R - uL * uL)              # chord end points
uB = math.sqrt(R * R - vB * vB)


def edge_line(a, b):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(P(*a)); s.SetEnd(P(*b))
    s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(FromMM(0.1))
    board.Add(s)


def edge_arc(a0, a1):                        # angles in degrees, counter-clockwise from a0 to a1
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    pt = lambda a: P(R * math.cos(math.radians(a)), R * math.sin(math.radians(a)))
    # KiCad's Y axis points down: going CCW in (u, v) is clockwise on screen, so swap the ends
    s.SetArcGeometry(pt(a1), pt((a0 + a1) / 2), pt(a0))
    s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(FromMM(0.1))
    board.Add(s)


aB = math.degrees(math.atan2(vB, uB))                    # bottom chord, right end
aL1 = math.degrees(math.atan2(vL, uL))                   # left chord, top end
assert uL * uL + vB * vB < R * R                         # the two chords meet inside the circle
edge_line((uL, vB), (uB, vB))
edge_arc(aB, aL1)
edge_line((uL, vL), (uL, vB))


def inside_board(u, v, inset):
    return (u * u + v * v <= (R - inset) ** 2) and u >= uL + inset and v >= vB + inset


# ------------------------------------------------------------------------------------------------
# router (grid maze router, 2 layers, 45-degree moves)
# ------------------------------------------------------------------------------------------------
PITCH = 0.05
N = int(2 * 30 / PITCH)                      # 60 x 60 mm window centred on the board
VIA_D, VIA_DRILL = 0.6, 0.3
EDGE_CLR = 0.35


def gx(xmm): return int(round((xmm - (CX - 30)) / PITCH))
def gy(ymm): return int(round((ymm - (CY - 30)) / PITCH))
def mmx(i): return CX - 30 + i * PITCH
def mmy(j): return CY - 30 + j * PITCH


yy, xx = np.mgrid[0:N, 0:N]
UU = (xx * PITCH - 30.0)
VV = -(yy * PITCH - 30.0)

# obstacle items: (kind, layers(set of 0/1), net, geometry)
items = []


def add_rect(layers, netname, x0, y0, x1, y1): items.append(("r", layers, netname, (x0, y0, x1, y1)))
def add_circ(layers, netname, x, y, r): items.append(("c", layers, netname, (x, y, r)))
def add_seg(layers, netname, x0, y0, x1, y1, r): items.append(("s", layers, netname, (x0, y0, x1, y1, r)))


smd_pads = []                                # (x0,y0,x1,y1) of all SMD pads: no vias there
for fp in board.GetFootprints():
    for pad in fp.Pads():
        bb = pad.GetBoundingBox()
        x0, y0, x1, y1 = (ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom()))
        nname = pad.GetNetname() or None
        attr = pad.GetAttribute()
        pos = pad.GetPosition()
        if attr == pcbnew.PAD_ATTRIB_NPTH:
            d = max(ToMM(pad.GetDrillSize().x), ToMM(pad.GetDrillSize().y))
            add_circ({0, 1}, "#hole", ToMM(pos.x), ToMM(pos.y), d / 2 + 0.2)   # + extra: edge clearance > copper clearance
            continue
        if not pad.IsOnLayer(pcbnew.F_Cu) and not pad.IsOnLayer(pcbnew.B_Cu):
            continue                           # paste-only apertures
        layers = {0, 1} if attr == pcbnew.PAD_ATTRIB_PTH else ({0} if pad.IsOnLayer(pcbnew.F_Cu) else {1})
        if pad.GetShape() == pcbnew.PAD_SHAPE_CIRCLE:
            add_circ(layers, nname or "#nc", ToMM(pos.x), ToMM(pos.y), ToMM(pad.GetSize().x) / 2)
        else:
            add_rect(layers, nname or "#nc", x0, y0, x1, y1)
        if attr == pcbnew.PAD_ATTRIB_SMD:
            smd_pads.append((x0, y0, x1, y1))
    for z in fp.Zones():                       # footprint keep-outs (USB connector pegs, antenna)
        bb = z.GetBoundingBox()
        ls = set()
        if z.IsOnLayer(pcbnew.F_Cu): ls.add(0)
        if z.IsOnLayer(pcbnew.B_Cu): ls.add(1)
        add_rect(ls, "#keepout", ToMM(bb.GetLeft()), ToMM(bb.GetTop()), ToMM(bb.GetRight()), ToMM(bb.GetBottom()))


def stamp(mask, item, inflate):
    kind, _, _, g = item
    if kind == "r":
        x0, y0, x1, y1 = g
        i0, i1 = max(0, gx(x0 - inflate)), min(N - 1, gx(x1 + inflate))
        j0, j1 = max(0, gy(y0 - inflate)), min(N - 1, gy(y1 + inflate))
        if i0 <= i1 and j0 <= j1:
            mask[j0:j1 + 1, i0:i1 + 1] = True
    elif kind == "c":
        x, y, r = g
        rr = r + inflate
        i0, i1 = max(0, gx(x - rr)), min(N - 1, gx(x + rr))
        j0, j1 = max(0, gy(y - rr)), min(N - 1, gy(y + rr))
        sub = (mmx(xx[j0:j1 + 1, i0:i1 + 1]) - x) ** 2 + (mmy(yy[j0:j1 + 1, i0:i1 + 1]) - y) ** 2 <= rr * rr
        mask[j0:j1 + 1, i0:i1 + 1] |= sub
    else:
        x0, y0, x1, y1, r = g
        rr = r + inflate
        i0, i1 = max(0, gx(min(x0, x1) - rr)), min(N - 1, gx(max(x0, x1) + rr))
        j0, j1 = max(0, gy(min(y0, y1) - rr)), min(N - 1, gy(max(y0, y1) + rr))
        px = mmx(xx[j0:j1 + 1, i0:i1 + 1]); py = mmy(yy[j0:j1 + 1, i0:i1 + 1])
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        t = np.clip(((px - x0) * dx + (py - y0) * dy) / L2, 0, 1) if L2 > 0 else 0
        sub = (px - (x0 + t * dx)) ** 2 + (py - (y0 + t * dy)) ** 2 <= rr * rr
        mask[j0:j1 + 1, i0:i1 + 1] |= sub


_bm = {}


def board_mask(inset):
    key = round(inset, 3)
    if key not in _bm:
        _bm[key] = ~((UU * UU + VV * VV <= (R - inset) ** 2) & (UU >= uL + inset) & (VV >= vB + inset))
    return _bm[key]


def build_masks(netname, hw, clr):
    blocked = [board_mask(EDGE_CLR + hw).copy(), board_mask(EDGE_CLR + hw).copy()]
    via_bad = board_mask(EDGE_CLR + VIA_D / 2).copy()
    for it in items:
        if it[2] == netname:
            continue
        keepout = it[2] == "#keepout"          # rule area, not copper: no clearance needed
        for l in it[1]:
            stamp(blocked[l], it, hw if keepout else clr + hw + 0.005)
        stamp(via_bad, it, VIA_D / 2 if keepout else clr + VIA_D / 2 + 0.005)
    for (x0, y0, x1, y1) in smd_pads:          # no via-in-pad
        stamp(via_bad, ("r", None, None, (x0, y0, x1, y1)), VIA_D / 2 - 0.05)
    return blocked, via_bad


SQ2 = math.sqrt(2)
MOVES = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, SQ2), (1, -1, SQ2), (-1, 1, SQ2), (-1, -1, SQ2)]
VIA_COST = 3.0 / PITCH                         # a via "costs" 3 mm of track
B_COST = 1.15                                  # mild preference for the component side


def astar(sources, target, tlayers, blocked, via_bad):
    """sources: iterable of (i, j, layer); target (i, j); returns list of (i, j, layer)"""
    ti, tj = target
    def h(i, j):
        dx, dy = abs(i - ti), abs(j - tj)
        return (max(dx, dy) + (SQ2 - 1) * min(dx, dy))
    openq, best, came = [], {}, {}
    for s in sources:
        best[s] = 0.0
        heapq.heappush(openq, (h(s[0], s[1]), 0.0, s))
    while openq:
        f, g, cur = heapq.heappop(openq)
        if g > best.get(cur, 1e18):
            continue
        i, j, l = cur
        if i == ti and j == tj and l in tlayers:
            path = [cur]
            while cur in came:
                cur = came[cur]; path.append(cur)
            return path[::-1]
        bl = blocked[l]
        lc = B_COST if l == 1 else 1.0
        for di, dj, c in MOVES:
            ni, nj = i + di, j + dj
            if ni < 0 or nj < 0 or ni >= N or nj >= N or bl[nj, ni]:
                continue
            ng = g + c * lc
            key = (ni, nj, l)
            if ng < best.get(key, 1e18):
                best[key] = ng; came[key] = cur
                heapq.heappush(openq, (ng + h(ni, nj), ng, key))
        if not via_bad[j, i]:
            key = (i, j, 1 - l)
            ng = g + VIA_COST
            if not blocked[1 - l][j, i] and ng < best.get(key, 1e18):
                best[key] = ng; came[key] = cur
                heapq.heappush(openq, (ng + h(i, j), ng, key))
    return None


LAYER = [pcbnew.F_Cu, pcbnew.B_Cu]
stats = {"len": 0.0, "vias": 0}


def emit(path, netname, width):
    """turn a cell path into tracks/vias on the board and into obstacle items"""
    n = nets[netname]
    k = 0
    while k < len(path) - 1:
        i, j, l = path[k]
        ni, nj, nl = path[k + 1]
        if nl != l:
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(VECTOR2I(FromMM(mmx(i)), FromMM(mmy(j))))
            v.SetWidth(FromMM(VIA_D)); v.SetDrill(FromMM(VIA_DRILL)); v.SetNet(n)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            board.Add(v)
            add_circ({0, 1}, netname, mmx(i), mmy(j), VIA_D / 2)
            stats["vias"] += 1
            k += 1
            continue
        d = (ni - i, nj - j)
        m = k + 1
        while m + 1 < len(path) and path[m + 1][2] == l and (path[m + 1][0] - path[m][0], path[m + 1][1] - path[m][1]) == d:
            m += 1
        ei, ej, _ = path[m]
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(VECTOR2I(FromMM(mmx(i)), FromMM(mmy(j))))
        t.SetEnd(VECTOR2I(FromMM(mmx(ei)), FromMM(mmy(ej))))
        t.SetWidth(FromMM(width)); t.SetLayer(LAYER[l]); t.SetNet(n)
        board.Add(t)
        add_seg({l}, netname, mmx(i), mmy(j), mmx(ei), mmy(ej), width / 2)
        stats["len"] += math.hypot(ei - i, ej - j) * PITCH
        k = m


def pad_nodes(netname):
    out = []
    for fp in board.GetFootprints():
        seen = set()
        for pad in fp.Pads():
            if pad.GetNetname() != netname or not (pad.IsOnLayer(pcbnew.F_Cu) or pad.IsOnLayer(pcbnew.B_Cu)):
                continue
            key = (fp.GetReference(), pad.GetNumber())
            if key in seen and netname == "GND" and fp.GetReference() == "U1":
                continue                       # the many small apertures of the ESP32 ground pad
            seen.add(key)
            pos = pad.GetPosition()
            layers = (0, 1) if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else ((0,) if pad.IsOnLayer(pcbnew.F_Cu) else (1,))
            out.append((gx(ToMM(pos.x)), gy(ToMM(pos.y)), layers, key))
    return out


# ---- hand-made fan-out of the vertical USB-C connector (0.79 mm pitch, 0.15 mm tracks) -----------
# J1-local coordinates (KiCad: x right, y down).  A row is at y<0, B row at y>0.
J1X, J1Y = CX + D.PARTS["J1"][3], CY - D.PARTS["J1"][4]
FAN = 3.2
r1x = D.PARTS["R1"][3] + 0.825 - D.PARTS["J1"][3]; r1y = -(D.PARTS["R1"][4] - D.PARTS["J1"][4])     # R1 pad 2 (CC1)
r2x = D.PARTS["R2"][3] - 0.825 - D.PARTS["J1"][3]; r2y = -(D.PARTS["R2"][4] - D.PARTS["J1"][4])     # R2 pad 1 (CC2)
PREROUTES = [   # net, width, covered pads, polyline, port: None | "F" (router continues here) | "via"
    ("USB_DP", 0.15, [("J1", "A6"), ("J1", "B6")], [(-0.41, -0.76), (-0.41, -0.30), (0.38, 0.30), (0.38, 0.76)], None),
    ("USB_DP", 0.15, [], [(-0.41, -0.76), (-0.41, -1.42), (-0.60, -1.61), (-0.92, -1.61), (-0.92, -FAN)], "F"),
    ("USB_DN", 0.15, [("J1", "A7")], [(0.38, -0.76), (0.38, -1.42), (0.57, -1.61), (0.92, -1.61), (0.92, -FAN)], "F"),
    ("USB_DN", 0.15, [("J1", "B7")], [(-0.41, 0.76), (-0.41, 1.42), (-0.60, 1.61), (-0.92, 1.61), (-0.92, 4.3)], "via"),
    ("CC1", 0.15, [("J1", "A5"), ("R1", "2")], [(-1.26, -0.76), (-1.26, r1y + 0.55), (r1x, r1y)], None),
    ("CC2", 0.15, [("J1", "B5"), ("R2", "1")], [(1.26, 0.76), (1.26, r2y - 0.55), (r2x, r2y)], None),
    ("VBUS", 0.15, [("J1", "A4")], [(-1.99, -0.76), (-1.99, -1.35), (-1.62, -1.72), (-1.62, -2.9), (-1.77, -3.05), (-3.3, -3.05)], "F"),
    ("VBUS", 0.15, [("J1", "A9")], [(1.96, -0.76), (1.96, -1.35), (1.62, -1.69), (1.62, -2.9), (1.77, -3.05), (3.3, -3.05)], "F"),
    ("VBUS", 0.15, [("J1", "B4")], [(1.96, 0.76), (1.96, 1.35), (1.62, 1.69), (1.62, 2.9), (1.77, 3.05), (3.3, 3.05)], "F"),
    ("VBUS", 0.15, [("J1", "B9")], [(-1.99, 0.76), (-1.99, 1.35), (-1.62, 1.72), (-1.62, 2.9), (-1.77, 3.05), (-3.3, 3.05)], "F"),
    ("GND", 0.25, [("J1", "A1")], [(-2.78, -0.76), (-2.78, -1.3), (-2.5, -1.9)], None),
    ("GND", 0.25, [("J1", "A12")], [(2.75, -0.76), (2.75, -1.3), (2.5, -1.9)], None),
    ("GND", 0.25, [("J1", "B1")], [(2.75, 0.76), (2.75, 1.3), (2.5, 1.9)], None),
    ("GND", 0.25, [("J1", "B12")], [(-2.78, 0.76), (-2.78, 1.3), (-2.5, 1.9)], None),
]
pre_ports = {}          # net -> list of port nodes
pre_covered = set()     # (ref, pad)
for netname, w, covered, pts, port in PREROUTES:
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(VECTOR2I(FromMM(J1X + x0), FromMM(J1Y + y0)))
        t.SetEnd(VECTOR2I(FromMM(J1X + x1), FromMM(J1Y + y1)))
        t.SetWidth(FromMM(w)); t.SetLayer(pcbnew.F_Cu); t.SetNet(net(netname))
        board.Add(t)
        add_seg({0}, netname, J1X + x0, J1Y + y0, J1X + x1, J1Y + y1, w / 2)
    pre_covered.update(covered)
    ex, ey = J1X + pts[-1][0], J1Y + pts[-1][1]
    if port == "via":
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(VECTOR2I(FromMM(ex), FromMM(ey)))
        v.SetWidth(FromMM(VIA_D)); v.SetDrill(FromMM(VIA_DRILL)); v.SetNet(net(netname))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        board.Add(v)
        add_circ({0, 1}, netname, ex, ey, VIA_D / 2)
        stats["vias"] += 1
    if port:
        pre_ports.setdefault(netname, []).append((gx(ex), gy(ey), (0, 1) if port == "via" else (0,), ("J1", "fan")))

# U3's ground pin sits between the two USB data pins: give it its via before the data lines box it in
net("GND")
_u3 = D.PARTS["U3"]
_i, _j = gx(CX + _u3[3]), gy(CY - (_u3[4] - 1.1375))
emit([(_i, _j, 0), (_i, _j + int(round(1.35 / PITCH)), 0), (_i, _j + int(round(1.35 / PITCH)), 1)], "GND", 0.25)
pre_covered.add(("U3", "2"))

failed = []
for netname in D.ROUTE_ORDER:
    width = D.NET_WIDTH.get(netname, D.DEFAULT_WIDTH)
    pads = [p for p in pad_nodes(netname) if p[3] not in pre_covered] + pre_ports.get(netname, [])
    if len(pads) < 2:
        continue
    tree = [(pads[0][0], pads[0][1], l) for l in pads[0][2]]
    todo = pads[1:]
    while todo:
        # connect the pad closest to the existing tree next
        todo.sort(key=lambda p: min(abs(p[0] - s[0]) + abs(p[1] - s[1]) for s in tree))
        tgt = todo.pop(0)
        path = None
        for clr, w in ((0.2, width), (0.15, width), (0.15, min(width, 0.2)), (0.15, 0.15)):
            blocked, via_bad = build_masks(netname, w / 2, clr)
            path = astar(tree, (tgt[0], tgt[1]), set(tgt[2]), blocked, via_bad)
            if path:
                break
        if not path:
            failed.append((netname, tgt[3]))
            print("  FAILED", netname, tgt[3], flush=True)
            continue
        emit(path, netname, w)
        tree += path
        tree += [(tgt[0], tgt[1], l) for l in tgt[2]]
    print("routed %-8s %d nodes" % (netname, len(pads)), flush=True)

# ---- ground: stitch every SMD ground pad to the back-side pour with its own via -----------------
gnd_pads = [p for p in pad_nodes("GND") if p[2] == (0,) and p[3] not in pre_covered]


def stub_to_via(i0, j0, blocked, via_bad, limit=40000):
    """shortest front-side path from a pad to a spot where a via fits"""
    openq = [(0.0, (i0, j0))]
    best = {(i0, j0): 0.0}
    came = {}
    while openq and len(best) < limit:
        g, cur = heapq.heappop(openq)
        if g > best[cur]:
            continue
        i, j = cur
        if not via_bad[j, i] and not blocked[1][j, i] and g * PITCH >= 0.6:
            path = [(i, j, 1), (i, j, 0)]
            while cur in came:
                cur = came[cur]; path.append((cur[0], cur[1], 0))
            return path[::-1]
        for di, dj, c in MOVES:
            ni, nj = i + di, j + dj
            if 0 <= ni < N and 0 <= nj < N and not blocked[0][nj, ni] and g + c < best.get((ni, nj), 1e18):
                best[(ni, nj)] = g + c; came[(ni, nj)] = cur
                heapq.heappush(openq, (g + c, (ni, nj)))
    return None


blocked, via_bad = build_masks("GND", 0.125, 0.2)
for (i, j, layers, key) in gnd_pads:
    path = stub_to_via(i, j, blocked, via_bad)
    if not path:                                # boxed in: route it like a signal to the USB shell pin
        tgt = [p for p in pad_nodes("GND") if p[3] == ("J1", "S1")][0]
        b2, v2 = build_masks("GND", 0.1, 0.15)
        path = astar([(i, j, 0)], (tgt[0], tgt[1]), {0, 1}, b2, v2)
        if not path:
            print("  no ground connection for", key, flush=True); continue
        emit(path, "GND", 0.2)
        continue
    emit(path, "GND", 0.25)
    it = items[-1]                              # keep later vias away from this one (hole-to-hole)
    stamp(via_bad, it, 0.3)

# a few extra stitching vias tying the two pours together
for (u, v) in [(21, 17), (25, -11), (-12, -21), (8, -22), (-11, 25.2), (1, -3.6), (20, 0.0), (9, 11), (9, -4)]:
    i, j = gx(CX + u), gy(CY - v)
    if not via_bad[j, i] and not blocked[0][j, i] and not blocked[1][j, i]:
        emit([(i, j, 0), (i, j, 1)], "GND", 0.3)

# ---- ground pours on both layers -----------------------------------------------------------------
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(nets["GND"])
    z.SetIsFilled(False)
    z.SetLocalClearance(FromMM(0.25))
    z.SetMinThickness(FromMM(0.2))
    z.SetThermalReliefGap(FromMM(0.25))
    z.SetThermalReliefSpokeWidth(FromMM(0.4))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    ol = z.Outline()
    ol.NewOutline()
    for (u, v) in ((-30, -30), (30, -30), (30, 30), (-30, 30)):
        ol.Append(FromMM(CX + u), FromMM(CY - v))
    board.Add(z)

board.GetTitleBlock().SetTitle("Moon Monitor v2")
board.GetTitleBlock().SetRevision("2.0")
board.GetTitleBlock().SetComment(0, "Generated by hardware/gen/build_pcb.py")
pcbnew.SaveBoard(OUT, board)

os.makedirs(os.path.join(HERE, "..", "fab"), exist_ok=True)
rpt = os.path.join(HERE, "..", "fab", "drc.rpt")
board = pcbnew.LoadBoard(OUT)                    # (filling zones needs a board loaded from disk)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(OUT, board)
pcbnew.WriteDRCReport(board, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
print("tracks: %.0f mm, vias: %d, unrouted: %d" % (stats["len"], stats["vias"], len(failed)))
print(open(rpt).read()[-1500:])
sys.exit(1 if failed else 0)
