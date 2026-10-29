"""Typesetting and output shared by the posters (tenfold/, seven-orders/): header and footer text in
outline fonts (fonts/), labels in Tait's traced lettering (a poster's traced/glyphs.json), labels with
ink bounding boxes, the SVG <defs> of every glyph used, and writing SVG, PDF and PNG.

All sizes are in mm on the poster. A text of size `size` has capital height CAP_EM * size, in any font
and in the traced glyphs (the sizes were first defined for a placeholder font, DejaVu Serif)."""
import json, re
import numpy as np
from . import FONTS_DIR, layout

INK, PAPER_TONE, WHITE = '#1a1a1a', '#f6f0dc', '#ffffff'
SUP_SIZE, SUP_RISE = 0.62, 0.42   # superscripts: size and rise, in font sizes

# Header and footer (lettered on the plates in imitation of type): free fonts close to it (fonts/, SIL OFL),
# drawn as outlines so the SVG and PDF look the same everywhere. 'title': the spaced sans-serif capitals;
# 'normal': the light condensed serif of the side texts and credits.
FONTS = {'title': ('BarlowSemiCondensed-Medium.ttf', {}),
         'title-xliv': ('BarlowSemiCondensed-Medium.ttf', {}),
         'normal': ('RobotoSerif-Latin[GRAD,opsz,wdth,wght].ttf', dict(wdth=55, wght=250, opsz=14, GRAD=0)),
         # superscripts: heavier, so that scaled down they come close to the text's stroke weight
         'sup': ('RobotoSerif-Latin[GRAD,opsz,wdth,wght].ttf', dict(wdth=55, wght=430, opsz=14, GRAD=0)),
         # Plate XLIV's group headers ("III Two forms"): as heavy as the traced label glyphs (stroke 0.097
         # capital heights); their superscripts heavier, so that scaled down they keep 0.85 of that weight
         'header': ('RobotoSerif-Latin[GRAD,opsz,wdth,wght].ttf', dict(wdth=55, wght=400, opsz=14, GRAD=0)),
         'header-sup': ('RobotoSerif-Latin[GRAD,opsz,wdth,wght].ttf', dict(wdth=55, wght=570, opsz=14, GRAD=0))}
SERIF_TRACK = 0.06            # extra letter-spacing of the serif texts, in capital heights (the plates space loosely)
# Title styles: (gap between the letters' ink, between the words), in capital heights, as measured:
# Plate LXXX spaces its short title widely; Plate XLIV sets its long title tighter.
TITLE_SPACING = {'title': (0.70, 2.10), 'title-xliv': (0.46, 1.23)}
# Sizes are given as before for the former placeholder font (DejaVu Serif): a text of size `size` has
# capital height CAP_EM * size, whatever the font, so the layout keeps its proportions.
CAP_EM = 0.729

class OutlineFont:
    def __init__(self, file, axes):
        from fontTools.ttLib import TTFont
        f = TTFont(FONTS_DIR / file)
        if axes:
            from fontTools.varLib.instancer import instantiateVariableFont
            f = instantiateVariableFont(f, axes)
        self.cmap, self.gs, self.hmtx = f.getBestCmap(), f.getGlyphSet(), f['hmtx']
        self.cap = self.bounds(self.cmap[ord('H')])[3]; self.cache = {}
    def bounds(self, g):
        from fontTools.pens.boundsPen import BoundsPen
        bp = BoundsPen(self.gs); self.gs[g].draw(bp); return bp.bounds
    def glyph(self, ch):
        """(glyph name, advance, ink bounds (x0, y0, x1, y1) y up or None, SVG path) in font units"""
        if ch not in self.cache:
            from fontTools.pens.svgPathPen import SVGPathPen
            g = self.cmap[ord(ch)]; pen = SVGPathPen(self.gs); self.gs[g].draw(pen)
            self.cache[ch] = (g, self.hmtx[g][0], self.bounds(g), pen.getCommands())
        return self.cache[ch]
