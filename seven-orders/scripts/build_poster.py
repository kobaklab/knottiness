"""Assemble the poster of Plate XLIV, 'The first seven orders of knottiness', on an A3 portrait page:
the companion of the tenfold poster's single-plate pages (same page, margins, header and footer).

  uv run scripts/build_poster.py                 (from inside seven-orders/)

Writes output/seven_orders_knottiness[_white].svg/.pdf/.png (paper tone / white; PNG 1250 px wide, the
density of the tenfold pages). The layout is proportional, so prints at other A sizes are scaled.

Reads data/census.csv, traced/<seq>.json (geometry and each knot's place on the scan) and
output/knots/<seq>.svg (the rendered knots: run ../scripts/render_knots.py first).

Layout: Tait's, spread over the page. One scale for the whole plate (the reference scan, the Cambridge
PDF), so the knots keep their relative sizes. Horizontally, every row but the last is justified: its
first and last knots at the margins, the gaps between its knots all widened by the same factor, so
Tait's rhythm of the figures and groups is kept (the double bars between the orders, found on the scan,
keep their places within their gaps); the shorter last row keeps the plate's spacing, centred,
with extra room between single neighbours where their headers would nearly touch (EXTRA_GAP). Vertically, the rows are spread over the page: the first row's ink (headers or knots) as far
below the header band as on the tenfold poster, the last row's ink (labels or knots) as far above the
footer band, and the rows equally spaced in between (row = the median centre of its knots).
Group headers stand over their first figure, labels are centred under each figure, both on a common
line per row (the labels' baseline as low as the lowest-hanging figure of the row requires). A label
with a former designation (6- and 7-folds: 'β  6A', 'II,  7C') spans its figure as on the plate: the
designation starts and the order and letter end where the plate's label does (measured on the scan). Labels: the former paper's designation (β γ δ for the 6-folds, Roman numerals for the
7-folds), the order and Kirkman's designation, as printed. The labels are set in the tenfold poster's
traced glyphs (../tenfold/traced/glyphs.json) plus the letters and the comma it lacks, traced from this
plate (traced/glyphs.json, scripts/trace_glyphs.py); the group headers in Roboto Serif."""
import argparse, json, re
from collections import defaultdict
import numpy as np
from scipy import ndimage
from shapely.geometry import LineString, box
from shapely.affinity import affine_transform
from tait import SEVEN_ORDERS as P, TENFOLD
from tait import poster as tp
from tait.poster import Label, INK, SUP_SIZE, SUP_RISE, CAP_EM
from tait.census import load
from tait.render import densify
from tait.sources import load_gray, config

ap = argparse.ArgumentParser()
ap.add_argument('--png-width', type=int, default=1250)
ap.add_argument('--gap', type=float, default=None,
                help='gap margin of the paper-tone knots in stroke widths (default: the committed knots, 1.1)')
ap.add_argument('--white-gap', type=float, default=2.0,
                help='gap margin of the knots in the _white files, in stroke widths: wider, so that the gaps survive ink bleeding '
                     'in home printing (default 2.0; rendered on first use, cached in output/knots/gap<value>/)')
ap.add_argument('--check-only', action='store_true', help='only report spacing, write nothing')
a = ap.parse_args()

# ---------------------------------------------------------------- page: as one page of the tenfold poster
PAGE_W, PAGE_H = 297, 420                                  # A3 portrait (mm)
# On the tenfold sheet (A2 landscape, 594 x 420) each plate is (594 - 2 x side margin - gutter) / 2 wide;
# a single-plate page is half the sheet, centred on its plate, so its side margins are (297 - plate) / 2.
PLATE_W = (594 - 2 * 0.028 * 594 - 0.040 * 594) / 2         # 268.5 mm
MARGIN_X, MARGIN_Y = (PAGE_W - PLATE_W) / 2, 0.040 * 420     # as on the tenfold pages: 14.3 mm, 16.8 mm
# The footer's text hangs down from the top of its band while the header is centred in its band, which left
# 20.9 mm of white above the title and 12.35 mm below the footer (the address aside). The content is moved
# up by half the difference, so that both are 16.6 mm.
MARGIN_TOP, MARGIN_BOTTOM = MARGIN_Y - 4.28, MARGIN_Y + 4.28      # (as on the tenfold pages)
HEADER, FOOTER = 0.040 * 420, 0.024 * 420
# text sizes of the tenfold pages: their label size fs = 0.15 x knot height, knot height = 0.72 x row
# pitch over 14 rows; header 1.45 fs, title 1.45 x header, footer 0.95 x header
FS_TENFOLD = 0.150 * 0.72 * (420 - 2 * MARGIN_Y - HEADER - FOOTER) / 14
HS = 1.45 * FS_TENFOLD; FT = 0.95 * HS
TITLE_SCALE = 1.45            # title size relative to the header text, as on the tenfold poster; the long
                              # title fits by the plate's own, tighter spacing (style 'title-xliv')
