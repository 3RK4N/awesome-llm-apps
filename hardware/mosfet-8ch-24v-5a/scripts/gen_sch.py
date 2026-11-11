#!/usr/bin/env python3
"""Generate mosfet8.kicad_sch from design.py (KiCad 7 format)."""
import uuid, sys, os
from sexpr import parse, dump, find, Sym
from design import PARTS, N

SYMDIR = '/usr/share/kicad/symbols/'
PROJECT = 'mosfet8'
ROOT_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, 'mosfet8-root'))
_cnt = [0]
def uid():
    _cnt[0] += 1
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f'mosfet8-{_cnt[0]}'))

S = Sym
libcache, libsyms = {}, {}
def libsym(lib_id):
    if lib_id in libsyms:
        return libsyms[lib_id]
    lib, name = lib_id.split(':')
    if lib not in libcache:
        libcache[lib] = parse(open(f'{SYMDIR}{lib}.kicad_sym').read())
    for s in find(libcache[lib], 'symbol'):
        if s[1] == name:
            assert not find(s, 'extends')
            node = list(s)
            node[1] = lib_id
            libsyms[lib_id] = node
            return node
    raise KeyError(lib_id)

def r(v):
    return round(v + 0.0, 4)

def xform(x, y, rot, mirror):
    """lib coords (y up) -> schematic offset (y down)."""
    y = -y
    if mirror == 'x':
        y = -y
    elif mirror == 'y':
        x = -x
    if rot == 90:
        x, y = y, -x
    elif rot == 180:
        x, y = -x, -y
    elif rot == 270:
        x, y = -y, x
    return x, y

items = []
SYM_UUID = {}
pwr_n = [0]

def fx(font=1.27, just=None, hide=False):
    e = [S('effects'), [S('font'), [S('size'), font, font]]]
    if just:
        e.append([S('justify')] + [S(j) for j in just.split()])
    if hide:
        e.append(S('hide'))
    return e

def place(lib_id, ref, x, y, rot=0, mirror=None, value=None, fp='', refpos=None, valpos=None, extra=None):
    ls = libsym(lib_id)
    pins = {}
    for u in find(ls, 'symbol'):
        for p in find(u, 'pin'):
            at = find(p, 'at')[0]
            num = find(p, 'number')[0][1]
            dx, dy = xform(float(at[1]), float(at[2]), rot, mirror)
            pins[num] = (r(x + dx), r(y + dy))
    node = [S('symbol'), [S('lib_id'), lib_id], [S('at'), r(x), r(y), rot]]
    if mirror:
        node.append([S('mirror'), S(mirror)])
    node += [[S('unit'), 1], [S('in_bom'), S('yes')], [S('on_board'), S('yes')], [S('dnp'), S('no')],
             [S('uuid'), uid()]]
    SYM_UUID[ref] = node[-1][1]
    power = lib_id.startswith('power:')
    rp = refpos or (x + 2.54, y - 1.27, 'left')
    vp = valpos or (x + 2.54, y + 1.27, 'left')
    pang = 90 if rot in (90, 270) else 0      # keeps text horizontal on rotated symbols
    def jj(pos):
        j = pos[2] if len(pos) > 2 else None
        if j and rot == 180:
            j = {'left': 'right', 'right': 'left'}[j]
        return j
    node.append([S('property'), 'Reference', ref, [S('at'), r(rp[0]), r(rp[1]), pang], fx(1.0, jj(rp), hide=power)])
    node.append([S('property'), 'Value', value or '', [S('at'), r(vp[0]), r(vp[1]), pang], fx(1.0, jj(vp))])
    node.append([S('property'), 'Footprint', fp, [S('at'), r(x), r(y), 0], fx(hide=True)])
    node.append([S('property'), 'Datasheet', '~', [S('at'), r(x), r(y), 0], fx(hide=True)])
    for k, v in (extra or {}).items():
        node.append([S('property'), k, v, [S('at'), r(x), r(y), 0], fx(hide=True)])
    for num in pins:
        node.append([S('pin'), num, [S('uuid'), uid()]])
    node.append([S('instances'), [S('project'), PROJECT, [S('path'), '/' + ROOT_UUID, [S('reference'), ref], [S('unit'), 1]]]])
    items.append(node)
    return pins