_outline_fonts = {}
def outline_font(style):
    if style not in _outline_fonts: _outline_fonts[style] = OutlineFont(*FONTS[style])
    return _outline_fonts[style]

def _font_run(t, size, style):
    """[(char, x)], scale (mm per font unit), advance, ink box (x0, y0, x1, y1; y down) of a text in an
    outline font. The title is spaced by its ink (as hand-spaced capitals), the rest by the advances."""
    f = outline_font(style); cap = CAP_EM * size; s = cap / f.cap
    x, run, prev = 0.0, [], None
    for ch in t:
        g, adv, b, d = f.glyph(ch)
        if style in TITLE_SPACING:
            if ch == ' ': prev = ('space', prev[1] if prev else 0.0); continue
            if b is None: continue
            if prev is not None:                            # left ink edge after the previous ink + gap
                gap, word = TITLE_SPACING[style]
                x = prev[1] + (word if prev[0] == 'space' else gap) * cap - b[0] * s
            run.append((ch, x)); prev = ('ink', x + b[2] * s)
        else:
            run.append((ch, x)); x += adv * s + SERIF_TRACK * cap
    boxes = [(x + b[0] * s, -b[3] * s, x + b[2] * s, -b[1] * s) for ch, x in run for b in [f.glyph(ch)[2]] if b]
    ink = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    advance = prev[1] if style in TITLE_SPACING else x
    return run, s, advance, ink


# Tait's lettering for the labels: the traced glyphs (glyph units: 1000 = capital height, y down,
# baseline at 0, ink from x = 0). Their capital height is that of the placeholder font at the same
# size, so the labels keep their size and the layout its proportions.
GLYPHS, GLYPH_STROKE = {}, None     # set by use_glyphs()
def use_glyphs(*paths):
    """load traced glyph sets (traced/glyphs.json) for the labels set with glyphs=True; later sets add to
    (or replace glyphs of) the first, whose units and stroke width they must share"""
    global GLYPH_STROKE
    GLYPHS.clear(); GLYPH_STROKE = None
    for path in paths:
        data = json.load(open(path, encoding='utf-8'))
        if GLYPH_STROKE is None: GLYPH_STROKE = data['stroke_width']   # glyph units
        elif abs(data['stroke_width'] - GLYPH_STROKE) > 1e-6: raise ValueError(f'{path}: other stroke width')
        GLYPHS.update(data['glyphs'])
GLYPH_CAP = 1000 * CAP_EM    # glyph capital height per 1000 units of size
GLYPH_SPACE = 330             # a word space in a run of traced glyphs, in glyph units
GLYPH_GAP = 110               # space between the glyphs of a label, in glyph units
used_glyphs = {}              # (name, offset) -> id, for the <defs>

def glyph(name, offset=0.0):
    """a traced glyph, its outline offset by `offset` glyph units on every side (> 0: heavier), with its
    metrics; ink again from x = 0, the baseline kept"""
    key = (name, round(offset, 2))
    if key not in _variants:
        g = GLYPHS[name]
        if not offset: _variants[key] = g
        else:
            from tait.glyphs import path_to_geom, geom_to_path
            from shapely.affinity import translate
            geo = path_to_geom(g['d']).buffer(offset, join_style=2, mitre_limit=2.0)
            geo = translate(geo, -geo.bounds[0], 0); x0, y0, x1, y1 = geo.bounds
            _variants[key] = dict(d=geom_to_path(geo), width=x1 - x0, top=y0, bottom=y1)
    return _variants[key], key
_variants = {}

def glyph_name(ch, style):
    if ch.isdigit(): return f'digits/{ch}'
    if ch.isupper(): return f'capitals/{ch}'
    if ord(ch) > 0x370: return f'greek/{ch}'
    if not ch.isalpha(): return f'punct/{ch}'
    return f'{"italic" if style == "italic" else "upright"}/{ch}'