URL, URL_SCALE, URL_OPACITY = 'github.com/kobaklab/knottiness', 1.0, 0.3
# right-hand credit, as on the tenfold poster. The plate prints no year (only 'F. Huth, Lith' Edin''); MDCCCLXXXIV
# is that of the paper (Trans. RSE 32, Part II, read on 2 June 1884).
CREDIT = [[('F. Huth Lith', False), ('r', True), (' Edin', False), ('r', True), (' MDCCCLXXXIV', False)],
          [('D. Kobak Rest', False), ('r', True), (' Gent MMXXVI', False)]]
CREDIT_LEADING = 2.1

# gaps between the rows and the header / footer bands, as on the tenfold poster: its first row's labels
# 1.19 mm below the header band, its last row's labels 0.03 mm above the footer band (computed from its
# layout constants and the labels printed in those rows)
GAP_TOP, GAP_BOTTOM = 1.19, 0.03
# the last row (9 figures, centred): the plate's spacing (gaps x LAST_ROW_STRETCH), plus extra room between
# single neighbours: (row, column) -> extra gap after that figure, in label sizes. 9 Ip | 9 Ir: their
# headers XXXVIII and XXXIX Unique would nearly touch; with 1.4 they are 1.56 label sizes apart, like XXXIX and XL.
LAST_ROW_STRETCH = 1.0
EXTRA_GAP = {(12, 6): 1.4}

# ---------------------------------------------------------------- plate text, relative to the knot height
LABEL_SIZE = 0.144            # figure labels: capital height 0.105 knot heights, as measured on the plate
HEADER_TEXT = 0.135           # group headers: capital height ~0.1 knot heights, as measured
LABEL_CLEAR = 0.35            # minimum gap between a label or header and the figures (label sizes)
LABEL_DROP = 1.05             # label baseline below the lowest knot bottom of the row (label sizes)
HEADER_RISE = 0.45            # header baseline above the highest knot top of the row (label sizes)
ORDER_GAP = 0.28              # between the order digit and Kirkman's letters (label sizes)
FORMER_GAP = 0.55             # after the former designation (label sizes)
BAR_GAP = 4.0                 # between the two lines of an order separator (separator line widths)
SEP_WIDTH = 0.45              # separator line width relative to the knot lines

tp.use_glyphs(TENFOLD.traced / 'glyphs.json', P.traced / 'glyphs.json')   # the tenfold glyphs + XLIV's additions
census = load(P.data / 'census.csv')
recs = {f['seq']: json.load(open(P.traced / f"{f['seq']:03d}.json")) for f in census}
REF = recs[1]['ref_source']
f_ref = recs[1]['scale'] if recs[1]['source'] == REF else None
kh_ref = config(REF, 'XLIV')['knot_h']

# ---------------------------------------------------------------- the plate's geometry (reference scan px)
def place(rec):
    """(origin, scale): the knot's curve C (working px) lies at origin + C / scale on the reference scan"""
    if rec['source'] == REF: return np.array(rec['crop_origin'], float), rec['scale']
    # traced from another scan: centre its curve on the knot's box in the reference scan
    C = np.array(rec['curve']); f = 314.0 / kh_ref
    by0, by1, bx0, bx1 = rec['ref_box']
    return np.array([(bx0 + bx1) / 2, (by0 + by1) / 2]) - (C.min(0) + C.max(0)) / 2 / f, f
geo = {}
for f in census:
    rec = recs[f['seq']]; o, sc = place(rec); C = np.array(rec['curve'])
    lo, hi = o + C.min(0) / sc, o + C.max(0) / sc
    geo[f['seq']] = dict(o=o, sc=sc, lo=lo, hi=hi)
