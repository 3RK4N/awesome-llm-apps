#!/usr/bin/python3
"""Generate mosfet8.kicad_pcb (placement, routing, zones) from design.py.

Run with the system python that ships the KiCad 7 `pcbnew` module:
    /usr/bin/python3 gen_pcb.py
Board coordinates below are in mm, origin = top-left board corner.
"""
import json, os, sys
import pcbnew
from pcbnew import VECTOR2I, FromMM, F_Cu, B_Cu

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from design import PARTS, N

FPDIR = '/usr/share/kicad/footprints/'
OX, OY = 100.0, 50.0            # board origin on the KiCad page
W, H = 62.0, 72.0               # board size: 62 mm along the rail, 72 mm carrier width

board = pcbnew.BOARD()
UUIDS = json.load(open(os.path.join(HERE, 'sym_uuid.json')))

def P(x, y):
    return VECTOR2I(FromMM(OX + x), FromMM(OY + y))

# ------------------------------------------------------------------ rules
ds = board.GetDesignSettings()
ds.SetCopperLayerCount(2)
ds.m_MinClearance = FromMM(0.2)
ds.m_TrackMinWidth = FromMM(0.2)
ds.m_ViasMinSize = FromMM(0.5)
ds.m_MinThroughDrill = FromMM(0.3)
ds.m_CopperEdgeClearance = FromMM(0.3)
ds.m_HoleToHoleMin = FromMM(0.25)
ds.SetBoardThickness(FromMM(1.6))
nc = ds.m_NetSettings.m_DefaultNetClass
nc.SetClearance(FromMM(0.25))
nc.SetTrackWidth(FromMM(0.3))
nc.SetViaDiameter(FromMM(0.6))
nc.SetViaDrill(FromMM(0.3))

# ------------------------------------------------------------------ nets
NETS = {}
def net(name):
    if name not in NETS:
        # local labels on the root sheet get a '/' prefix in KiCad net names
        full = name if name in ('+24V', 'GND') else '/' + name
        ni = pcbnew.NETINFO_ITEM(board, full)
        board.Add(ni)
        NETS[name] = ni
    return NETS[name]

# ------------------------------------------------------------------ helpers
FPS = {}
def place(ref, x, y, rot=0):
    p = PARTS[ref]
    lib, name = p['fp'].split(':')
    fp = pcbnew.FootprintLoad(FPDIR + lib + '.pretty', name)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    fp.SetReference(ref)
    fp.SetValue(p['value'])
    fp.SetPosition(P(x, y))
    fp.SetOrientationDegrees(rot)
    fp.Reference().SetVisible(False)          # dense board: refs live on F.Fab
    fp.SetPath(pcbnew.KIID_PATH('/' + UUIDS['symbols'][ref]))
    for pad in fp.Pads():
        num = pad.GetNumber()
        if num in p['pins']:
            pad.SetNet(net(p['pins'][num]))
    board.Add(fp)
    FPS[ref] = fp
    return fp

def pad(ref, num, pick=None):
    """Pad centre in board mm. For multi-pad numbers pick=max area by default."""
    best = None
    for pd in FPS[ref].Pads():
        if pd.GetNumber() == str(num):
            a = pd.GetSize().x * pd.GetSize().y
            if best is None or a > best[0]:
                best = (a, pd)
    pos = best[1].GetPosition()
    return (pcbnew.ToMM(pos.x) - OX, pcbnew.ToMM(pos.y) - OY)

def track(netname, pts, w=0.3, layer=F_Cu):
    for a, b in zip(pts, pts[1:]):
        if abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6:
            continue
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(P(*a)); t.SetEnd(P(*b))
        t.SetWidth(FromMM(w)); t.SetLayer(layer); t.SetNet(net(netname))
        board.Add(t)

def via(netname, x, y, dia=0.6, drill=0.3):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(P(x, y))
    v.SetWidth(FromMM(dia)); v.SetDrill(FromMM(drill))
    v.SetLayerPair(F_Cu, B_Cu)
    v.SetNet(net(netname))
    board.Add(v)