def _glyph_run(t, size, style, offset=0.0):
    """[(glyph, key, x offset)], scale, ink width (mm) of a run of traced glyphs"""
    s = GLYPH_CAP * size / 1e6; x, run = 0.0, []
    for ch in t:
        if ch == ' ': x += GLYPH_SPACE * s; continue           # word space (no glyph)
        g, key = glyph(glyph_name(ch, style), offset); run.append((g, key, x)); x += (g['width'] + GLYPH_GAP) * s
    return run, s, x - GLYPH_GAP * s

def width(t, size, style='normal', glyphs=False, offset=0.0):
    """advance: for traced glyphs the ink width plus one gap (the next piece follows at that distance)"""
    if glyphs: return _glyph_run(t, size, style, offset)[2] + GLYPH_GAP * GLYPH_CAP * size / 1e6
    return _font_run(t, size, style)[2]

def ink_box(t, size, style='normal', glyphs=False, offset=0.0):
    """ink bounding box of t relative to its origin on the baseline: (x0, y0, x1, y1), y down"""
    if glyphs:
        run, s, w = _glyph_run(t, size, style, offset)
        return (0.0, min(g['top'] for g, _, _ in run) * s, w, max(g['bottom'] for g, _, _ in run) * s)
    return _font_run(t, size, style)[3]

def svg_glyphs(x, y, t, size, style='normal', offset=0.0):
    run, s, _ = _glyph_run(t, size, style, offset); out = []
    for g, key, dx in run:
        gid = used_glyphs.setdefault(key, f'g{len(used_glyphs)}')
        out.append(f'<use xlink:href="#{gid}" transform="translate({x + dx:.3f},{y:.3f}) scale({s:.6f})"/>')
    return ''.join(out)

def svg_text(x, y, t, size, style='normal'):
    """text in an outline font, as <use> of glyph outlines defined once in <defs>"""
    run, s, _, _ = _font_run(t, size, style); f = outline_font(style); out = []
    for ch, dx in run:
        g, adv, b, d = f.glyph(ch)
        if not d: continue
        key = ('font', style, g); _variants.setdefault(key, dict(d=d))
        gid = used_glyphs.setdefault(key, f'g{len(used_glyphs)}')
        out.append(f'<use xlink:href="#{gid}" transform="translate({x + dx:.3f},{y:.3f}) scale({s:.6f},{-s:.6f})"/>')
    return ''.join(out)

class Label:
    """a label made of pieces (text, dx, dy, size, style) and optional bars, relative to an origin on
    the baseline; knows its ink bounding box and renders at any position. glyphs=True: set in the
    traced glyphs (the annotations), else in an outline font (header, footer: FONTS)"""
    def __init__(self, glyphs=False):
        self.pieces, self.bars, self.adv, self.g = [], [], 0.0, glyphs
    def add(self, t, size, style='normal', rise=0.0, offset=0.0, glyphs=None):
        """offset: for traced glyphs, extra weight in glyph units on every side of the outline;
        glyphs: this piece in the traced glyphs (True) or an outline font (False), default as the label"""
        g = self.g if glyphs is None else glyphs
        self.pieces.append((t, self.adv, -rise, size, style, offset, g))
        self.adv += width(t, size, style, g, offset); return self
    def raised(self, t, size, style, rise, stop=None):
        """a raised ending of an abbreviation (Edin^r, Amphich^l), and with stop=(size, style) the abbreviation's full stop on the
        baseline under it, as on the plates (the stop does not advance the label)"""
        x0 = self.adv; self.add(t, size, style, rise=rise)
        if stop:
            sx0, _, sx1, _ = ink_box(t, size, style, self.g, 0.0); px0, _, px1, _ = ink_box('.', stop[0], stop[1], self.g, 0.0)
            self.pieces.append(('.', x0 + (sx0 + sx1) / 2 - (px0 + px1) / 2, 0.0, stop[0], stop[1], 0.0, self.g))
        return self
    def space(self, w):
        """advance by w (mm)"""
        self.adv += w; return self
    def bar(self, size):                     # bar over the last piece (amphicheiral)
        t, dx, dy, sz, st, off, g = self.pieces[-1]; x0, y0, x1, y1 = ink_box(t, sz, st, g, off)
        yb = dy + y0 - 0.12 * size
        self.bars.append((dx + x0, dx + x1, yb, 0.06 * size)); return self
    def bbox(self):
        bs = [(dx + x0, dy + y0, dx + x1, dy + y1) for t, dx, dy, sz, st, off, g in self.pieces
              for x0, y0, x1, y1 in [ink_box(t, sz, st, g, off)]]
        bs += [(x0, yb - w, x1, yb + w) for x0, x1, yb, w in self.bars]
        return min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)
    def svg(self, x, y):
        out = [svg_glyphs(x + dx, y + dy, t, sz, st, off) if g else svg_text(x + dx, y + dy, t, sz, st)
               for t, dx, dy, sz, st, off, g in self.pieces]
        out += [f'<line x1="{x + x0:.3f}" y1="{y + yb:.3f}" x2="{x + x1:.3f}" y2="{y + yb:.3f}" '
                f'stroke="{INK}" stroke-width="{w:.3f}"/>' for x0, x1, yb, w in self.bars]
        return ''.join(out)


