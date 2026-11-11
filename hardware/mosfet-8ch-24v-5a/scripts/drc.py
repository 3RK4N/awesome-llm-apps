#!/usr/bin/python3
"""Run KiCad DRC on the board and print a summary."""
import sys, re, collections, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
rpt = sys.argv[2] if len(sys.argv) > 2 else '/tmp/drc.rpt'
pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
txt = open(rpt).read()
kinds = collections.Counter(re.findall(r'^\[(\w+)\]', txt, re.M))
for k, v in kinds.most_common():
    print(f'{v:4d}  {k}')
for m in re.findall(r'\*\* Found (\d+) (.*?) \*\*', txt):
    print(m)
