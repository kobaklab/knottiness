"""Assemble the poster: both plates side by side on an A2 landscape sheet, or each plate on its own
A3 portrait page (half the sheet).

  uv run scripts/build_poster.py                       # the sheet (default)
  uv run scripts/build_poster.py --plates separate     # the two pages
  uv run scripts/build_poster.py --bold 1.0 --sup-weight 0.62   # type numbers and superscripts as on the plates / plainly scaled

Writes, each as .svg, .pdf and .png (the sheet 2500 px wide, the pages at the same density):
  output/tenfold_knottiness[_white]             the sheet, on the paper tone / on white
  output/tenfold_knottiness_page1/2[_white]     each plate on its own page (complete footer)
The layout is proportional: every size is defined relative to the sheet, so prints at other sizes
are just scaled ("Fit to page"; e.g. the pages on A4 = the original's scale).

Reads data/census.csv (positions, type numbers, Kirkman labels, region codes, as corrected),
traced/<seq>.json (knot geometry) and output/knots/<seq>.svg (the rendered knots: run
../scripts/render_knots.py first; the stroke width is read from those files).

Layout per plate: 14 rows x 13 knots; a vertical separator wherever the type changes between
neighbouring knots of a row; each row justified to the plate width. Annotations at the four corners
of each knot, on common baselines per row, pushed outward until they clear the knot's outline.
The labels are set in Tait's own lettering, traced from the plates (traced/glyphs.json, see
scripts/trace_glyphs.py); header and footer in Barlow Semi Condensed and Roboto Serif (fonts/). All text is
positioned from the glyphs' and the fonts' own metrics, and drawn as outlines (renderer-independent)."""
import argparse, re
from collections import defaultdict
from shapely.geometry import LineString, box
from shapely.affinity import affine_transform
from tait import TENFOLD, poster as tp
from tait.poster import Label, INK, SUP_SIZE, SUP_RISE
from tait.codes import letter_style
from tait.layout import (SHEET_W as PAGE_W, PAGE_H, MARGIN_X, MARGIN_TOP, Y_GRID, MARGIN_BOTTOM, GUTTER, HEADER, FOOTER,
                         PLATE_W as plate_w, ROWS, ROW_H as row_h, KNOT_FILL, LABEL_SIZE, HEADER_SIZE, FOOTER_SCALE)
TRACED_DIR, OUTPUT_DIR = TENFOLD.traced, TENFOLD.output
from tait.census import load
from tait.render import densify
from tait.sources import S

ap = argparse.ArgumentParser()
ap.add_argument('--plates', default='together', choices=['together', 'separate'],
                help='both plates on one sheet (A2 landscape), or each plate on its own page (A3 portrait)')
ap.add_argument('--png-width', type=int, default=2500)
ap.add_argument('--gap', type=float, default=None,
                help='gap margin of the paper-tone knots in stroke widths (default: the committed knots, 1.1)')
ap.add_argument('--white-gap', type=float, default=2.0,
                help='gap margin of the knots in the _white files, in stroke widths: wider, so that the gaps survive ink bleeding '
                     'in home printing (default 2.0; rendered on first use, cached in output/knots/gap<value>/)')
ap.add_argument('--check-only', action='store_true', help='only report label spacing, write nothing')
for name, default in [('top_rise', 0.05), ('bottom_drop', 0.85), ('label_clear', 0.30), ('sep_weight', 0.30),
                      ('sep_len', 0.55), ('sup_weight', 0.85), ('bold', 1.4)]:
    ap.add_argument('--' + name.replace('_', '-'), type=float, default=default)
a = ap.parse_args()
# The layout (tait/layout.py) is made for the whole sheet, A2 landscape; each plate's page is half of it, A3 portrait.
# Everything is proportional to the sheet, so other sizes are just scaled prints of these files.

SEP_WEIGHT = a.sep_weight     # a separator slot is this fraction of a knot slot
SEP_LEN = a.sep_len           # separator length as a fraction of the row pitch
LABEL_CLEAR = a.label_clear   # minimum gap between a label and its knot, in label font sizes
TOP_RISE, BOTTOM_DROP = a.top_rise, a.bottom_drop   # label baselines rel. to the median knot's top / bottom (font sizes);
                              # chosen for the long descenders of the traced lowercase (β γ ζ η f g p q)