def part(ref, x, y, rot=0, mirror=None, **kw):
    p = PARTS[ref]
    return place(p['sym'], ref, x, y, rot, mirror, value=p['value'], fp=p['fp'],
                 extra={'MPN': p['mpn'], 'Description': p['desc']}, **kw)

junctions = []
segments = []

def wire(*pts):
    for a, b in zip(pts, pts[1:]):
        segments.append(((r(a[0]), r(a[1])), (r(b[0]), r(b[1]))))

def flush_wires():
    """Emit wires, split at junctions (KiCad only connects at wire ends)."""
    for a, b in segments:
        cuts = [a, b]
        for j in junctions:
            if j in (a, b):
                continue
            if a[0] == b[0] == j[0] and min(a[1], b[1]) < j[1] < max(a[1], b[1]):
                cuts.append(j)
            if a[1] == b[1] == j[1] and min(a[0], b[0]) < j[0] < max(a[0], b[0]):
                cuts.append(j)
        cuts.sort()
        for c, d in zip(cuts, cuts[1:]):
            _wire(c, d)

def _wire(*pts):
    for a, b in zip(pts, pts[1:]):
        items.append([S('wire'), [S('pts'), [S('xy'), r(a[0]), r(a[1])], [S('xy'), r(b[0]), r(b[1])]],
                      [S('stroke'), [S('width'), 0], [S('type'), S('default')]], [S('uuid'), uid()]])

def junction(x, y):
    junctions.append((r(x), r(y)))
    items.append([S('junction'), [S('at'), r(x), r(y)], [S('diameter'), 0], [S('color'), 0, 0, 0, 0], [S('uuid'), uid()]])

def label(name, x, y, rot=0, just='left bottom'):
    items.append([S('label'), name, [S('at'), r(x), r(y), rot], fx(1.0, just), [S('uuid'), uid()]])

def text(t, x, y, size=1.5):
    items.append([S('text'), t, [S('at'), r(x), r(y), 0], fx(size, 'left bottom'), [S('uuid'), uid()]])

def pwr(kind, x, y):
    pwr_n[0] += 1
    if kind == '+24V':
        place('power:+24V', f'#PWR{pwr_n[0]:03d}', x, y, value='+24V', valpos=(x, y - 3.56))
    else:
        place('power:GND', f'#PWR{pwr_n[0]:03d}', x, y, value='GND', valpos=(x, y + 3.81))

