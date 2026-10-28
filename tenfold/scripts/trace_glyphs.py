"""Trace Tait's annotation glyphs (84: digits, capitals incl. Greek, italic/upright lowercase, Greek).

  uv run scripts/trace_glyphs.py            # uses output/glyphs/collected.pkl if present (fast)
  uv run scripts/trace_glyphs.py --fresh    # re-collect all instances from the scans (~3 min)

Writes traced/glyphs.json (outlines + metrics, see tait/glyphs.py) and review sheets in
output/glyphs/: one per glyph class (the original next to the traced glyph) and a specimen of all
glyphs on common baselines. Hand-made decisions are in data/glyphs.yaml, including the hand edits
(`edit:` lists) applied to the finished outlines (../scripts/edit_glyphs.py re-applies them alone)."""
import io, json
from collections import defaultdict
import numpy as np
import cairosvg
from PIL import Image, ImageDraw
from tait import TENFOLD
from tait.review import font
TRACED_DIR, OUTPUT_DIR = TENFOLD.traced, TENFOLD.output
from tait.glyphs import (ORDER, DESCENDERS, SHARPEN, UP, LEVEL, SMOOTH, SCALE, collect, combine, outline,
                         geom_stroke_width, smooth_geom, to_path, load_choices, _isolate, apply_edits)

def _rasterise(geom, shape=None):
    """shapely geometry (UP x px) -> boolean mask on a canvas fitted to the geometry, with a margin"""
    from PIL import ImageDraw as _D
    x0, y0, x1, y1 = geom.bounds; m = 4; ox, oy = x0 - m, y0 - m
    im = Image.new('1', (int(x1 - x0) + 2 * m + 1, int(y1 - y0) + 2 * m + 1), 0); d = _D.Draw(im)
    for p in getattr(geom, 'geoms', [geom]):
        d.polygon([(c[0] - ox, c[1] - oy) for c in p.exterior.coords], fill=1)
        for r in p.interiors: d.polygon([(c[0] - ox, c[1] - oy) for c in r.coords], fill=0)
    return np.array(im, bool)

import argparse, pickle
ap = argparse.ArgumentParser(); ap.add_argument('--fresh', action='store_true'); args = ap.parse_args()
choices = load_choices()
CACHE = OUTPUT_DIR / 'glyphs' / 'collected.pkl'; CACHE.parent.mkdir(parents=True, exist_ok=True)
if CACHE.exists() and not args.fresh:
    found, occ, maps = pickle.load(open(CACHE, 'rb'))
else:
    found, occ, maps = collect()
    maps = {p: (gI.clip(0, 255).astype(np.uint8), txt, A, gH.clip(0, 255).astype(np.uint8))
            for p, (gI, txt, A, gH) in maps.items()}
    pickle.dump((found, occ, maps), open(CACHE, 'wb'), protocol=5)
H_CAP = float(np.median([o['box'][1] - o['box'][0] for (cl, c), L in found.items() if cl == 'capitals' for o in L]))
print(f'median capital height: {H_CAP:.1f} px (Internet Archive scan)')

# ---- descenders: region letters stand in pairs on one baseline; a partner without descender gives it
SITS = lambda key: key[0] in ('digits', 'capitals') or key[1] not in DESCENDERS.get(key[0], set())
by_pos = {(o['seq'], o['corner']): (key, o) for key, L in found.items() for o in L if o['corner'] in ('BL', 'BR')}
drops = defaultdict(list)
for (seq, corner), (key, o) in by_pos.items():
    other = by_pos.get((seq, 'BR' if corner == 'BL' else 'BL'))
    if other and SITS(other[0]): drops[key].append(o['box'][1] - other[1]['box'][1])