SUP_WEIGHT = a.sup_weight     # superscript stroke width as a fraction of the full-size glyphs' (scaling
                              # alone would give SUP_SIZE); the plates' superscripts are nearly full weight
BOLD = a.bold                 # stroke width of the type numbers relative to the other labels (1 = as on the plates)

tp.use_glyphs(TRACED_DIR / 'glyphs.json')


census = load()
plates = {p: [r for r in census if r['plate'] == p] for p in ('LXXX', 'LXXXI')}
k = KNOT_FILL * row_h / S                                 # mm per working pixel, the same for every knot
knot_h = S * k                                            # median knot height (mm)
fs = LABEL_SIZE * knot_h                                  # label font size (mm)

# ---------------------------------------------------------------- text helpers
def kirkman_label(lab):
    m = re.match(r'(\D+)(\d*)', lab)
    return (Label(glyphs=True).add(m.group(1), fs)
            .add(m.group(2), SUP_SIZE * fs, rise=SUP_RISE * fs, offset=SUP_OFFSET))

# superscripts: scaled down, their strokes would be SUP_SIZE as heavy; offset (in the superscript's own
# glyph units) to SUP_WEIGHT of the full-size stroke. Type numbers: BOLD x the normal stroke.
SUP_OFFSET = max(0.0, (SUP_WEIGHT / SUP_SIZE - 1) * tp.GLYPH_STROKE / 2)
BOLD_OFFSET = (BOLD - 1) * tp.GLYPH_STROKE / 2

# ---------------------------------------------------------------- knots
def knot_svg(seq): return tp.knot_svg(TENFOLD, seq)
def knot_curve(seq): return tp.knot_curve(TENFOLD, seq)

STROKE = knot_svg(1)[1]                    # knot line width (working px), as rendered
SEP_WIDTH = 0.45                           # separator line width relative to the knot lines

out, plate_groups = [], []                 # the body shared by all outputs (no paper, no footer); each
                                           # plate's slice of it
placed_labels, knot_polys, sep_lines, plate_centres = [], [], [], []   # for the spacing report
MIN_GAP = 0.35 * fs                        # wanted minimum gap between a label and anything else
def lbox(d):
    x0, y0, x1, y1 = d['lab'].bbox(); return box(d['ox'] + x0, d['yb'] + y0, d['ox'] + x1, d['yb'] + y1)

