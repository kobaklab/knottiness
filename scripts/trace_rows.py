"""Trace knots of one plate from every available source and keep the first trace that validates.
Shared by the posters: the plate selects the poster (LXXX, LXXXI: tenfold/; XLIV: seven-orders/).

  uv run scripts/trace_rows.py --plate LXXXI --rows 1        # row 1
  uv run scripts/trace_rows.py --plate LXXX --rows 1-3
  uv run scripts/trace_rows.py --plate XLIV --rows all

Validation: one strand, the census's number of crossings (10 for the tenfold plates, the order for
XLIV), and the corner counts of the two mesh classes as given by Tait (region code, or partition pair).

Writes, in the plate's poster directory,
  traced/candidates/<seq>_<source>.json   every attempt (gitignored)
  traced/<seq>.json                       the accepted trace (committed)
  output/knots/<seq>.svg                  rendering in the current default style
  output/review/<plate>_row<NN>.png      traces on each source + annotated rendering (see scripts/review_sheets.py)
and each knot's row and column on the plate in data/census.csv.
"""
import argparse, json, sys
import numpy as np
from tait.sources import find_knots, knot_crop, cells, align, priority, source_path, config, PLATES
from tait.census import plate_forms
from tait.trace import trace
from tait.render import svg, self_intersections

ap = argparse.ArgumentParser()
ap.add_argument('--plate', required=True, choices=list(PLATES))
ap.add_argument('--rows', default='1', help="'1', '1-3' or 'all' (1-based)")
ap.add_argument('--sources', help='comma-separated, in order of preference (default: all, for this plate)')
a = ap.parse_args()
P = PLATES[a.plate]; TRACED_DIR, OUTPUT_DIR, DATA_DIR = P.traced, P.output, P.data
PRIORITY = priority(a.plate)
sources = [s for s in (a.sources.split(',') if a.sources else PRIORITY) if source_path(s, a.plate).exists()]
forms = plate_forms(a.plate)

# --- segment every source; align rows to a reference source that finds exactly all forms ---
seg = {s: find_knots(s, a.plate) for s in sources}
for s, (g, rows) in seg.items():
    print(f'{s}: {sum(map(len, rows))} knots in {len(rows)} rows (plate has {len(forms)})')
ref = next((s for s in sources if sum(map(len, seg[s][1])) == len(forms)), None)
if ref is None: sys.exit('no source segments the complete plate; cannot assign census numbers safely')
ref_rows = seg[ref][1]
if a.rows == 'all': rows_sel = list(range(len(ref_rows)))
elif '-' in a.rows: lo, hi = map(int, a.rows.split('-')); rows_sel = list(range(lo - 1, hi))
else: rows_sel = [int(a.rows) - 1]
start = {r: sum(len(x) for x in ref_rows[:r]) for r in range(len(ref_rows))}

# --- match every source's knots to the reference by position, not by count ---
# An affine map per source (fitted on the knots both contain) pairs each reference knot with the
# nearest mapped knot of the source, so a knot missing in one scan affects only that knot.
match = {}                                  # (source, ref_row, ref_col) -> box in that source
cellmap = {}                                # (source, ref_row, ref_col) -> label cell in that source
affine = {}                                 # source -> 2x3 map from its page to the reference page
ref_cells = cells(ref_rows, config(ref, a.plate)['knot_h'])
for s in sources:
    if s == ref:
        affine[s] = np.array([[1.0, 0, 0], [0, 1.0, 0]])
        for r, row in enumerate(ref_rows):
            for j, b in enumerate(row): match[(s, r, j)] = b; cellmap[(s, r, j)] = ref_cells[r][j]
        continue
    A, m = align(seg[s][1], ref_rows, config(ref, a.plate)['knot_h'])
    if A is None:
        print(f'{s}: too few rows agree with {ref} to align; skipping'); continue
    affine[s] = A
    Ainv = np.linalg.inv(np.vstack([A, [0, 0, 1]]))[:2]        # reference page -> this source
    for (r, j), bb in m.items():
        match[(s, r, j)] = bb
        y0, y1, x0, x1 = ref_cells[r][j]
        (sx0, sy0), (sx1, sy1) = Ainv @ [x0, y0, 1], Ainv @ [x1, y1, 1]
        cellmap[(s, r, j)] = (int(sy0), int(sy1), int(sx0), int(sx1))
    n_ref = sum(map(len, ref_rows))
    print(f'{s}: aligned to {ref}; {n_ref - len(m)} reference knots have no counterpart in {s}')