glyphs = {}
for cl, chars in ORDER:
    for ch in chars:
        key = (cl, ch); name = f'{cl}/{ch}'; ch_ = choices.get(name, {})
        if 'instance' in ch_:
            if ch_['instance'] >= len(occ.get(key, [])): raise SystemExit(f"{name}: instance {ch_['instance']} but only {len(occ.get(key, []))} occurrences: {occ.get(key)}")
            o = occ[key][ch_['instance']]; gI, txt, Ainv, gH = maps[o['plate']]
            got = _isolate(gI, txt, Ainv, o['ht'], ch_.get('pick', 'nearest'))
            src = f"occurrence {ch_['instance']} (#{o['seq']})"
            if got is None: raise SystemExit(f'{name}: chosen occurrence could not be isolated')
            avg = combine([got['crop']])[0]; used, ref = 1, got['crop']; h_ref = got['box'][1] - got['box'][0]
            ref_occ = dict(o, box=got['box'])
        elif found.get(key):
            crops = [o['crop'] for o in found[key]]
            avg, used, ri, pad = combine(crops); ref = crops[ri]
            h_ref = found[key][ri]['box'][1] - found[key][ri]['box'][0]; ref_occ = found[key][ri]
            src = f'average of {used}/{len(crops)}' if used > 1 else f'best of {len(crops)}'
        else:                                     # not visible in the greyscale photo: black-and-white scan
            o = occ[key][0]; gH = maps[o['plate']][3]; y0, y1, x0, x1 = o['ht']
            im = Image.fromarray(gH[y0 - 3:y1 + 3, x0 - 3:x1 + 3].astype('uint8'))
            ref = np.array(im.resize((max(1, int(im.width * SCALE)), max(1, int(im.height * SCALE))), Image.LANCZOS)).astype(float)
            avg = combine([ref])[0]; used, h_ref = 1, (y1 - y0) * SCALE; src = 'black-and-white scan (only occurrence)'
            ref_occ = None
        sharp = ch_.get('sharpen', cl in SHARPEN)
        # type-like glyphs are traced at the true edge (50 % ink): a lower level fills the inside corners
        # where serifs meet stems; the calligraphic ones lower, to keep their hairlines
        geom, mask = outline(avg, ch_.get('level', 0.5 if sharp else LEVEL), ch_.get('smooth', SMOOTH),
                            ch_.get('cuts', ()), ch_.get('speck', 0.04), sharp)
        drop = 0.0 if SITS(key) else float(np.median(drops[key])) if drops.get(key) else None
        # true stroke weight: the outline at 50 % ink, measured like the traced outline (2 * area / length)
        true50, _ = outline(avg, 0.5, ch_.get('smooth', SMOOTH), ch_.get('cuts', ()), ch_.get('speck', 0.04))
        glyphs[name] = dict(char=ch, cls=cl, source=src, n=len(occ.get(key, [])), geom=geom,
                            sw=geom_stroke_width(true50) / UP, drop=drop, ref=ref, h_ref=h_ref,
                            smooth=ch_.get('smooth', SMOOTH), ref_occ=ref_occ, sharp=sharp,
                            align=ch_.get('align', 'baseline'))

# ---- common stroke width: offset every outline to the median true stroke weight (measured at 50 % ink)
target = float(np.median([g['sw'] for g in glyphs.values()]))
print(f'stroke widths: median {target:.2f} px, range {min(g["sw"] for g in glyphs.values()):.2f}-'
      f'{max(g["sw"] for g in glyphs.values()):.2f} px -> all set to {target:.2f}')
# descenders that could not be measured: median of the measured ones, relative to glyph height
rel = [g['drop'] / g['h_ref'] for g in glyphs.values() if g['drop']]
for name, g in glyphs.items():
    if g['drop'] is None: g['drop'] = float(np.median(rel)) * g['h_ref']; g['source'] += ', descender estimated'

k = 1000 / (H_CAP * UP)                          # UP-x pixels -> glyph units (1000 = capital height)
out = {'units': '1000 = median capital height; y down, baseline at y = 0, ink from x = 0',
       'stroke_width': round(target * UP * k, 1), 'glyphs': {}}
for name, g in glyphs.items():
    # the outline was taken at a lower ink level (to keep hairlines), so it is heavier than the 50 % mask
    # measured in 'sw'; offset by the difference between the outline's own width and the target
    own = geom_stroke_width(g['geom']) / UP
    if g['sharp']: geom = g['geom'].buffer((target - own) / 2 * UP, join_style=2, mitre_limit=3)
    else: geom = smooth_geom(g['geom'].buffer((target - own) / 2 * UP, join_style=1), g['smooth'])
    x0, y0, x1, y1 = geom.bounds
    if g['align'] == 'top': base = y0 + H_CAP * UP * (geom.bounds[3] - geom.bounds[1]) / (g['h_ref'] * UP)
    else: base = y1 - g['drop'] * UP * (geom.bounds[3] - geom.bounds[1]) / (g['h_ref'] * UP)
    g['out'] = dict(char=g['char'], cls=g['cls'], source=g['source'], occurrences=g['n'],
                    d=to_path(geom, x0, base, k), width=round((x1 - x0) * k, 1),
                    top=round((y0 - base) * k, 1), bottom=round((y1 - base) * k, 1),
                    stroke_offset_px=round((target - own) / 2, 3))
    out['glyphs'][name] = g['out']
