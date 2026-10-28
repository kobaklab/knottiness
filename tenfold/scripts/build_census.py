"""data/census_p503.txt -> data/census.csv, validated against Tait's own totals (§21).

Columns filled later (row, col, kirkman, notes) are preserved when the CSV already exists."""
import csv, sys
from tait import TENFOLD
DATA_DIR = TENFOLD.data
from tait.codes import parse
from tait.census import parse_transcription, PLATE_SIZE

forms = parse_transcription()

# Places where the order of forms on the plates differs from the list on p. 503.
# type -> plate order, given as the form numbers of the p. 503 list.
# Type 79: the plate prints εc under R³ and βc under S³; the list says "βc, εc".
# (Found by tracing: both forms trace perfectly, with the two codes swapped.)
PLATE_ORDER = {79: [2, 1]}
for t, order in PLATE_ORDER.items():
    idx = [i for i, f in enumerate(forms) if f['type'] == t]
    block = [dict(forms[idx[k - 1]]) for k in order]
    for i, f in zip(idx, block): f['form'] = idx.index(i) + 1; forms[i] = f
errs = []
for f in forms:
    fam, parts, amph = parse(f['code'])
    f['family'] = fam
    exp = {'6/6': [6, 6], '5/7': [5, 7], '4/8': [4, 8], '3/9': [3, 9]}[fam]
    if sorted(len(p) for p in parts) != exp: errs.append(f"{f['type']}.{f['form']} {f['code']}: wrong mesh counts")
    if any(sum(p) != 20 for p in parts): errs.append(f"{f['type']}.{f['form']} {f['code']}: corners != 20")
    if amph and fam != '6/6': errs.append(f"{f['code']}: bar outside the 6/6 family")

# Tait's totals, §21: (non-unique types, unique types, forms) per family
TAIT = {'6/6': (24, 14, 133), '5/7': (43, 21, 200), '4/8': (7, 8, 25), '3/9': (0, 6, 6)}
types = {(f['family'], f['type']): f['n_forms'] for f in forms}
for fam, want in TAIT.items():
    got = (sum(1 for (fm, t), n in types.items() if fm == fam and n > 1),
           sum(1 for (fm, t), n in types.items() if fm == fam and n == 1),
           sum(1 for f in forms if f['family'] == fam))
    if got != want: errs.append(f'{fam}: got {got}, Tait says {want}')
if len(forms) != 364 or len(types) != 123: errs.append(f'{len(forms)} forms / {len(types)} types (expected 364 / 123)')

# plate assignment: LXXX holds the first 182 forms; LXXXI starts with the 3rd form of type 46
split = PLATE_SIZE['LXXX']
assert forms[split]['type'] == 46 and forms[split]['form'] == 3
for i, f in enumerate(forms):
    f['seq'] = i + 1; f['plate'] = 'LXXX' if i < split else 'LXXXI'

# Misprinted region codes, corrected for the poster: seq -> (as printed, corrected)
# #352 (type 111): text and plate print 'lκ', but the outer region (6 corners) is in class l, so by
# Tait's convention (2nd letter = class containing the outer region) it is 'κl'.
CODE_CORRECTIONS = {352: ('lκ', 'κl')}
for seq, (printed, fixed) in CODE_CORRECTIONS.items():
    assert forms[seq - 1]['code'] == printed, (seq, forms[seq - 1]['code'])
    forms[seq - 1]['code'] = fixed

out = DATA_DIR / 'census.csv'
keep = {}
if out.exists():
    with open(out, encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            keep[int(r['seq'])] = {k: r.get(k, '') for k in ('row', 'col', 'kirkman', 'notes')}
with open(out, 'w', encoding='utf-8', newline='') as fh:
    w = csv.writer(fh, lineterminator='\n')
    w.writerow(['seq', 'type', 'form', 'code', 'family', 'plate', 'row', 'col', 'kirkman', 'notes'])
    for f in forms:
        k = keep.get(f['seq'], {})
        w.writerow([f['seq'], f['type'], f['form'], f['code'], f['family'], f['plate'],
                    k.get('row', ''), k.get('col', ''), k.get('kirkman', ''), k.get('notes', '')])
print(f'{len(forms)} forms in {len(types)} types -> {out.relative_to(DATA_DIR.parent)}')
print('validation:', 'all checks pass' if not errs else '\n  ' + '\n  '.join(errs))
sys.exit(1 if errs else 0)