for pi, (plate, forms) in enumerate(plates.items()):
    x_plate = MARGIN_X + pi * (plate_w + GUTTER)
    plate_centres.append(x_plate + plate_w / 2)
    y_grid = Y_GRID
    group_start = len(out); out.append(f'<g id="plate-{plate}">')
    # ---- header and footer
    hs = HEADER_SIZE * fs; yh = MARGIN_TOP + 0.5 * HEADER
    head, _, _, _ = tp.page_header(x_plate, x_plate + plate_w, yh, hs, 'TENFOLD KNOTTINESS.', 'title', f'Vol. XXXII, Pl. {plate}.')
    out.extend(head)
    # ---- rows
    by_row = defaultdict(list)
    for f in forms: by_row[f['row']].append(f)
    for r in range(1, ROWS + 1):
        row = sorted(by_row[r], key=lambda f: f['col'])
        items = []
        for j, f in enumerate(row):
            if j > 0 and f['type'] != row[j - 1]['type']: items.append(('sep', None))
            items.append(('knot', f))
        n_sep = sum(1 for t, _ in items if t == 'sep')
        unit = plate_w / (len(row) + SEP_WEIGHT * n_sep)
        y_mid = y_grid + (r - 0.5) * row_h
        y_top = y_mid - knot_h / 2 + TOP_RISE * fs          # common baselines for the whole row
        y_bot = y_mid + knot_h / 2 + BOTTOM_DROP * fs
        x = x_plate; row_labels = []
        for kind, f in items:
            w = unit * (SEP_WEIGHT if kind == 'sep' else 1)
            if kind == 'sep':
                xs = x + w / 2
                sep_lines.append(box(xs, y_mid - SEP_LEN * row_h / 2, xs, y_mid + SEP_LEN * row_h / 2))
                out.append(f'<line x1="{xs:.3f}" y1="{y_mid - SEP_LEN * row_h / 2:.3f}" x2="{xs:.3f}" '
                           f'y2="{y_mid + SEP_LEN * row_h / 2:.3f}" stroke="{INK}" '
                           f'stroke-width="{SEP_WIDTH * STROKE * k:.3f}"/>')
                x += w; continue
            seq = f['seq']; path, stroke = knot_svg(seq)
            C = knot_curve(seq); (x0, y0), (x1, y1) = C.min(0), C.max(0)
            tx, ty = x + w / 2 - k * (x0 + x1) / 2, y_mid - k * (y0 + y1) / 2
            out.append(f'<path id="knot-{seq:03d}" transform="translate({tx:.3f},{ty:.3f}) scale({k:.6f})" '
                       f'd="{path}" fill="{INK}" fill-rule="evenodd"/>')
            # knot outline in poster coordinates, for label clearance
            poly = affine_transform(LineString(densify(C, 3.0)).buffer(stroke / 2), [k, 0, 0, k, tx, ty])
            knot_polys.append((seq, poly))
            bx0, bx1 = tx + k * x0, tx + k * x1
            # the four labels: (label, baseline, side)
            code = f['code']; letters = list(code.rstrip('*'))
            st = [letter_style(c, f['family']) for c in letters]
            # type number on the first form of each type only (Tait's '–' on the other forms is omitted)
            labels = [(Label(glyphs=True).add(str(f['type']), fs, offset=BOLD_OFFSET), y_top, 'left')] if f['form'] == 1 else []
            if f['kirkman']: labels.append((kirkman_label(f['kirkman']), y_top, 'right'))
            if code.endswith('*'):
                labels.append((Label(glyphs=True).add(letters[0], fs, st[0]).bar(fs), y_bot, 'left'))
            else:
                labels.append((Label(glyphs=True).add(letters[0], fs, st[0]), y_bot, 'left'))
                labels.append((Label(glyphs=True).add(letters[1], fs, st[1]), y_bot, 'right'))
            for lab, yb, side in labels:
                lx0, ly0, lx1, ly1 = lab.bbox()
                # start with the label's inner edge a little inside the knot's bounding box, then move
                # outward until it clears the knot by LABEL_CLEAR
                if side == 'left': ox = bx0 + 0.6 * fs - lx1
                else:              ox = bx1 - 0.6 * fs - lx0
                step = 0.04 * fs * (-1 if side == 'left' else 1)
                for _ in range(400):
                    if box(ox + lx0, yb + ly0, ox + lx1, yb + ly1).distance(poly) >= LABEL_CLEAR * fs: break
                    ox += step
                row_labels.append(dict(seq=seq, lab=lab, ox=ox, yb=yb, side=side, poly=poly))
            x += w
        # resolve crowding between neighbouring labels in this row: two labels that are too close each
        # move back towards their own knot (giving up some clearance, never touching it)
        for band in (y_top, y_bot):
            L_ = sorted([d for d in row_labels if d['yb'] == band], key=lambda d: d['ox'])
            for d1, d2 in zip(L_, L_[1:]):
                if d1['seq'] == d2['seq']: continue
                for _ in range(200):
                    b1, b2 = lbox(d1), lbox(d2)
                    if b1.distance(b2) >= MIN_GAP: break
                    moved = False
                    for d, sgn in ((d1, -1), (d2, +1)):       # d1 moves left, d2 moves right ...
                        inward = (sgn < 0) == (d['side'] == 'right')   # ... only if that is towards its own knot
                        if not inward: continue
                        trial = dict(d, ox=d['ox'] + sgn * 0.03 * fs)
                        if lbox(trial).distance(d['poly']) >= 0.12 * fs: d['ox'] = trial['ox']; moved = True
                    if not moved: break
        for d in row_labels:
            out.append(d['lab'].svg(d['ox'], d['yb'])); placed_labels.append((d['seq'], lbox(d)))
    out.append('</g>'); plate_groups.append((group_start, len(out)))