def zone(netname, layer, pts, prio=0, clearance=0.3, minw=0.25):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net(netname))
    z.SetAssignedPriority(prio)
    z.SetLocalClearance(FromMM(clearance))
    z.SetMinThickness(FromMM(minw))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    o = z.Outline()
    o.NewOutline()
    for x, y in pts:
        o.Append(FromMM(OX + x), FromMM(OY + y))
    board.Add(z)
    return z

def text(s, x, y, size=1.0, layer=pcbnew.F_SilkS, rot=0, thick=0.15):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(P(x, y))
    t.SetLayer(layer)
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
    t.SetTextThickness(FromMM(thick))
    t.SetTextAngleDegrees(rot)
    if layer in (pcbnew.B_SilkS, pcbnew.B_Fab):
        t.SetMirrored(True)
    board.Add(t)

# ------------------------------------------------------------------ outline
e = pcbnew.PCB_SHAPE(board)
e.SetShape(pcbnew.SHAPE_T_RECT)
e.SetStart(P(0, 0)); e.SetEnd(P(W, H))
e.SetLayer(pcbnew.Edge_Cuts); e.SetWidth(FromMM(0.1))
board.Add(e)

# ------------------------------------------------------------------ geometry
PX0, PXP = 4.0, 3.5                 # input columns (IN1 at left)
XC0, XCP = 6.45, 7.3                # MOSFET columns
TX0, TXP = 14.2, 5.08               # output terminal pins
Y_J1, Y_J3, Y_J2 = 5.0, 5.8, 66.9
Y_R1, Y_R2, Y_BUS, Y_U, Y_LED = 10.95, 14.25, 15.25, 19.45, 25.25
Y_FAN0, Y_FAN1 = 26.95, 35.2
Y_R4, Y_ZD, Y_R3 = 37.0, 39.7, 41.7
Y_Q = 48.94                         # DPAK origin; pins at Y_Q-5.04, tab centre Y_Q+1.26
Y_F = 57.34                         # fuse / flyback diode centre
X_JP, X_PL, X_C1 = 35.4, 39.2, 47.6

px = lambda i: PX0 + PXP * i
xc = lambda i: XC0 + XCP * i
tx = lambda i: TX0 + TXP * i

# ------------------------------------------------------------------ connectors + power block
place('J1', px(8), Y_J1, 180)                  # pin1 (COM) right, pin9 (IN1) left
place('J3', 56.24, Y_J3, 180)                  # pins: 0V 0V | 24V 24V (right to left)
place('J2', tx(0), Y_J2, 0)
place('JP1', X_JP, Y_BUS - 2.54, 0)
place('R1', X_PL, 14.15, 270)                   # pad1 (+24V) up
place('D2', X_PL, 17.55, 90)                    # pad1 (K) down
place('C1', X_C1, 16.7, 0)                     # + left (over +24V strip), - right
place('D1', X_C1, 23.6, 0)                     # K left, A right

# J1 pin9..2 -> R1 handled per channel. COM: J1.1 and JP1.2 on the bottom bus
track('IN_COM', [pad('J1', 1), (px(8), Y_BUS), pad('JP1', 2)], 0.4, B_Cu)
track('IN_COM', [(px(0) - 0.73, Y_BUS), (px(8), Y_BUS)], 0.4, B_Cu)

# JP1.1 = +24V: top to R1, bottom into the +24V strip
jp1 = pad('JP1', 1)
track('+24V', [jp1, (X_PL, jp1[1]), pad('R1', 1)], 0.4)
track('+24V', [jp1, (40.0, jp1[1])], 0.5, B_Cu)
track('PWR_LED', [pad('R1', 2), pad('D2', 2)], 0.3)
d2k = pad('D2', 1)
track('GND', [d2k, (X_PL, d2k[1] + 0.9), (X_JP + 1.6, d2k[1] + 0.9), pad('JP1', 3)], 0.4)