# ---------------------------------------------------------------- channels
PITCH = 29.21
Y_FIRST = 38.1
for n in range(1, N + 1):
    y0 = Y_FIRST + (n - 1) * PITCH
    ya, yc = y0 - 2.54, y0 + 5.08          # A line / COM line
    # input label -> R1
    p = part(f'R{n}1', 92.71, ya, 90, refpos=(92.71, ya - 2.54), valpos=(92.71, ya + 2.8))
    label(f'IN{n}', 81.28, ya)
    wire((81.28, ya), p['1'])
    # opto
    u = part(f'U{n}', 120.65, y0, refpos=(120.65, y0 - 6.6), valpos=(120.65, y0 + 6.9))
    wire(p['2'], u['1'])
    label(f'A{n}', 97.79, ya)
    # R2 across LED
    r2 = part(f'R{n}2', 104.14, y0 + 1.27, 180, refpos=(105.9, y0 + 0.3, 'left'), valpos=(105.9, y0 + 2.3, 'left'))
    junction(*r2['2'])
    wire((97.79, yc), r2['1'], (110.49, yc), (110.49, u['2'][1]), u['2'])
    label('IN_COM', 97.79, yc, 0, 'right bottom')
    # emitter -> GND
    wire(u['3'], (130.81, u['3'][1]), (130.81, y0 + 7.62))
    pwr('GND', 130.81, y0 + 7.62)
    # LED, R4
    d1 = part(f'D{n}1', 138.43, ya, refpos=(138.43, ya - 3.3), valpos=(138.43, ya + 3.3))
    wire(u['4'], d1['1'])
    label(f'LK{n}', 129.54, ya)
    r4 = part(f'R{n}4', 153.67, ya, 90, refpos=(153.67, ya - 2.54), valpos=(153.67, ya + 2.8))
    wire(d1['2'], r4['1'])
    label(f'GD{n}', 143.51, ya)
    # MOSFET (mirrored: source up)
    q = part(f'Q{n}', 187.96, ya, mirror='x', refpos=(193.04, ya - 1.27, 'left'), valpos=(193.04, ya + 1.27, 'left'))
    wire(r4['2'], q['1'])
    label(f'G{n}', 176.53, ya)
    yr = y0 - 10.16                         # +24V rail of the cell
    r3 = part(f'R{n}3', 165.1, y0 - 6.35, refpos=(163.3, y0 - 7.3, 'right'), valpos=(163.3, y0 - 5.3, 'right'))
    z = part(f'D{n}2', 172.72, y0 - 6.35, 270, refpos=(174.6, y0 - 7.3, 'left'), valpos=(174.6, y0 - 5.3, 'left'))
    junction(*r3['2']); junction(*z['2'])
    wire(r3['1'], (q['3'][0], yr)); junction(*z['1'])
    wire(q['3'], (q['3'][0], yr)); junction(q['3'][0], yr)
    pwr('+24V', q['3'][0], yr)
    # drain -> fuse -> out
    yo = y0 + 5.08
    f = part(f'F{n}', 205.74, yo, 90, refpos=(205.74, yo - 2.54), valpos=(205.74, yo + 2.8))
    wire(q['2'], (q['2'][0], yo), f['1'])
    label(f'D{n}', 194.31, yo)
    wire(f['2'], (233.68, yo))
    label(f'OUT{n}', 226.06, yo)
    d3 = part(f'D{n}3', 219.71, yo + 3.81, 270, refpos=(221.6, yo + 2.9, 'left'), valpos=(221.6, yo + 4.9, 'left'))
    junction(*d3['1'])
    pwr('GND', *d3['2'])

# ---------------------------------------------------------------- connectors
j1 = part('J1', 38.1, 53.34, mirror='y', refpos=(38.1, 40.6), valpos=(38.1, 67.3))
for i in range(1, 10):
    x, y = j1[str(i)]
    wire((x, y), (x + 7.62, y))
    label(PARTS['J1']['pins'][str(i)], x + 2.54, y)

jp = part('JP1', 38.1, 91.44, mirror='y', refpos=(38.1, 86.4), valpos=(38.1, 97.8))
wire(jp['1'], (50.8, jp['1'][1])); pwr('+24V', 50.8, jp['1'][1])
wire(jp['2'], (60.96, jp['2'][1])); label('IN_COM', 53.34, jp['2'][1])
wire(jp['3'], (50.8, jp['3'][1]), (50.8, jp['3'][1] + 2.54)); pwr('GND', 50.8, jp['3'][1] + 2.54)

j3 = part('J3', 38.1, 127.0, mirror='y', refpos=(38.1, 120.7), valpos=(38.1, 135.9))
wire(j3['1'], (50.8, j3['1'][1]), (50.8, j3['1'][1] - 2.54)); wire(j3['2'], (45.72, j3['2'][1]), (45.72, j3['1'][1])); junction(45.72, j3['1'][1])
wire(j3['3'], (45.72, j3['3'][1]), (45.72, j3['4'][1])); wire(j3['4'], (55.88, j3['4'][1]))
junction(45.72, j3['4'][1])
pwr('+24V', 55.88, j3['4'][1])
# 0V of J3: pins 1,2 -> GND symbol drawn to the right
wire((50.8, j3['1'][1] - 2.54), (60.96, j3['1'][1] - 2.54), (60.96, j3['1'][1]))
pwr('GND', 60.96, j3['1'][1])

