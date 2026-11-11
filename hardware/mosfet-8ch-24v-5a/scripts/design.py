"""Single source of truth: components, footprints and pin->net table.

Both gen_sch.py (schematic) and gen_pcb.py (board) read this table, and
check_netlist.py verifies the generated schematic against it.
"""
N = 8  # channels

FP = {
    'R0603': 'Resistor_SMD:R_0603_1608Metric',
    'R1206': 'Resistor_SMD:R_1206_3216Metric',
    'LED': 'LED_SMD:LED_0603_1608Metric',
    'OPTO': 'Package_SO:SOP-4_4.4x2.6mm_P1.27mm',
    'DPAK': 'Package_TO_SOT_SMD:TO-252-2',
    'SOD123': 'Diode_SMD:D_SOD-123',
    'SMA': 'Diode_SMD:D_SMA',
    'SMB': 'Diode_SMD:D_SMB',
    'FUSE': 'Fuse:Fuse_Littelfuse-NANO2-451_453',
    'CAP': 'Capacitor_SMD:CP_Elec_8x10',
    'J_IN': 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-9-3.5-H_1x09_P3.50mm_Horizontal',
    'J_OUT': 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-8-5.08_1x08_P5.08mm_Horizontal',
    'J_PWR': 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-3-4-5.08_1x04_P5.08mm_Horizontal',
    'JP': 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
}

# ref -> dict(sym, value, fp, mpn, desc, pins{num: net})
PARTS = {}

def add(ref, sym, value, fp, mpn, desc, pins):
    PARTS[ref] = dict(sym=sym, value=value, fp=FP[fp], mpn=mpn, desc=desc,
                      pins={str(k): v for k, v in pins.items()})

for n in range(1, N + 1):
    add(f'R{n}1', 'Device:R', '4k7', 'R1206', 'RC1206FR-074K7L',
        'Giris seri direnci 4k7 1% 0.25W 1206', {1: f'IN{n}', 2: f'A{n}'})
    add(f'R{n}2', 'Device:R', '1k', 'R0603', 'RC0603FR-071KL',
        'Opto LED paralel direnci 1k 1% 0603', {1: 'IN_COM', 2: f'A{n}'})
    add(f'U{n}', 'Isolator:LTV-354T', 'TLP290(GB)', 'OPTO', 'TLP290(GB-TP,SE',
        'AC girisli optokuplor SO-4, CTR>=100% (alt: LTV-354T, EL354N)',
        {1: f'A{n}', 2: 'IN_COM', 3: 'GND', 4: f'LK{n}'})
    add(f'D{n}1', 'Device:LED', 'GREEN', 'LED', 'KP-1608SGC / 19-217/GHC',
        'Kanal durum LED yesil 0603', {1: f'LK{n}', 2: f'GD{n}'})
    add(f'R{n}4', 'Device:R', '10k', 'R0603', 'RC0603FR-0710KL',
        'Kapi seri direnci 10k 1% 0603', {1: f'GD{n}', 2: f'G{n}'})
    add(f'R{n}3', 'Device:R', '10k', 'R0603', 'RC0603FR-0710KL',
        'Kapi-kaynak direnci 10k 1% 0603', {1: '+24V', 2: f'G{n}'})
    add(f'D{n}2', 'Device:D_Zener', 'BZT52C15', 'SOD123', 'BZT52C15-7-F',
        'Kapi koruma zeneri 15V SOD-123', {1: '+24V', 2: f'G{n}'})
    add(f'Q{n}', 'Device:Q_PMOS_GDS', 'SUD50P06-15', 'DPAK', 'SUD50P06-15-GE3',
        'P-MOSFET -60V 15mOhm DPAK (alt: SQD50P06-15L, NCE60P50K)',
        {1: f'G{n}', 2: f'D{n}', 3: '+24V'})
    add(f'F{n}', 'Device:Fuse', '7A', 'FUSE', '0451007.MRL',
        'SMD sigorta 7A hizli, Littelfuse Nano2 451', {1: f'D{n}', 2: f'OUT{n}'})
    add(f'D{n}3', 'Device:D_Schottky', 'SS36', 'SMA', 'SS36',
        'Serbest gecis diyodu 3A 60V SMA', {1: f'OUT{n}', 2: 'GND'})

add('J1', 'Connector:Screw_Terminal_01x09', 'COM + IN8-1', 'J_IN', 'PT 1,5/9-3,5-H (1984688)',
    'Giris klemensi 9 kutup 3.5mm', {1: 'IN_COM', **{i: f'IN{10 - i}' for i in range(2, 10)}})
add('J2', 'Connector:Screw_Terminal_01x08', 'OUT1-8', 'J_OUT', 'MKDS 1,5/8-5,08 (1715786)',
    'Cikis klemensi 8 kutup 5.08mm', {i: f'OUT{i}' for i in range(1, 9)})
add('J3', 'Connector:Screw_Terminal_01x04', '0V 0V 24V 24V', 'J_PWR', 'MKDS 3/4-5,08 (1711741)',
    'Besleme klemensi 4 kutup 5.08mm 24A', {1: 'GND', 2: 'GND', 3: '+24V', 4: '+24V'})
add('JP1', 'Connector_Generic:Conn_01x03', 'NPN|COM|PNP', 'JP', 'Pin header 1x3 2.54mm + jumper',
    'Giris tipi secimi: 1-2 NPN (COM=+24V), 2-3 PNP (COM=0V)', {1: '+24V', 2: 'IN_COM', 3: 'GND'})
add('C1', 'Device:C_Polarized', '100u/50V', 'CAP', 'EEE-FK1H101P',
    'Elektrolitik 100uF 50V SMD 8x10', {1: '+24V', 2: 'GND'})
add('D1', 'Device:D_Zener', 'SMBJ33A', 'SMB', 'SMBJ33A',
    'TVS 33V 600W tek yonlu SMB', {1: '+24V', 2: 'GND'})
add('R1', 'Device:R', '10k', 'R0603', 'RC0603FR-0710KL',
    'Besleme LED direnci 10k 0603', {1: '+24V', 2: 'PWR_LED'})
add('D2', 'Device:LED', 'BLUE', 'LED', 'KP-1608QBC-D / 19-217/BHC',
    'Besleme LED mavi 0603', {1: 'GND', 2: 'PWR_LED'})

def nets():
    out = {}
    for ref, p in PARTS.items():
        for num, net in p['pins'].items():
            out.setdefault(net, set()).add((ref, num))
    return out