# C1 / TVS
c1p, c1n = pad('C1', 1), pad('C1', 2)
for dy in (-0.8, 0.8):
    track('+24V', [c1p, (X_C1 - 6.0, c1p[1] + dy)], 0.8); via('+24V', X_C1 - 6.0, c1p[1] + dy, 0.8, 0.4)
    track('GND', [c1n, (X_C1 + 6.0, c1n[1] + dy)], 0.8); via('GND', X_C1 + 6.0, c1n[1] + dy, 0.8, 0.4)
tk, ta = pad('D1', 1), pad('D1', 2)
track('+24V', [tk, (X_C1 - 4.5, tk[1])], 0.8); via('+24V', X_C1 - 4.5, tk[1], 0.8, 0.4)
track('GND', [ta, (X_C1 + 4.5, ta[1])], 0.8); via('GND', X_C1 + 4.5, ta[1], 0.8, 0.4)

# ------------------------------------------------------------------ channels
for i in range(N):
    n = i + 1
    x, c = px(i), xc(i)
    xs, xg = c - 2.28, c + 2.28
    A, LK, GD, G, D, OUT = (f'{k}{n}' for k in ('A', 'LK', 'GD', 'G', 'D', 'OUT'))

    # ---- input stage (3.5 mm pitch columns)
    place(f'R{n}1', x, Y_R1, 270)              # pad1 (IN) up
    place(f'R{n}2', x, Y_R2, 0)                # pad1 (COM) left
    place(f'U{n}', x, Y_U, 270)                # pins 1,2 up / 3,4 down
    place(f'D{n}1', x + 0.64, Y_LED, 270)      # pad1 (K) up
    track(f'IN{n}', [pad('J1', 9 - i), pad(f'R{n}1', 1)], 0.5)
    r2a, u1 = pad(f'R{n}2', 2), pad(f'U{n}', 1)
    track(A, [pad(f'R{n}1', 2), (r2a[0], r2a[1] - 0.9), r2a, (r2a[0], u1[1] - 0.9), u1])
    r2c, u2 = pad(f'R{n}2', 1), pad(f'U{n}', 2)
    vx = x - 0.73
    track('IN_COM', [r2c, (vx, Y_BUS), u2])
    via('IN_COM', vx, Y_BUS)
    u3, u4 = pad(f'U{n}', 3), pad(f'U{n}', 4)
    track('GND', [u3, (u3[0], Y_LED - 0.9)]); via('GND', u3[0], Y_LED - 0.9)
    track(LK, [u4, pad(f'D{n}1', 1)])

    # ---- gate network
    place(f'R{n}4', xg, Y_R4, 270)             # pad1 (GD) up
    place(f'D{n}2', c, Y_ZD, 0)                # K left (+24V), A right (gate)
    place(f'R{n}3', c, Y_R3, 0)                # pad1 left (+24V)
    place(f'Q{n}', c, Y_Q, 270)                # G right-top, S left-top, tab down
    la = pad(f'D{n}1', 2)
    track(GD, [la, (la[0], Y_FAN0), (xg, Y_FAN1), pad(f'R{n}4', 1)])
    qg, qs = pad(f'Q{n}', 1), pad(f'Q{n}', 3)
    track(G, [pad(f'R{n}4', 2), qg])
    track(G, [pad(f'D{n}2', 2), (xg, Y_ZD)])
    track(G, [pad(f'R{n}3', 2), (xg, Y_R3)])
    # source bar with 4 vias into the bottom +24V bus
    xb = xs - 0.7
    vy = [38.5 + 1.4 * k for k in range(4)]
    for y in vy:
        via('+24V', xb, y, 0.9, 0.5)
    track('+24V', [(xb, y) for y in vy] + [qs], 1.6)
    track('+24V', [(xb, Y_ZD), pad(f'D{n}2', 1)], 0.6)
    track('+24V', [(xb, Y_R3), pad(f'R{n}3', 1)], 0.4)

    # ---- output: tab -> fuse -> terminal, flyback diode
    left = i < N // 2                           # left half: fuse right of column, diode left
    xf = c + 1.42 if left else c - 1.42
    xd = c - 2.21 if left else c + 2.21
    place(f'F{n}', xf, Y_F, 270)                # pad1 (drain side) up
    place(f'D{n}3', xd, Y_F, 90)                # K down, A up
    f1, f2 = pad(f'F{n}', 1), pad(f'F{n}', 2)
    tab = pad(f'Q{n}', 2)
    track(D, [(xf, tab[1] + 1.0), f1], 2.5)
    track(D, [tab, (xf, tab[1] + 1.0)], 2.5)
    for vx_ in ((c - 1.7, c, c + 1.7) if i < N - 1 else (c - 1.9, c - 0.8, c + 0.3)):           # thermal vias under the tab
        for vy_ in (tab[1] - 1.5, tab[1] + 1.3):
            via(D, vx_, vy_, 0.7, 0.35)
            track(D, [tab, (vx_, vy_)], 0.6)
    dk, da = pad(f'D{n}3', 1), pad(f'D{n}3', 2)
    track(OUT, [f2, dk], 1.5)
    t = (tx(i), Y_J2)
    dx = t[0] - xf
    y0 = f2[1] + 0.6
    track(OUT, [f2, (xf, y0), (t[0], y0 + abs(dx)), t], 2.0)
    for gx in (xd - 0.4, xd + 0.4):             # anode to bottom GND
        via('GND', gx, Y_F)
        track('GND', [da, (gx, Y_F)], 0.5)

    # bottom copper island under the tab (heat spreading)
    xr = c + 2.9 if i < N - 1 else c + 0.8
    zone(D, B_Cu, [(c - 2.9, 45.4), (xr, 45.4), (xr, 54.8), (c - 2.9, 54.8)], prio=2)

    # silk: channel number next to LED and at MOSFET
    text(str(n), x - 0.95, Y_LED + 0.3, 0.9)

