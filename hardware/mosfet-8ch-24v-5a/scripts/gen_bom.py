#!/usr/bin/env python3
"""Write a grouped BOM (CSV) from design.py."""
import csv, re, sys
from design import PARTS
groups = {}
for ref, p in PARTS.items():
    groups.setdefault((p['value'], p['fp'].split(':')[1], p['mpn'], p['desc']), []).append(ref)
key = lambda r: (re.match(r'[A-Z]+', r).group(), int(re.search(r'\d+', r).group()))
rows = sorted(((sorted(refs, key=key), k) for k, refs in groups.items()), key=lambda r: key(r[0][0]))
with open(sys.argv[1] if len(sys.argv) > 1 else '../bom.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Adet', 'Referanslar', 'Deger', 'Kilif', 'Onerilen parca (MPN)', 'Aciklama'])
    for refs, (value, fp, mpn, desc) in rows:
        w.writerow([len(refs), ' '.join(refs), value, fp, mpn, desc])
print('bom rows', len(rows), 'parts', len(PARTS))