X0 = min(g['lo'][0] for g in geo.values()); X1 = max(g['hi'][0] for g in geo.values())
Y0 = min(g['lo'][1] for g in geo.values()); Y1 = max(g['hi'][1] for g in geo.values())
KH = float(np.median([g['hi'][1] - g['lo'][1] for g in geo.values()]))   # median knot height (ref px)
band_w = PAGE_W - 2 * MARGIN_X
band_top, band_bot = MARGIN_TOP + HEADER, PAGE_H - MARGIN_BOTTOM - FOOTER
s = band_w / (X1 - X0)                                     # mm per reference px: the plate's width fills the page's
ox = MARGIN_X - s * X0
ROWS = sorted({f['row'] for f in census})
ROW_Y = {r: float(np.median([(geo[f['seq']]['lo'][1] + geo[f['seq']]['hi'][1]) / 2 for f in census if f['row'] == r]))
         for r in ROWS}                                    # each row's centre on the reference scan
row_of = {f['seq']: f['row'] for f in census}
# horizontal map per row: reference x -> page x, piecewise linear. Knots keep scale s; the gaps between
# them are stretched by one factor per row so the row spans the page width (justified); the shorter last
# row is centred on the page (gaps x LAST_ROW_STRETCH, plus EXTRA_GAP).
XMAP = {}
for r in ROWS:
    ks = sorted((geo[f['seq']]['lo'][0], geo[f['seq']]['hi'][0]) for f in census if f['row'] == r)
    widths = sum(h - l for l, h in ks); gaps = sum(ks[i + 1][0] - ks[i][1] for i in range(len(ks) - 1))
    fs_ = LABEL_SIZE * s * KH                            # the label size (mm), as below
    extra = {c: EXTRA_GAP.get((r, c), 0) * fs_ for c in range(1, len(ks))}   # after the c-th figure
    if r == ROWS[-1]:                                    # the shorter last row: centred
        stretch = LAST_ROW_STRETCH; x = PAGE_W / 2 - (s * (widths + stretch * gaps) + sum(extra.values())) / 2
    else:
        stretch = (band_w - s * widths - sum(extra.values())) / (s * gaps); x = MARGIN_X
    xs, ps = [], []
    for i, (l, h) in enumerate(ks):
        if i: x += s * stretch * (l - ks[i - 1][1]) + extra[i]
        xs += [l, h]; ps += [x, x + s * (h - l)]; x += s * (h - l)
    XMAP[r] = (xs, ps)
def xmap(x, r):
    xs, ps = XMAP[r]
    if x <= xs[0]: return ps[0] + s * (x - xs[0])            # outside the row: scale s
    if x >= xs[-1]: return ps[-1] + s * (x - xs[-1])
    return float(np.interp(x, xs, ps))
yc = {r: band_top + (i + 0.5) * (band_bot - band_top) / len(ROWS) for i, r in enumerate(ROWS)}   # first guess
def to_page(xy, r):
    """reference-scan point of row r -> page (mm)"""
    return xmap(xy[0], r), yc[r] + s * (xy[1] - ROW_Y[r])
def knot_origin(g, r):
    """page position of a knot's crop origin: the knot moves rigidly with its left edge"""
    return xmap(g['lo'][0], r) + s * (g['o'][0] - g['lo'][0]), yc[r] + s * (g['o'][1] - ROW_Y[r])
knot_h = s * KH; fs = LABEL_SIZE * knot_h; hs_plate = HEADER_TEXT * knot_h

# ---------------------------------------------------------------- order separators, found on the scan
REF_INK = load_gray(REF, 'XLIV') < 128
def find_bars():
    g = REF_INK
    lab, n = ndimage.label(g); bars = []
    for sl in ndimage.find_objects(lab):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if h > 0.3 * kh_ref and w < 0.06 * kh_ref:  bars.append(((sl[1].start + sl[1].stop) / 2, sl[0].start, sl[0].stop))   # (a line may be broken in two)
    bars.sort(); pairs = []
    while bars:                                               # the two lines of a double bar
        b = bars.pop(0); j = next((i for i, c in enumerate(bars) if c[0] - b[0] < 0.1 * kh_ref and abs(c[1] - b[1]) < 0.5 * kh_ref), None)
        if j is not None: c = bars.pop(j); pairs.append(((b[0] + c[0]) / 2, min(b[1], c[1]), max(b[2], c[2])))
    return pairs
