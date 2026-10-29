"""Trace the label glyphs that Plate XLIV needs but the tenfold plates never print: upright i j m n v w
x y z (Kirkman's designations such as 8 Bi, 9 Hz). The labels below the knots are set in the tenfold
poster's traced glyphs (../tenfold/traced/glyphs.json); these additions are traced from Plate XLIV's own
labels with the same method (tait/glyphs.py), and fitted to the tenfold set: scaled so that their
x-height is that of the tenfold upright lowercase, and offset to the tenfold glyphs' stroke width.

  uv run scripts/trace_glyphs.py             (from inside seven-orders/; needs the scans in sources/)

Writes traced/glyphs.json (the additions only, in the tenfold glyphs' units) and their specimen sheet,
output/glyphs/glyph_sheet.svg/.png (../scripts/plot_glyphs.py, as for the tenfold glyphs). Hand-made decisions and edits: data/glyphs.yaml (as for tenfold).

Instances are taken from the Internet Archive photo (the only greyscale scan, as for the tenfold glyphs).
Each label of the 8- and 9-folds is split into its glyphs left to right (pieces overlapping
horizontally are one glyph: the dots of i and j); a label is used only if it splits into exactly as many
glyphs as its text has characters (order digit + Kirkman's letters)."""
import json
from collections import defaultdict
import numpy as np
from scipy import ndimage
from tait import SEVEN_ORDERS as P, TENFOLD
from tait.census import load
from tait.sources import find_knots, align, cells, config
from tait.glyphs import (combine, outline, geom_stroke_width, to_path, load_choices, apply_edits,
                         UP, SMOOTH, _text_mask)

NEW = 'ijmnvwxyz,'                        # missing from the tenfold glyphs (the comma: 7-fold labels, 'II, 7C')
gname = lambda c: 'punct/,' if c == ',' else f'upright/{c}'
XH_LETTERS = set('acemnrsuvwxz')          # x-height letters (no ascender, no descender)
DESC = set('gjpqy,')
choices = load_choices(P) if (P.data / 'glyphs.yaml').exists() else {}

# ---- locate every label on the IA photo: its knots matched to the reference scan's (the PDF)
REF = 'PDF'
gI, rI = find_knots('IA', 'XLIV'); _, rR = find_knots(REF, 'XLIV')
A, match = align(rI, rR, config(REF, 'XLIV')['knot_h'])
if A is None: raise SystemExit('XLIV: the Internet Archive scan cannot be aligned to the PDF (fewer than 10 knots in agreeing rows)')
khI = config('IA', 'XLIV')['knot_h']
cellI = {b: c for row_b, row_c in zip(rI, cells(rI, khI)) for b, c in zip(row_b, row_c)}
paper = ndimage.uniform_filter(gI, 61)
text = _text_mask(gI < paper - 30, khI)

inst = defaultdict(list)                  # char -> [dict(crop, h, drop, seq)]
n_used = n_skip = 0
for f in load(P.data / 'census.csv'):
    if f['order'] < 7: continue                                   # 6-folds: Greek letters first
    b = match.get((f['row'] - 1, f['col'] - 1))
    if b is None: continue                                        # hidden in the IA photo's gutter
    y0, y1, x0, x1 = b; cy0, cy1, cx0, cx1 = cellI[b]
    Y0, Y1 = y1 + 2, min(gI.shape[0], y1 + int(0.42 * khI)); X0, X1 = max(0, cx0), min(gI.shape[1], cx1)
    lab, n = ndimage.label(text[Y0:Y1, X0:X1], structure=np.ones((3, 3)))
    comps = [(sl, i + 1) for i, sl in enumerate(ndimage.find_objects(lab)) if (lab[sl] == i + 1).sum() > 2]   # small: the dots of i and j
    # the label is the first line of text below the knot (the next row's group headers follow lower down)
    tall = [sl[0].start for sl, i in comps if sl[0].stop - sl[0].start > 0.06 * khI]
    if not tall: continue
    reach = 0.13 if f['order'] == 7 else 0.08                     # 7-folds: down to the comma's head
    top0 = min(tall); comps = [(sl, i) for sl, i in comps if sl[0].start < top0 + reach * khI and sl[0].stop > top0]
    # glyphs: pieces overlapping horizontally belong together (i, j: stem and dot)
    comps.sort(key=lambda c: c[0][1].start); groups = []
    for sl, i in comps:
        if groups and sl[1].start < groups[-1]['x1'] - 1:
            g = groups[-1]; g['ids'].append(i); g['x1'] = max(g['x1'], sl[1].stop)
            g['y0'] = min(g['y0'], sl[0].start); g['y1'] = max(g['y1'], sl[0].stop)
        else: groups.append(dict(ids=[i], x0=sl[1].start, x1=sl[1].stop, y0=sl[0].start, y1=sl[0].stop))
    # drop specks: groups much smaller than the label's glyphs
    hmax = max((g['y1'] - g['y0'] for g in groups), default=0)
    groups = [g for g in groups if g['y1'] - g['y0'] > 0.3 * hmax]
    chars = (f['former'] + ',' if f['order'] == 7 else '') + str(f['order']) + f['kirkman']   # 'II,7C'
    if len(groups) != len(chars): n_skip += 1; continue
    n_used += 1
    base = np.median([g['y1'] for g, c in zip(groups, chars) if c not in DESC])
    for g, c in zip(groups, chars):
        keep = ndimage.binary_dilation(np.isin(lab, g['ids']), iterations=2)
        crop = gI[Y0:Y1, X0:X1].copy(); crop[~keep] = np.percentile(crop, 90)
        p = 3; crop = crop[max(0, g['y0'] - p):g['y1'] + p, max(0, g['x0'] - p):g['x1'] + p]
        inst[c].append(dict(crop=crop, h=g['y1'] - g['y0'], drop=g['y1'] - base, seq=f['seq'], top=base - g['y0']))
