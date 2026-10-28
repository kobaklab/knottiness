"""Review sheets: one image per plate row.

Rows of the sheet: for each source, the knot's full cell (knot + its labels) from that scan with the
trace overlaid in red; at the bottom, the accepted trace rendered in its cell together with the
annotations typeset from data/census.csv (tenfold: type number or '–', Kirkman label, region letters;
Plate XLIV: group header, order and Kirkman label, Tait's former designation, and the partition pair
from the text), so both the geometry and the transcribed labels can be checked against the scans."""
import io, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from . import FONTS_DIR
from .sources import load_gray, priority, PLATES, S
from .census import plate_forms
from .render import densify, svg

FONT_DIR = '/usr/share/fonts/truetype/dejavu/'
H = 300                                     # height of each cell on the sheet (px)
FALLBACK_FONT = FONTS_DIR / 'RobotoSerif-Latin[GRAD,opsz,wdth,wght].ttf'   # bundled: used where DejaVu is not installed

def font(style, size):
    """font for review sheets and contact sheets: DejaVu Serif where installed (Linux), else the bundled
    Roboto Serif (macOS, Windows); italic and bold fall back to the upright face"""
    name = {'roman': 'DejaVuSerif.ttf', 'italic': 'DejaVuSerif-Italic.ttf', 'bold': 'DejaVuSerif-Bold.ttf'}[style]
    for path in (FONT_DIR + name, str(FALLBACK_FONT)):
        try: return ImageFont.truetype(path, int(size))
        except OSError: pass
    return ImageFont.load_default()

def letter_style(ch, family):
    """as printed: capitals upright; Greek italic; Latin italic in 5/7, upright in 4/8 and 3/9"""
    if ch.isupper(): return 'roman'
    if ord(ch) > 0x370: return 'italic'
    return 'italic' if family == '5/7' else 'roman'

def kirkman_parts(k):
    """'B28' -> ('B', '28')"""
    i = 0
    while i < len(k) and not k[i].isdigit(): i += 1
    return k[:i], k[i:]

def annotate(im, form, box, scale_px):
    """draw Tait's four annotations around the knot box (in image coordinates)"""
    d = ImageDraw.Draw(im); ink = (26, 26, 26)
    x0, y0, x1, y1 = box; fs = 0.11 * scale_px
    y0 = max(y0, 0.13 * scale_px); y1 = min(y1, im.height - 0.09 * scale_px)   # keep labels inside the cell
    big, small = font('roman', fs), font('roman', fs * 0.62)
    # top left: type number on the first form of a type, a dash on the others
    d.text((x0, y0 + 0.01 * scale_px), str(form['type']) if form['form'] == 1 else '–', font=big, fill=ink, anchor='ls')
    # top right: Kirkman's designation, letter with superscript number
    k = form.get('kirkman', '')
    if k:
        letter, num = kirkman_parts(k)
        wn = d.textlength(num, font=small)
        d.text((x1 - wn, y0 + 0.01 * scale_px), letter, font=big, fill=ink, anchor='rs')
        d.text((x1, y0 + 0.01 * scale_px - fs * 0.45), num, font=small, fill=ink, anchor='rs')
    elif 'no Kirkman label' not in form.get('notes', ''):      # not transcribed yet
        d.text((x1, y0 + 0.01 * scale_px), '?', font=big, fill=(200, 60, 60), anchor='rs')
    # bottom: region letters (a single barred letter for an amphicheiral)
    code = form['code']; fam = form['family']; yb = y1 + 0.07 * scale_px
    letters = list(code.rstrip('*'))
    f0 = font(letter_style(letters[0], fam), fs)
    d.text((x0, yb), letters[0], font=f0, fill=ink, anchor='ls')
    if code.endswith('*'):
        bb = d.textbbox((x0, yb), letters[0], font=f0, anchor='ls')
        d.line([(bb[0], bb[1] - 0.025 * scale_px), (bb[2], bb[1] - 0.025 * scale_px)], fill=ink, width=max(2, int(fs / 14)))
    else:
        d.text((x1, yb), letters[1], font=font(letter_style(letters[1], fam), fs), fill=ink, anchor='rs')

def annotate_xliv(im, form, box, scale_px):
    """Plate XLIV: header above the group's first figure; under the knot the former designation and
    'order Kirkman' as on the plate, and below that (not on the plate) Tait's partition pair"""
    d = ImageDraw.Draw(im); ink = (26, 26, 26)
    x0, y0, x1, y1 = box; fs = 0.11 * scale_px; xm = (x0 + x1) / 2
    y0 = max(y0, 0.13 * scale_px); y1 = min(y1, im.height - 0.2 * scale_px)
    if form['header']: d.text((x0, y0 - 0.02 * scale_px), form['header'], font=font('roman', fs * 0.8), fill=ink, anchor='ls')
    label = (form['former'] + (', ' if form['former'][:1].isupper() else ' ') if form['former'] else '') + f"{form['order']} {form['kirkman']}"
    d.text((xm, y1 + 0.11 * scale_px), label, font=font('roman', fs), fill=ink, anchor='ms')
    d.text((xm, y1 + 0.2 * scale_px), form['partitions'].replace('*', ' (bar)'), font=font('roman', fs * 0.65), fill=(40, 90, 200), anchor='ms')

