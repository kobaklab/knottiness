"""Check the Kirkman labels in data/census.csv against the traced geometry.

Kirkman (Trans. RSE 32, 1885, pp. 483-491) sorts the ten-crossing knots into lists 10A, 10B, ...
by their flaps: F_e = number of flaps of e loops, a flap of e loops being a chain of e bigons
(a twist of e+1 crossings). So the letter of each label is fixed by the diagram's geometry.
This script computes every traced knot's flap signature and reports labels whose letter
does not match, plus list-length discrepancies."""
import csv, json
from collections import Counter
from tait import TENFOLD
DATA_DIR, TRACED_DIR = TENFOLD.data, TENFOLD.traced
from tait.diagram import flaps, KIRKMAN_LISTS, KIRKMAN_LIST_LENGTH

rows = list(csv.DictReader(open(DATA_DIR / 'census.csv', encoding='utf-8')))
inv = {tuple(sorted(v.items())): k for k, v in KIRKMAN_LISTS.items()}
per_list = Counter(); problems = []
for r in rows:
    seq = int(r['seq']); p = TRACED_DIR / f'{seq:03d}.json'
    if not p.exists(): continue
    F = flaps(json.load(open(p))['curve'])
    geo = inv.get(tuple(sorted(F.items())), 'solid' if not F else '?')
    per_list[geo] += 1
    printed = r['kirkman'].rstrip('0123456789')
    if (printed or 'solid') != geo:
        problems.append(f"#{seq}: printed {r['kirkman'] or '(none)'}, flaps {F} -> list {geo}")
print('labels whose letter disagrees with the geometry:')
print('  ' + ('\n  '.join(problems) if problems else 'none'))
print('knots per list (geometry) vs. length of Kirkman\'s printed list:')
for k, n in KIRKMAN_LIST_LENGTH.items():
    if per_list[k] != n: print(f'  {k}: {per_list[k]} on the plates, {n} in Kirkman\'s list')
print(f"  solid: {per_list['solid']} (Kirkman: 1, described separately)")