def defs():
    """the <defs> with every glyph and font outline used so far, each defined once and placed with <use>
    (font outlines use the nonzero rule they are designed for: a variable font's glyphs keep overlapping
    contours where strokes cross, which evenodd would punch out; the traced glyphs are evenodd)"""
    return ('<defs>' + ''.join(
        f'<path id="{gid}" d="{_variants[key]["d"]}" fill="{INK}" fill-rule="{"nonzero" if key[0] == "font" else "evenodd"}"/>'
        for key, gid in used_glyphs.items()) + '</defs>')

# ---------------------------------------------------------------- knots
DEFAULT_GAP = 1.1      # margin of the gaps in the rendered knots (output/knots/), in stroke widths

def knot_svg(poster, seq, gap=None):
    """(outline path, stroke width in working px) of a rendered knot. By default the committed rendering,
    <poster>/output/knots/<seq>.svg; with `gap` (margin on each side of an over-strand, in stroke widths;
    DEFAULT_GAP is the committed one) the knot rendered with that gap, cached in
    <poster>/output/knots/gap<gap>/<seq>.svg (about 2 s per knot the first time)."""
    path = poster.output / 'knots' / f'{seq:03d}.svg'
    s = open(path).read()
    m = re.search(r'stroke=([\d.]+)', s); stroke = float(m.group(1)) if m else 4.0
    if gap is not None and abs(gap - DEFAULT_GAP) > 1e-9:
        cache = poster.output / 'knots' / f'gap{gap:g}' / f'{seq:03d}.svg'
        want = f'<!-- stroke={stroke:g} margin={stroke * gap:g} -->'
        if not cache.exists() or want not in cache.read_text():
            from .render import svg as render_svg
            rec = json.load(open(poster.traced / f'{seq:03d}.json'))
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(render_svg(np.array(rec['curve']), *rec['crop_size'], stroke=stroke, gap=gap)[0])
        s = cache.read_text()
    return re.search(r'<path d="([^"]*)" fill="#1a1a1a"', s).group(1), stroke

def swap_knot_paths(lines, poster, gap):
    """the svg lines of a poster body with every knot (<path id="knot-NNN" ... d="...">) redrawn with `gap`"""
    def sub(m):
        return m.group(1) + knot_svg(poster, int(m.group(2)), gap)[0] + m.group(3)
    return [re.sub(r'(<path id="knot-(\d+)" [^>]*?d=")[^"]*(")', sub, l) if l.startswith('<path id="knot-') else l
            for l in lines]

def knot_curve(poster, seq):
    return np.array(json.load(open(poster.traced / f'{seq:03d}.json'))['curve'])