apply_edits(out['glyphs'], choices)              # hand edits of the finished outlines (data/glyphs.yaml)
(TRACED_DIR / 'glyphs.json').write_text(json.dumps({k_: v for k_, v in out.items()}, ensure_ascii=False, indent=1))
print('traced', len(out['glyphs']), 'glyphs -> traced/glyphs.json')

# ---- review sheets
D = OUTPUT_DIR / 'glyphs'; D.mkdir(parents=True, exist_ok=True)
F = font('roman', 15)
def render(g, cap_px, margin=10):
    """glyph on its baseline; returns image and baseline y"""
    s = cap_px / 1000; w = g['width'] * s + 2 * margin; top = -1550 * s; bot = 700 * s
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{bot - top:.0f}" '
           f'viewBox="{-margin / s:.1f} {-1550:.1f} {w / s:.1f} {2250:.1f}">'
           f'<line x1="{-margin / s:.1f}" y1="0" x2="{w / s:.1f}" y2="0" stroke="#7aa6e0" stroke-width="{1.5 / s:.1f}"/>'
           f'<path d="{g["d"]}" fill="#1a1a1a" fill-rule="evenodd"/></svg>')
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(), background_color='white'))).convert('RGB')
for cl, chars in ORDER:
    cells = []
    for ch in chars:
        g = glyphs[f'{cl}/{ch}']; cap = 110
        if g['ref_occ'] is not None:                 # the reference occurrence with its surroundings on the page
            gI = maps[g['ref_occ']['plate']][0]; y0, y1, x0, x1 = g['ref_occ']['box']; m = int(0.3 * (y1 - y0))
            o = Image.fromarray(gI[max(0, y0 - m):y1 + m, max(0, x0 - m):x1 + m].astype('uint8')).convert('RGB')
        else:
            o = Image.fromarray(g['ref'].clip(0, 255).astype('uint8')).convert('RGB')
        o = o.resize((max(1, int(o.width * cap / H_CAP)), max(1, int(o.height * cap / H_CAP))), Image.LANCZOS)
        if o.height > 145: o = o.resize((max(1, int(o.width * 145 / o.height)), 145), Image.LANCZOS)   # fit the band
        t = render(g['out'], cap)
        W = max(o.width, t.width) + 20; cell = Image.new('RGB', (W, 180 + t.height + 5), 'white'); d = ImageDraw.Draw(cell)
        cell.paste(o, ((W - o.width) // 2, max(30, 175 - o.height))); cell.paste(t, ((W - t.width) // 2, 180))
        d.text((6, 4), ch, fill='black', font=font('roman', 22))
        for i, line in enumerate(g['source'].replace(', ', ',\n').split('\n')[:2]): d.text((30, 6 + 16 * i), line, fill=(90, 90, 90), font=F)
        cells.append(cell)
    per = 8; rows_ = [cells[i:i + per] for i in range(0, len(cells), per)]
    RH = max(c.height for c in cells) + 10
    sheet = Image.new('RGB', (max(sum(c.width + 8 for c in r) for r in rows_) + 10, len(rows_) * RH + 10), 'white')
    for i, r in enumerate(rows_):
        x = 5
        for c in r: sheet.paste(c, (x, 5 + i * RH)); x += c.width + 8
    sheet.save(D / f'review_{cl}.png')
# specimen: all glyphs on common baselines, large and at print size
for cap, name in ((70, 'specimen.png'), (14, 'specimen_print_size.png')):
    lines = []
    for cl, chars in ORDER:
        ims = [render(glyphs[f'{cl}/{c}']['out'], cap, margin=max(2, cap // 12)) for c in chars]
        line = Image.new('RGB', (sum(i.width for i in ims) + 20, ims[0].height), 'white'); x = 10
        for i in ims: line.paste(i, (x, 0)); x += i.width
        lines.append(line)
    sp = Image.new('RGB', (max(l.width for l in lines), sum(l.height for l in lines)), 'white'); y = 0
    for l in lines: sp.paste(l, (0, y)); y += l.height
    if cap < 30: sp = sp.resize((sp.width * 3, sp.height * 3), Image.NEAREST)
    sp.save(D / name)
print('review sheets in', D)