def _cell_image(gray, rec):
    """the knot's cell from one scan, at working scale, with the trace overlaid"""
    cy0, cy1, cx0, cx1 = rec['cell']; f = rec['scale']
    cy0, cx0 = max(0, cy0), max(0, cx0); cy1, cx1 = min(gray.shape[0], cy1), min(gray.shape[1], cx1)
    sub = gray[cy0:cy1, cx0:cx1]
    im = Image.fromarray(sub.clip(0, 255).astype('uint8')).resize((max(1, int(sub.shape[1] * f)), max(1, int(sub.shape[0] * f))))
    im = Image.blend(im.convert('RGB'), Image.new('RGB', im.size, 'white'), 0.3)
    d = ImageDraw.Draw(im)
    if 'curve' in rec:
        C = densify(rec['curve'], 2.0)
        P = (C / f + np.array(rec['crop_origin']) - [cx0, cy0]) * f
        P = [tuple(p) for p in P]; d.line(P + [P[0]], fill=(220, 30, 30), width=3)
    tag = 'FAIL: ' + '; '.join(rec['problems'])[:70] if not rec['ok'] else ('warning' if rec.get('warnings') else '')
    if tag: d.text((6, 6), tag, fill=(220, 0, 0) if not rec['ok'] else (230, 120, 0), font=font('roman', 14))
    return im

def _rendered_cell(rec, form):
    """accepted trace rendered in its cell, with the typeset annotations"""
    cy0, cy1, cx0, cx1 = rec['cell']; f = rec['scale']
    W, Hc = int((cx1 - cx0) * f), int((cy1 - cy0) * f)
    ox, oy = (cx0 - rec['crop_origin'][0]) * f, (cy0 - rec['crop_origin'][1]) * f
    import cairosvg
    s, _ = svg(np.array(rec['curve']), W, Hc, offset=(ox, oy), stroke=5)
    im = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=s.encode()))).convert('RGB')
    by0, by1, bx0, bx1 = rec['box']
    box = ((bx0 - cx0) * f, (by0 - cy0) * f, (bx1 - cx0) * f, (by1 - cy0) * f)
    (annotate if 'code' in form else annotate_xliv)(im, form, box, S)
    return im

def make_sheets(plate, rows=None, sources=None):
    sources = sources or priority(plate)
    TRACED_DIR, OUTPUT_DIR = PLATES[plate].traced, PLATES[plate].output
    forms = {f['seq']: f for f in plate_forms(plate)}
    rows = rows or sorted({f['row'] for f in forms.values() if f['row']})
    grays = {}
    out_dir = OUTPUT_DIR / 'review'; out_dir.mkdir(parents=True, exist_ok=True)
    labels = sources + ['rendered + census']
    for r in rows:
        seqs = sorted((f['seq'] for f in forms.values() if f['row'] == r), key=lambda q: forms[q]['col'])
        cols = []
        for seq in seqs:
            cells = []
            for s in sources:
                p = TRACED_DIR / 'candidates' / f'{seq:03d}_{s}.json'
                if p.exists():
                    if s not in grays: grays[s] = load_gray(s, plate)
                    cells.append(_cell_image(grays[s], json.load(open(p))))
                else:
                    cells.append(Image.new('RGB', (200, H), 'white'))
            acc = TRACED_DIR / f'{seq:03d}.json'
            cells.append(_rendered_cell(json.load(open(acc)), forms[seq]) if acc.exists()
                         else Image.new('RGB', (200, H), (255, 230, 230)))
            cols.append((seq, [c.resize((max(1, int(c.width * H / c.height)), H)) for c in cells]))
        W = [max(c.width for c in cells) for _, cells in cols]
        sheet = Image.new('RGB', (150 + sum(W) + 8 * len(W), 34 + len(labels) * (H + 8)), 'white')
        d = ImageDraw.Draw(sheet); x = 150; fnt = font('roman', 18)
        for (seq, cells), w in zip(cols, W):
            d.text((x + 4, 6), f'#{seq}', fill='black', font=fnt)
            for i, c in enumerate(cells): sheet.paste(c, (x, 34 + i * (H + 8)))
            x += w + 8
        for i, l in enumerate(labels): d.text((6, 34 + i * (H + 8) + H // 2), l, fill='black', font=fnt)
        sheet.quantize(colors=64, method=Image.Quantize.MEDIANCUT).save(out_dir / f'{plate}_row{r:02d}.png', optimize=True)