bars = find_bars()

def plate_label_span(seq):
    """left and right ink edges (reference px) of a figure's label on the plate: the band just below the
    knot, within its cell"""
    rec = recs[seq]; y0, y1, x0, x1 = rec['ref_box']; cy0, cy1, cx0, cx1 = rec['ref_cell']
    sub = REF_INK[y1 + 2:y1 + int(0.2 * kh_ref), max(0, cx0):cx1]
    lab, n = ndimage.label(sub, structure=np.ones((3, 3)))
    sl = [q for q in ndimage.find_objects(lab) if q[0].stop - q[0].start > 0.035 * kh_ref]
    return min(q[1].start for q in sl) + max(0, cx0), max(q[1].stop for q in sl) + max(0, cx0)

def header_label(txt, size):
    """a group header, with its superscripts as printed (Amphichˡ, 2ⁿᵈ, 3ʳᵈ)"""
    h = Label()
    for part in re.split(r'([ˡⁿᵈʳ]+)', txt):
        if not part: continue
        if part[0] in 'ˡⁿᵈʳ': h.add(part.translate(str.maketrans('ˡⁿᵈʳ', 'lndr')), SUP_SIZE * size, 'header-sup', rise=SUP_RISE * size)
        else: h.add(part, size, 'header')
    return h
MIN_GAP = 0.3 * fs

# ---------------------------------------------------------------- draw
STROKE = tp.knot_svg(P, 1)[1]
by_row = defaultdict(list)
for f in census: by_row[f['row']].append(f)
lw = SEP_WIDTH * STROKE * s / (314.0 / kh_ref)

