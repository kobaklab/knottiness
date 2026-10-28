"""data/plate_xliv.txt + data/partitions_p332.txt -> data/census.csv, checked for consistency and
against Tait's own totals (On Knots II, §§4-6).

Columns filled later (row, col, notes) are preserved when the CSV already exists.

  uv run scripts/build_census.py      (from inside seven-orders/)"""
import csv, re, sys
from collections import Counter
from tait import SEVEN_ORDERS
P = SEVEN_ORDERS.data

def lines(name):
    for line in open(P / name, encoding='utf-8'):
        line = line.split('#')[0].rstrip() if line.lstrip().startswith('#') else line.rstrip()
        if line.strip(): yield line

ROMAN = dict(I=1, V=5, X=10, L=50)
def roman(s):
    v = [ROMAN[c] for c in s]
    return sum(-a if i + 1 < len(v) and a < v[i + 1] else a for i, a in enumerate(v))

# --- the plate: types in plate order
types = []
for line in lines('plate_xliv.txt'):
    key, header, figs = (x.strip() for x in line.split('|'))
    order, t = key.split(); order = int(order)
    figs = [f.split('/') for f in figs.split()]
    types.append(dict(order=order, numeral=t if not t.isdigit() else '', header=header,
                      kirkman=[f[0] for f in figs], former=[f[1] if len(f) > 1 else '' for f in figs]))
# type numbers within each order: Roman numeral if printed, else position
pos = Counter()
for t in types:
    pos[t['order']] += 1
    t['type'] = roman(t['numeral']) if t['numeral'] else pos[t['order']]

# --- the partitions (text, §6)
parts = {}
for line in lines('partitions_p332.txt'):
    key, forms = line.split(':'); order, t = key.split()
    parts[(int(order), roman(t) if not t.isdigit() else int(t))] = forms.split()

errs = []
def err(m): errs.append(m)

WORDS = dict(Unique=1, Two=2, Three=3, Four=4, Five=5, Six=6)
for t in types:
    key = (t['order'], t['type']); n = len(t['kirkman'])
    if t['numeral'] and not t['header'].startswith(t['numeral'] + ' '): err(f'{key}: header {t["header"]!r} does not start with the numeral')
    m = re.search(r'(Unique|Un\.|Two|Three|Four|Five|Six) ?(forms)?', t['header'])
    if m:
        want = 1 if m.group(1) in ('Unique', 'Un.') else WORDS[m.group(1)]
        if want != n: err(f'{key}: header says {want} forms, {n} figures')
    if key not in parts: err(f'{key}: no partitions in the text'); continue
    if len(parts[key]) != n: err(f'{key}: {n} figures but {len(parts[key])} partition pairs in the text')
    # amphicheirals: barred partition <-> 'Amph' in the header (8 V: only the 2nd and 3rd forms)
    barred = [p.endswith('*') for p in parts[key]]
    if 'Amph' in t['header']:
        want = [False, True, True] if '2ⁿᵈ & 3ʳᵈ' in t['header'] else [True] * n
        if barred != want: err(f'{key}: header {t["header"]!r} but bars {barred}')
    elif any(barred): err(f'{key}: barred partition without Amphich. in the header')
    for p in parts[key]:
        pair = [p.rstrip('*')] * 2 if p.endswith('*') else p.split('/')
        k = t['order']
        for q in pair:
            d = [int(c) for c in q]
            if sum(d) != 2 * k: err(f'{key} {p}: {q} does not sum to 2n = {2 * k}')
            if min(d) < 2 or max(d) > k: err(f'{key} {p}: {q} has a part < 2 or > n')
            if d != sorted(d, reverse=True): err(f'{key} {p}: {q} not in descending order')
        if sum(len(q) for q in pair) != k + 2: err(f'{key} {p}: {sum(len(q) for q in pair)} meshes, a diagram with n crossings has n + 2')
extra = set(parts) - {(t['order'], t['type']) for t in types}
if extra: err(f'partitions for types not on the plate: {sorted(extra)}')

# Kirkman designations: unique within each order
for o in range(3, 10):
    c = Counter(k for t in types if t['order'] == o for k in t['kirkman'])
    if any(v > 1 for v in c.values()): err(f'order {o}: Kirkman labels repeated: {[k for k, v in c.items() if v > 1]}')

# Tait's totals (§5: knots without composites, 3- to 9-fold; §4: the 6- and 7-fold composites are not figured)
TYPES = {3: 1, 4: 1, 5: 2, 6: 3, 7: 7, 8: 18, 9: 41}
got = Counter(t['order'] for t in types)
for o, n in TYPES.items():
    if got[o] != n: err(f'order {o}: {got[o]} types, Tait says {n}')
for o in (7, 8, 9):
    nums = [t['type'] for t in types if t['order'] == o]
    if nums != list(range(1, len(nums) + 1)): err(f'order {o}: type numerals not consecutive: {nums}')

forms = []
for t in types:
    for i, (k, f) in enumerate(zip(t['kirkman'], t['former'])):
        p = parts.get((t['order'], t['type']), [''] * len(t['kirkman']))[i]
        forms.append(dict(order=t['order'], type=t['type'], numeral=t['numeral'], form=i + 1,
                          n_forms=len(t['kirkman']), header=t['header'] if i == 0 else '',
                          kirkman=k, former=f, partitions=p, amph=int(p.endswith('*'))))
if len(forms) != 144: err(f'{len(forms)} forms, the plate has 144')

out = P / 'census.csv'
keep = {}
if out.exists():
    with open(out, encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            keep[int(r['seq'])] = {k: r.get(k, '') for k in ('row', 'col', 'notes')}
cols = ['seq', 'order', 'type', 'numeral', 'form', 'n_forms', 'kirkman', 'former', 'partitions', 'amph',
        'header', 'plate', 'row', 'col', 'notes']
with open(out, 'w', encoding='utf-8', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=cols, lineterminator='\n'); w.writeheader()
    for i, f in enumerate(forms):
        k = keep.get(i + 1, {})
        w.writerow(dict(seq=i + 1, plate='XLIV', **f, row=k.get('row', ''), col=k.get('col', ''), notes=k.get('notes', '')))
print(f'{len(forms)} forms in {len(types)} types ->', out.relative_to(P.parent.parent))
print('  per order (types/forms):', ', '.join(f'{o}: {got[o]}/{sum(1 for f in forms if f["order"] == o)}' for o in sorted(got)))
print('validation:', 'all checks pass' if not errs else '\n  ' + '\n  '.join(errs))
sys.exit(1 if errs else 0)