(TRACED_DIR / 'candidates').mkdir(parents=True, exist_ok=True)
(OUTPUT_DIR / 'knots').mkdir(parents=True, exist_ok=True)
attempts = {}   # seq -> {source: (record, gray crop)}
for r in rows_sel:
    for j in range(len(ref_rows[r])):
        f = forms[start[r] + j]
        for s in sources:
            box = match.get((s, r, j))
            if box is None: continue
            g = seg[s][0]
            gg, mask, (x0, y0, scale) = knot_crop(s, g, box, plate=a.plate)
            try:
                rep, G, C = (trace(mask, f['code']) if 'code' in f else
                             trace(mask, partitions=f['partitions'], crossings=f['order']))
            except Exception as e:
                rep, C = dict(ok=False, problems=[f'error: {e}'], warnings=[]), None
            expect = dict(code=f['code']) if 'code' in f else dict(order=f['order'], partitions=f['partitions'])
            rec = dict(seq=f['seq'], type=f['type'], form=f['form'], **expect, plate=a.plate,
                       row=r + 1, col=j + 1, source=s, ok=bool(rep['ok']), problems=rep['problems'],
                       warnings=rep.get('warnings', []),
                       crop_origin=[int(x0), int(y0)], scale=scale, crop_size=[gg.shape[1], gg.shape[0]],
                       box=[int(v) for v in box], cell=list(cellmap[(s, r, j)]),
                       ref_source=ref, ref_box=[int(v) for v in ref_rows[r][j]], ref_cell=list(ref_cells[r][j]))
            if rep.get('outer_class'): rec['outer_class'] = ''.join(map(str, rep['outer_class']))   # mesh class of the outer region
            if C is not None:
                # store every 3rd point (~3 px apart at working scale); render.densify re-interpolates
                rec['curve'] = np.round(C[::3], 1).tolist()
                n = len(C)   # crossings: point, and both passes as fractions of the curve length
                rec['crossings'] = [[round(float(np.interp(p, np.arange(n), C[:, 0])), 1),
                                     round(float(np.interp(p, np.arange(n), C[:, 1])), 1),
                                     round(p / n, 4), round(q / n, 4)] for p, q in self_intersections(C)]
            json.dump(rec, open(TRACED_DIR / 'candidates' / f"{f['seq']:03d}_{s}.json", 'w'))
            attempts.setdefault(f['seq'], {})[s] = (rec, gg)

# --- accept the first validating source per knot ---
n_ok = 0
for seq in sorted(attempts):
    cand = attempts[seq]
    best = next((s for s in PRIORITY if s in cand and cand[s][0]['ok']), None)
    status = ' '.join(f"{s}:{'ok' if c[0]['ok'] else 'FAIL'}{'!' if c[0]['ok'] and c[0]['warnings'] else ''}" for s, c in cand.items())
    rec0 = next(iter(cand.values()))[0]
    what = rec0.get('code') or f"{rec0['order']}: {rec0['partitions']}"
    print(f"  #{seq:3d} type {rec0['type']:3d}.{rec0['form']:<2d} {what:16s} {status:36s} -> {best or 'NEEDS ATTENTION'}")
    if best:
        n_ok += 1; rec = cand[best][0]
        json.dump(rec, open(TRACED_DIR / f'{seq:03d}.json', 'w'))
        s_, _ = svg(np.array(rec['curve']), *rec['crop_size'])
        open(OUTPUT_DIR / 'knots' / f'{seq:03d}.svg', 'w').write(s_)
print(f'{n_ok}/{len(attempts)} knots accepted')

# --- record each knot's position on the plate (from the reference segmentation) in census.csv ---
import csv
pos = {forms[start[r] + j]['seq']: (r + 1, j + 1) for r in rows_sel for j in range(len(ref_rows[r]))}
with open(DATA_DIR / 'census.csv', encoding='utf-8', newline='') as fh:
    table = list(csv.DictReader(fh)); cols_ = list(table[0].keys())
for row in table:
    if int(row['seq']) in pos: row['row'], row['col'] = pos[int(row['seq'])]
with open(DATA_DIR / 'census.csv', 'w', encoding='utf-8', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=cols_, lineterminator='\n'); w.writeheader(); w.writerows(table)

# --- review sheets ---
from tait.review import make_sheets
make_sheets(a.plate, [r + 1 for r in rows_sel], sources)