# ---------------------------------------------------------------- output
def write(stem, doc_parts, vx, vw, page_h, px, white_parts=None):
    """write <stem>.svg/.pdf/.png on the paper tone and <stem>_white.* on white: doc_parts = the
    content (the defs first), placed in a page of vw x page_h mm whose left edge is at x = vx;
    white_parts = the content of the white version where it differs (wider gaps in the knots)"""
    import cairosvg
    for tone, suffix, parts in ((PAPER_TONE, '', doc_parts), (WHITE, '_white', white_parts or doc_parts)):
        doc = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
               f'width="{vw:.3f}mm" height="{page_h}mm" viewBox="{vx:.3f} 0 {vw:.3f} {page_h}">\n'
               f'<rect x="{vx:.3f}" width="{vw:.3f}" height="{page_h}" fill="{tone}"/>\n'
               + parts + '\n</svg>')
        s = stem.parent / (stem.name + suffix)
        s.with_suffix('.svg').write_text(doc, encoding='utf-8')
        cairosvg.svg2pdf(bytestring=doc.encode(), write_to=str(s.with_suffix('.pdf')))
        cairosvg.svg2png(bytestring=doc.encode(), write_to=str(s.with_suffix('.png')), output_width=px)


# ---------------------------------------------------------------- page header and footer (both posters)
def page_header(x0, x1, yh, hs, title, title_style, vol):
    """the header of a page between x0 and x1, on the baseline yh, text size hs: 'Trans. Roy. Soc. Edin^r' at
    the left, the title centred, `vol` at the right -> ([svg of each], side-text label, title label, vol label)"""
    side = Label().add('Trans. Roy. Soc. Edin', hs).raised('r', SUP_SIZE * hs, 'sup', SUP_RISE * hs, stop=(hs, 'normal'))
    t = Label().add(title, layout.TITLE_SCALE * hs, title_style)
    v = Label().add(vol, hs)
    return [side.svg(x0, yh), t.svg((x0 + x1) / 2 - t.adv / 2, yh), v.svg(x1 - v.adv, yh)], side, t, v

def credit_lines(year):
    """the right-hand credit: (text, superscript?) pieces of the lithographer's and the restorer's lines"""
    return [[('F. Huth Lith', False), ('r', True), (' Edin', False), ('r', True), (f' {year}', False)],
            [('D. Kobak Rest', False), ('r', True), (' Ghent MMXXVI', False)]]

def page_footer(x0, x1, yf, ft, year):
    """the footer between x0 and x1, text size ft, first baseline yf: Tait's credit at the left, the project's
    address centred below, the two credit lines at the right (`year` in Roman numerals, that of the paper)
    -> [(svg, ink box)]"""
    from shapely.geometry import box
    items = []
    def put(lab, x, y, wrap='{}'):
        items.append((wrap.format(lab.svg(x, y)), box(*(v + o for v, o in zip(lab.bbox(), (x, y) * 2)))))
    lines = credit_lines(year)
    put(Label().add('P. G. Tait del.', ft), x0, yf)
    url = Label().add(layout.URL, layout.URL_SCALE * ft)
    # the address: half-way between the last credit line and the page's edge
    y_url = (yf + (len(lines) - 1) * layout.CREDIT_LEADING * CAP_EM * ft + layout.PAGE_H) / 2 + 0.5 * CAP_EM * ft
    put(url, (x0 + x1) / 2 - url.adv / 2, y_url, f'<g opacity="{layout.URL_OPACITY}">{{}}</g>')
    for i, line in enumerate(lines):
        cred = Label()
        for t, sup in line:
            if sup: cred.raised(t, SUP_SIZE * ft, 'sup', SUP_RISE * ft, stop=(ft, 'normal'))
            else: cred.add(t, ft, 'normal')
        put(cred, x1 - cred.adv, yf + i * layout.CREDIT_LEADING * CAP_EM * ft)
    return items