# ------------------------------------------------------------------ zones
xs1, xs8 = xc(0) - 2.28, xc(N - 1) - 2.28
BL, BR = 2.6, xs8 + 1.15
zone('+24V', B_Cu, [(38.2, 1.0), (48.6, 1.0), (48.6, 34.1), (BR, 34.1), (BR, 44.5),
                    (BL, 44.5), (BL, 34.1), (38.2, 34.1)], prio=3)
full = [(0.5, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (0.5, H - 0.5)]
zone('GND', F_Cu, full, prio=0)
zone('GND', B_Cu, full, prio=0)

# ------------------------------------------------------------------ silkscreen
text('NPN', X_JP, 9.6, 0.9)
text('PNP', X_JP, 21.0, 0.9)
text('8xDO 24V PNP 5A', 52.0, 29.0, 0.9)
text('IN: NPN/PNP', 52.0, 27.4, 0.9)
bs = pcbnew.B_SilkS
for i in range(N):
    text(f'IN{i + 1}', px(i), 10.3, 0.9, bs, 90)
    text(f'OUT{i + 1}', tx(i), 61.0, 0.9, bs, 90)
text('COM', px(8), 10.3, 0.9, bs, 90)
text('+24V', 43.5, 13.0, 1.2, bs); text('0V', 53.7, 13.0, 1.2, bs)
text('JP1: 1-2 NPN / 2-3 PNP', 20.0, 30.0, 1.0, bs)
text('8CH MOSFET OUT 24V PNP 5A/CH  MAX 20A', 31.0, 48.0, 1.0, bs)
text('REV 1.0', 31.0, 50.0, 1.0, bs)

# ------------------------------------------------------------------ save, reload, fill
out = os.path.normpath(os.path.join(HERE, '..', 'mosfet8.kicad_pcb'))
pcbnew.SaveBoard(out, board)
board = pcbnew.LoadBoard(out)               # filling a freshly built BOARD() crashes KiCad 7
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(out, board)
print('saved', out, 'footprints', len(board.GetFootprints()), 'tracks', len(board.GetTracks()))
