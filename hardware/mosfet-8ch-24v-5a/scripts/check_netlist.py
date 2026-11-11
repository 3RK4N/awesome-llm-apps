#!/usr/bin/env python3
"""Compare a KiCad netlist (kicadsexpr) exported from the schematic with design.py."""
import sys
from sexpr import parse, find
from design import nets, PARTS
root = parse(open(sys.argv[1]).read())
got = {}
for net in find(find(root, 'nets')[0], 'net'):
    name = find(net, 'name')[0][1]
    nodes = {(find(n, 'ref')[0][1], find(n, 'pin')[0][1]) for n in find(net, 'node')}
    got[name.lstrip('/')] = nodes
exp = nets()
ok = True
for name, nodes in exp.items():
    if got.get(name) != nodes:
        ok = False
        print('MISMATCH', name, 'expected', sorted(nodes), 'got', sorted(got.get(name, [])))
for name in got:
    if name not in exp:
        ok = False
        print('EXTRA NET', name, sorted(got[name]))
comps = {find(c, 'ref')[0][1]: find(c, 'footprint')[0][1] for c in find(find(root, 'components')[0], 'comp')}
for ref, p in PARTS.items():
    if comps.get(ref) != p['fp']:
        ok = False
        print('FOOTPRINT', ref, comps.get(ref))
print('NETLIST OK: %d nets, %d parts' % (len(exp), len(PARTS)) if ok else 'NETLIST FAILED')
sys.exit(0 if ok else 1)