narrowed = []
def draw():
    """the plate at the current row positions yc -> (svg pieces, knot outlines, text and bar boxes)"""
    out, knot_polys, items = [], [], []          # items: (kind, seq, shapely box) for the spacing report
    for r in sorted(by_row):
        row = sorted(by_row[r], key=lambda f: f['col'])
        tops = [to_page(geo[f['seq']]['lo'], r)[1] for f in row]; bots = [to_page(geo[f['seq']]['hi'], r)[1] for f in row]
        y_head = min(tops) - HEADER_RISE * fs; y_lab = max(bots) + LABEL_DROP * fs
        knot_polys_row, row_labels = [], []
        for f in row:                                            # the row's knot outlines first (for the headers)
            g = geo[f['seq']]; k = s / g['sc']; tx, ty = knot_origin(g, r)
            knot_polys_row.append((f['seq'], affine_transform(LineString(densify(np.array(recs[f['seq']]['curve']), 3.0))
                                                              .buffer(STROKE / 2), [k, 0, 0, k, tx, ty])))
        for f in row:
            seq = f['seq']; g = geo[seq]; path, stroke = tp.knot_svg(P, seq)
            k = s / g['sc']; tx, ty = knot_origin(g, r)
            out.append(f'<path id="knot-{seq:03d}" transform="translate({tx:.3f},{ty:.3f}) scale({k:.6f})" '
                       f'd="{path}" fill="{INK}" fill-rule="evenodd"/>')
            C = np.array(recs[seq]['curve'])
            poly = affine_transform(LineString(densify(C, 3.0)).buffer(stroke / 2), [k, 0, 0, k, tx, ty]); knot_polys.append((seq, poly))
            (x0, _), (x1, _) = to_page(g['lo'], r), to_page(g['hi'], r); xm = (x0 + x1) / 2
            # label under the figure: [former designation] order Kirkman. Without a former designation it is
            # centred under the figure; with one (6- and 7-folds) it spans the figure as on the plate: the
            # designation starting, the order and Kirkman's letter ending, where the plate's label does
            # (measured on the reference scan; the knot moves rigidly with its left edge)
            right = Label(glyphs=True).add(str(f['order']), fs).space(ORDER_GAP * fs).add(f['kirkman'], fs)
            if not f['former']:
                lab = right; lx0, _, lx1, _ = lab.bbox(); x_l = xm - (lx0 + lx1) / 2
            else:
                left = (Label(glyphs=True).add(f['former'] + ',', fs) if f['former'][0].isupper()
                        else Label(glyphs=True).add(f['former'], fs, 'italic'))
                px0, px1 = plate_label_span(seq)
                to_x = lambda px: xmap(g['lo'][0], r) + s * (px - g['lo'][0])
                x_l = to_x(px0) - left.bbox()[0]; x_r = to_x(px1) - right.bbox()[2]
                lab = Label(glyphs=True)
                for (t_, dx, dy, sz, st, off, gl) in left.pieces: lab.add(t_, sz, st, -dy, off, gl)
                lab.space(max(FORMER_GAP * fs, x_r - x_l - lab.adv))
                lab.add(str(f['order']), fs).space(ORDER_GAP * fs).add(f['kirkman'], fs)
            bx = lab.bbox(); yl = y_lab
            for _ in range(100):                                 # below a figure that hangs low: lower the label
                if box(x_l + bx[0], yl + bx[1], x_l + bx[2], yl + bx[3]).distance(poly) >= LABEL_CLEAR * fs: break
                yl += 0.03 * fs
            row_labels.append((seq, lab, x_l, bx, yl))
            if f['header']:
                # room: up to the next header in the row (as on the plate, a long header is set narrower)
                nxt = [to_page(geo[g2['seq']]['lo'], r)[0] for g2 in row if g2['header'] and g2['col'] > f['col']]
                room = (min(nxt) if nxt else PAGE_W - MARGIN_X) - x0 - MIN_GAP
                h = header_label(f['header'], hs_plate)
                if h.adv > room:
                    h = header_label(f['header'], hs_plate * max(0.7, room / h.adv)); narrowed.append((f['header'], h.pieces[0][3] / hs_plate))
                hb = h.bbox(); xh = x0 - hb[0]; yhd = y_head
                above = [b for kind, s2, b in items if kind == 'label' and b.bounds[1] < y_head]
                for _ in range(100):                             # over tall figures: raise it, below the labels above
                    hbox = box(xh + hb[0], yhd + hb[1], xh + hb[2], yhd + hb[3])
                    if all(hbox.distance(q) >= LABEL_CLEAR * fs for _, q in knot_polys_row): break
                    trial = box(xh + hb[0], yhd - 0.03 * fs + hb[1], xh + hb[2], yhd - 0.03 * fs + hb[3])
                    if any(trial.distance(b) < MIN_GAP for b in above): break
                    yhd -= 0.03 * fs
                out.append(h.svg(xh, yhd)); items.append(('header', seq, hbox))
        # the row's labels on one baseline: the lowest any of them needs (below a figure that hangs low)
        y_row = max(yl for *_, yl in row_labels)
        for seq, lab, x_l, bx, yl in row_labels:
            out.append(lab.svg(x_l, y_row))
            items.append(('label', seq, box(x_l + bx[0], y_row + bx[1], x_l + bx[2], y_row + bx[3])))
    # order separators
    for xb, yb0, yb1 in bars:
        rb = min(ROWS, key=lambda q: abs(ROW_Y[q] - (yb0 + yb1) / 2))
        (px, py0), (_, py1) = to_page((xb, yb0), rb), to_page((xb, yb1), rb)
        for dx in (-BAR_GAP * lw / 2, BAR_GAP * lw / 2):
            out.append(f'<line x1="{px + dx:.3f}" y1="{py0:.3f}" x2="{px + dx:.3f}" y2="{py1:.3f}" stroke="{INK}" stroke-width="{lw:.3f}"/>')
        items.append(('bar', 0, box(px - lw * 2, py0, px + lw * 2, py1)))

    return out, knot_polys, items

def extent(r, knot_polys, items):
    """top and bottom of the ink of row r (knots and text)"""
    bs = [q.bounds for s2, q in knot_polys if row_of[s2] == r] + [b.bounds for kind, s2, b in items if kind != 'bar' and row_of[s2] == r]
    return min(b[1] for b in bs), max(b[3] for b in bs)

# rows equally spaced, the first and last at the tenfold poster's distances from the header and footer
# bands (the text placement depends a little on the spacing: iterate)
for it in range(6):
    narrowed.clear(); out, knot_polys, items = draw()
    top1 = extent(ROWS[0], knot_polys, items)[0]; bot_n = extent(ROWS[-1], knot_polys, items)[1]
    a1, bn = yc[ROWS[0]] - top1, bot_n - yc[ROWS[-1]]
    y1, yn = band_top + GAP_TOP + a1, band_bot - GAP_BOTTOM - bn
    if abs(y1 - yc[ROWS[0]]) < 1e-3 and abs(yn - yc[ROWS[-1]]) < 1e-3: break
    yc = {r: y1 + i * (yn - y1) / (len(ROWS) - 1) for i, r in enumerate(ROWS)}