print(f'labels split into glyphs: {n_used}, skipped (pieces did not match the text): {n_skip}')
print('instances:', ' '.join(f'{c}:{len(inst[c])}' for c in sorted(inst)))

# ---- trace: the new letters, and for scale the x-height letters that the tenfold set has too
REF_LETTERS = 'acersu'
T = json.load(open(TENFOLD.traced / 'glyphs.json', encoding='utf-8'))
def trace_letter(c):
    L = inst.get(c, []); ch_ = choices.get(gname(c), {})
    if not L: return None
    if 'instance' in ch_: L = [L[ch_['instance']]]
    avg, used, ri, pad = combine([o['crop'] for o in L])
    geom, _ = outline(avg, ch_.get('level', 0.5), ch_.get('smooth', SMOOTH), ch_.get('cuts', ()), ch_.get('speck', 0.005 if c in 'ij' else 0.02), True)   # keep the dots
    return dict(geom=geom, used=used, n=len(L), L=L)
traced = {c: r for c in NEW + REF_LETTERS for r in [trace_letter(c)] if r}
# scale: the plate's letters to the tenfold glyph units, letter by letter for the letters both sets have
# (traced heights, so both are measured the same way); the median ratio for all
ratios = {c: -T['glyphs'][f'upright/{c}']['top'] / (traced[c]['geom'].bounds[3] - traced[c]['geom'].bounds[1])
          for c in REF_LETTERS if c in traced}
k = float(np.median(list(ratios.values())))   # glyph units per UP-px
print('scale from', ', '.join(f'{c} {r * UP:.1f}' for c, r in ratios.items()), f'(units per IA px) -> {k * UP:.1f}')
target = T['stroke_width'] / k                 # the tenfold stroke width, in UP-px
XH_TEN = float(np.median([-g['top'] for n_, g in T['glyphs'].items() if n_.startswith('upright/') and g['char'] in XH_LETTERS]))
from shapely.affinity import scale

out = {'units': T['units'] + "; the tenfold glyphs' units (scale fitted on a c e r s u)", 'stroke_width': T['stroke_width'],
       'based_on': 'tenfold/traced/glyphs.json', 'glyphs': {}}
for c in NEW:
    if c not in traced: print(f'{gname(c)}: no instance'); continue
    r = traced[c]; L = r['L']; name = gname(c)
    geom = r['geom']; x0, y0, x1, y1 = geom.bounds
    drop = float(np.median([o['drop'] / o['h'] for o in L])) * (y1 - y0) if c in DESC else 0.0
    base = y1 - drop
    # x-height as in the tenfold set: hand lettering varies by letter, so each letter's body (without
    # the dot of i and j) is scaled to the tenfold upright x-height, about its baseline
    # (the comma: at the common scale, its outline as traced)
    f_xh = 1.0
    if c != ',':
        body = max(getattr(geom, 'geoms', [geom]), key=lambda q: q.area)
        f_xh = XH_TEN / ((base - body.bounds[1]) * k)
        geom = scale(geom, f_xh, f_xh, origin=(x0, base))
        geom = geom.buffer((target - geom_stroke_width(geom)) / 2, join_style=2, mitre_limit=3)
    x0, y0, x1, y1 = geom.bounds
    if c not in DESC: base = y1                   # on the baseline
    src = f'Plate XLIV (IA photo): average of {r["used"]}/{r["n"]}' if r['used'] > 1 else f'Plate XLIV (IA photo): best of {r["n"]}'
    out['glyphs'][name] = dict(char=c, cls=name.split('/')[0], source=src, occurrences=r['n'], d=to_path(geom, x0, base, k),
                               width=round((x1 - x0) * k, 1), top=round((y0 - base) * k, 1), bottom=round((y1 - base) * k, 1))
    print(f'{name}: {src}; x-height scaled by {f_xh:.2f}; top {out["glyphs"][name]["top"]:.0f}, bottom {out["glyphs"][name]["bottom"]:.0f} units')
apply_edits(out['glyphs'], choices)
(P.traced / 'glyphs.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print('->', (P.traced / 'glyphs.json').relative_to(P.dir.parent))

# ---- the glyph sheet of the additions, as for the tenfold glyphs (../scripts/plot_glyphs.py)
import subprocess, sys
subprocess.run([sys.executable, str(P.dir.parent / 'scripts' / 'plot_glyphs.py'), '--poster', P.name], check=True)
