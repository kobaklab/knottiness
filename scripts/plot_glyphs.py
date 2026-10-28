"""Specimen sheet of the traced glyphs (<poster>/traced/glyphs.json): every glyph on its baseline, between two
horizontal guide lines, one block per class: the baseline (y = 0) and, for digits and capitals, the
capital height (y = -1000); for the lowercase classes the x-height (median top of the letters without
ascenders: a c e m n r s u, α γ ε η κ). A poster whose glyph set only adds to another's (seven-orders: the
letters and the comma the tenfold set lacks; 'based_on' in its glyphs.json) shows its additions only,
with the guide lines of the set it adds to.
Writes <poster>/output/glyphs/glyph_sheet.svg (and .png if cairosvg is installed)."""
import json, argparse
from pathlib import Path
from tait import Poster, poster_arg

ap = argparse.ArgumentParser()
poster_arg(ap)
ap.add_argument('--per-row', type=int, default=18)
ap.add_argument('--scale', type=float, default=0.1, help='px per glyph unit')
ap.add_argument('--out', help='default: <poster>/output/glyphs/glyph_sheet.svg')
a = ap.parse_args()
P = Poster(a.poster)
a.out = a.out or str(P.output / 'glyphs' / 'glyph_sheet.svg')

data = json.load(open(P.traced / 'glyphs.json', encoding='utf-8')); G = data['glyphs']
from tait import ROOT
BASE = json.load(open(ROOT / data['based_on'], encoding='utf-8'))['glyphs'] if 'based_on' in data else G   # for the guides
CLASSES = ['digits', 'capitals', 'italic', 'upright', 'greek', 'punct']
S, GAP, MARGIN = a.scale, 380, 60           # gap between glyphs in glyph units, margin in px
ABOVE, BELOW = 1350, 750                    # room above the baseline / below it (units), for ascenders, descenders
LABEL_H, TITLE_H = 26, 34
XLETTERS = {'italic': 'acemnrsu', 'upright': 'acemnrsu', 'greek': 'αγεηκ'}
def guide(cls):
    """height of the upper guide line: capital height, or the class's x-height"""
    if cls not in XLETTERS: return 1000            # capital height (punctuation: as the digits)
    tops = sorted(-g['top'] for g in BASE.values() if g['cls'] == cls and g['char'] in XLETTERS[cls])
    return tops[len(tops) // 2] if len(tops) % 2 else (tops[len(tops) // 2 - 1] + tops[len(tops) // 2]) / 2

rows = []                                   # (class title or None, [keys])
for cls in CLASSES:
    keys = [k for k, v in G.items() if v['cls'] == cls]
    if not keys: continue
    n = -(-len(keys) // a.per_row); step = -(-len(keys) // n)          # balanced rows
    for i in range(0, len(keys), step):
        rows.append((f'{cls} ({len(keys)})' if i == 0 else None, keys[i:i + step], cls))

def row_width(keys):
    return sum(G[k]['width'] + GAP for k in keys) - GAP
W = int(2 * MARGIN + max(row_width(k) for _, k, _ in rows) * S + 2 * GAP * S)
out, y = [], MARGIN
for title, keys, cls in rows:
    if title:
        out.append(f'<text x="{MARGIN}" y="{y + 22}" font-family="DejaVu Sans, sans-serif" font-size="20" font-weight="bold" fill="#333">{title}</text>')
        y += TITLE_H
    base = y + ABOVE * S
    x0, x1 = MARGIN, W - MARGIN
    for yy in (base, base - guide(cls) * S):
        out.append(f'<line x1="{x0}" y1="{yy:.1f}" x2="{x1}" y2="{yy:.1f}" stroke="#3a7bd5" stroke-width="1"/>')
    x = MARGIN + GAP * S
    for k in keys:
        g = G[k]
        out.append(f'<path transform="translate({x:.1f},{base:.1f}) scale({S})" d="{g["d"]}" fill="#111" fill-rule="evenodd"/>')
        cx = x + g['width'] * S / 2
        out.append(f'<text x="{cx:.1f}" y="{base + BELOW * S + 18:.1f}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" '
                   f'font-size="13" fill="#666">{k}</text>')
        x += (g['width'] + GAP) * S
    y = base + BELOW * S + LABEL_H + 10
H = int(y + MARGIN)
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
       f'<rect width="100%" height="100%" fill="#fff"/>' + ''.join(out) + '</svg>')
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
Path(a.out).write_text(svg, encoding='utf-8')
print('wrote', a.out, W, 'x', H)
try:
    import cairosvg
    png = a.out[:-4] + '.png'; cairosvg.svg2png(bytestring=svg.encode(), write_to=png); print('wrote', png)
except ImportError:
    pass