pitch = (yc[ROWS[-1]] - yc[ROWS[0]]) / (len(ROWS) - 1)

# ---------------------------------------------------------------- page header and footer
yh = MARGIN_TOP + 0.5 * HEADER; xl, xr = MARGIN_X, PAGE_W - MARGIN_X
out.append(Label().add('Trans. Roy. Soc. Edin', HS).add('r', SUP_SIZE * HS, 'sup', rise=SUP_RISE * HS).svg(xl, yh))
vol = Label().add('Vol. XXXII, Pl. XLIV.', HS); out.append(vol.svg(xr - vol.adv, yh))
ts = TITLE_SCALE * HS; title = Label().add('THE FIRST SEVEN ORDERS OF KNOTTINESS.', ts, 'title-xliv')
out.append(title.svg(PAGE_W / 2 - title.adv / 2, yh))
side = Label().add('Trans. Roy. Soc. Edin', HS).add('r', SUP_SIZE * HS, 'sup', rise=SUP_RISE * HS)
title_clear = min(PAGE_W / 2 - title.adv / 2 - (xl + side.bbox()[2]), (xr - vol.adv + vol.bbox()[0]) - (PAGE_W / 2 + title.adv / 2))
yf = PAGE_H - MARGIN_BOTTOM - 0.1 * FOOTER
out.append(Label().add('P. G. Tait del.', FT).svg(xl, yf))
url = Label().add(URL, URL_SCALE * FT); y_url = (yf + (len(CREDIT) - 1) * CREDIT_LEADING * CAP_EM * FT + PAGE_H) / 2 + 0.5 * CAP_EM * FT   # half-way between the last credit line and the page's edge
out.append(f'<g opacity="{URL_OPACITY}">{url.svg(PAGE_W / 2 - url.adv / 2, y_url)}</g>')
for i, line in enumerate(CREDIT):
    cred = Label()
    for t, sup in line: cred.add(t, SUP_SIZE * FT if sup else FT, 'sup' if sup else 'normal', rise=SUP_RISE * FT if sup else 0)
    out.append(cred.svg(xr - cred.adv, yf + i * CREDIT_LEADING * CAP_EM * FT))

# ---------------------------------------------------------------- spacing report
problems = []
for i, (kind, seq, b) in enumerate(items):
    if kind == 'bar': continue
    for s2, poly in knot_polys:
        d = b.distance(poly)
        if d < (0.15 * fs if s2 == seq else MIN_GAP): problems.append(f'{kind} of #{seq} close to knot #{s2} ({d / fs:.2f} fs)')
    for kind2, s2, b2 in items[i + 1:]:
        if b.distance(b2) < MIN_GAP: problems.append(f'{kind} of #{seq} close to {kind2} of #{s2}')
print(f'page A3 portrait: knot height {knot_h:.1f} mm, row pitch {pitch:.2f} mm, labels {fs:.2f} mm, '
      f'headers {hs_plate:.2f} mm, title {ts:.2f} mm ({title.adv:.1f} mm wide, {title_clear:.1f} mm clear of the '
      f'side texts); {len(bars)} order separators')
print(f'first row {extent(ROWS[0], knot_polys, items)[0] - band_top:.2f} mm below the header band, last row '
      f'{band_bot - extent(ROWS[-1], knot_polys, items)[1]:.2f} mm above the footer band')
print('headers set narrower to fit:', ', '.join(f'{h} ({k_:.2f})' for h, k_ in narrowed) or 'none')
print(f'text closer than {MIN_GAP / fs:.2f} label sizes to something else: {len(problems)}')
for p_ in problems: print('  ' + p_)
if a.check_only: raise SystemExit
if a.gap is not None: out = tp.swap_knot_paths(out, P, a.gap)
out_white = tp.swap_knot_paths(out, P, a.white_gap)               # the _white files: wider gaps
tp.write(P.output / 'seven_orders_knottiness', tp.defs() + '\n' + '\n'.join(out), 0.0, PAGE_W, PAGE_H, a.png_width,
         white_parts=tp.defs() + '\n' + '\n'.join(out_white))
print('  -> output/seven_orders_knottiness[_white] (.svg, .pdf, .png)')