# ---------------------------------------------------------------- footers
# Tait's credit at the left, the project's address in the middle, the lithographer's and the restorer's
# credits at the right: across the whole sheet (Tait under the left plate, the credits under the right
# one, the address under the gutter), and complete under each plate on the separate pages.
ft = FOOTER_SCALE * HEADER_SIZE * fs; yf = PAGE_H - MARGIN_BOTTOM - 0.1 * FOOTER
plate_x = [(c - plate_w / 2, c + plate_w / 2) for c in plate_centres]
YEAR = 'MDCCCLXXXV'                      # 1885 in Roman numerals, like the volume and plate numbers
footer_sheet = tp.page_footer(plate_x[0][0], plate_x[-1][1], yf, ft, YEAR)
footer_pages = [tp.page_footer(x0, x1, yf, ft, YEAR) for x0, x1 in plate_x]
defs = tp.defs()   # the traced glyphs and font outlines, defined once and placed with <use>

# ---------------------------------------------------------------- spacing report
problems = []
for i, (seq, b) in enumerate(placed_labels):
    for s2, poly in knot_polys:
        if s2 != seq and b.distance(poly) < MIN_GAP: problems.append(f'label of #{seq} close to knot #{s2}')
    for line in sep_lines:
        if b.distance(line) < MIN_GAP: problems.append(f'label of #{seq} close to a separator')
    for s2, b2 in placed_labels[i + 1:]:
        if b.distance(b2) < MIN_GAP: problems.append(f'labels of #{seq} and #{s2} close')
for name, items in [('sheet', footer_sheet)] + [(f'page {i + 1}', f) for i, f in enumerate(footer_pages)]:
    for i, (_, b) in enumerate(items):        # footer (of each layout) against the labels, knots and itself
        if any(b.distance(b2) < MIN_GAP for _, b2 in placed_labels) or \
           any(b.distance(poly) < MIN_GAP for _, poly in knot_polys) or \
           any(b.distance(b2) < MIN_GAP for _, b2 in items[i + 1:]):
            problems.append(f'footer ({name}) close to something')
print(f'labels closer than {MIN_GAP / fs:.2f} font sizes to something else: {len(problems)}')
for p_ in problems: print('  ' + p_)
if a.check_only: raise SystemExit

# ---------------------------------------------------------------- outputs
# the whole sheet and each plate on its own page (half the sheet, portrait: A2 -> two A3 pages, A3 -> two
# A4), each on the paper tone and on white; SVG, PDF and PNG (the pages at the sheet's pixel density)
if a.gap is not None: out = tp.swap_knot_paths(out, TENFOLD, a.gap)
out_white = tp.swap_knot_paths(out, TENFOLD, a.white_gap)         # the _white files: wider gaps
body_of = lambda groups, lines=out: '\n'.join([defs] + [l for g0, g1 in groups for l in lines[g0:g1]])
hw = PAGE_W / 2
views = ([('tenfold_knottiness', 0.0, PAGE_W, plate_groups, footer_sheet, a.png_width)] if a.plates == 'together'
         else [(f'tenfold_knottiness_page{i + 1}', c - hw / 2, hw, [g], f, a.png_width // 2)
               for i, (c, g, f) in enumerate(zip(plate_centres, plate_groups, footer_pages))])
for name, vx, vw, groups, foot, px in views:
    foot_svg = '\n' + ''.join(svg for svg, _ in foot)
    tp.write(OUTPUT_DIR / name, body_of(groups) + foot_svg, vx, vw, PAGE_H, px, white_parts=body_of(groups, out_white) + foot_svg)
print(f'{"sheet A2 landscape" if a.plates == "together" else "pages A3 portrait"}: knot height {knot_h:.1f} mm, labels {fs:.2f} mm, '
      f'row pitch {row_h:.1f} mm\n  -> ' + ', '.join(f'output/{n}[_white]' for n, *_ in views) + ' (.svg, .pdf, .png)')