c1 = part('C1', 33.02, 165.1)
pwr('+24V', *c1['1']); pwr('GND', *c1['2'])
tv = part('D1', 50.8, 165.1, 270, refpos=(52.7, 164.1, 'left'), valpos=(52.7, 166.1, 'left'))
pwr('+24V', *tv['1']); pwr('GND', *tv['2'])
r1 = part('R1', 33.02, 195.58)
d2 = part('D2', 33.02, 208.28, 90, refpos=(35.6, 207.3, 'right'), valpos=(35.6, 209.3, 'right'))
pwr('+24V', *r1['1'])
wire(r1['2'], d2['2']); label('PWR_LED', 33.02, 201.93)
pwr('GND', *d2['1'])

j2 = part('J2', 259.08, 127.0, refpos=(259.08, 114.3), valpos=(259.08, 140.9))
for i in range(1, 9):
    x, y = j2[str(i)]
    wire((x - 10.16, y), (x, y))
    label(f'OUT{i}', x - 10.16, y)

# ---------------------------------------------------------------- notes
text('8 KANAL OPTO-IZOLELI HIGH-SIDE (PNP) MOSFET CIKIS KARTI  -  24 V DC, 5 A / kanal, toplam 20 A', 81.28, 12.7, 2.5)
text('GIRIS: AC optokuplor, JP1 1-2 = NPN (COM=+24V), JP1 2-3 = PNP (COM=0V), jumper yok = harici COM (tam izole)', 81.28, 17.78)
text('Giris akimi ~3.7 mA @24V, acma esigi ~7..9 V.  LED Dn1 kapi surme akimi ile yanar (kanal aktif).', 81.28, 21.59)
text('GIRIS KLEMENSI', 25.4, 36.83); text('GIRIS TIPI SECIMI', 25.4, 82.55)
text('BESLEME 24V DC', 25.4, 116.84); text('BESLEME KORUMA', 25.4, 154.94); text('BESLEME LED', 25.4, 186.69)
text('CIKIS KLEMENSI\n24V PNP (kaynak)', 248.92, 110.49)
text('Yukler OUTn ile 0V arasina baglanir.\nFn: 7A hizli sigorta (kisa devre).\nDn3: enduktif yuk serbest gecis diyodu.\nAnahtarlama < 20 Hz (PWM icin uygun degil).', 243.84, 165.1)

sch = [S('kicad_sch'), [S('version'), 20230121], [S('generator'), S('eeschema')], [S('uuid'), ROOT_UUID],
       [S('paper'), 'A3'],
       [S('title_block'), [S('title'), '8 Kanal 24V PNP MOSFET Cikis Karti (NPN/PNP girisli)'],
        [S('date'), '2026-11-11'], [S('rev'), '1.0'], [S('comment'), 1, '5 A / kanal, toplam 20 A, DIN ray (72 mm PCB tasiyici)']],
       [S('lib_symbols')] + list(libsyms.values())]
flush_wires()
sch += items
sch.append([S('sheet_instances'), [S('path'), '/', [S('page'), '1']]])
out = sys.argv[1] if len(sys.argv) > 1 else '../mosfet8.kicad_sch'
open(out, 'w').write(dump(sch) + '\n')
import json
json.dump({'root': ROOT_UUID, 'symbols': {k: v for k, v in SYM_UUID.items() if not k.startswith('#')}},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sym_uuid.json'), 'w'), indent=1)
print('wrote', out, len(items), 'items')
