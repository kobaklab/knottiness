"""The figures of docs/making-of.md, made from the repository's own data (docs/making-of-*.png).

  uv run scripts/make_making_of_images.py

Needs the tenfold scans (tenfold/sources/), the traces and glyphs, and the glyph instances collected from the
scans (tenfold/output/glyphs/collected.pkl, made by tenfold/scripts/trace_glyphs.py; collected again, about 3 minutes,
if missing)."""
import io, json, pickle
import numpy as np
import cairosvg
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage.morphology import skeletonize
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union, polygonize
from tait import ROOT, TENFOLD
from tait.census import load
from tait.codes import partitions
from tait.glyphs import combine, ink, collect, path_to_geom, load_choices
from tait.render import densify, svg
from tait.review import _cell_image, font
from tait.sources import load_gray, find_knots, knot_crop
from tait.trace import trace, isolate_knot

DOCS = ROOT / 'docs'; DOCS.mkdir(exist_ok=True)
PAPER, INK = (246, 240, 220), (26, 26, 26)
census = {r['seq']: r for r in load(TENFOLD.data / 'census.csv')}
rec_of = lambda seq: json.load(open(TENFOLD.traced / f'{seq:03d}.json'))

def save(im, name, colors=64):
    im.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(DOCS / name, optimize=True)
    print('wrote docs/' + name, im.size)

def to_height(im, h): return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)

def strip(ims, gap=0, bg='white'):
    sheet = Image.new('RGB', (sum(i.width for i in ims) + gap * (len(ims) - 1), max(i.height for i in ims)), bg); x = 0
    for i in ims: sheet.paste(i, (x, 0)); x += i.width + gap
    return sheet

def stack(ims, gap=0, bg='white'):
    sheet = Image.new('RGB', (max(i.width for i in ims), sum(i.height for i in ims) + gap * (len(ims) - 1)), bg); y = 0
    for i in ims: sheet.paste(i, (0, y)); y += i.height + gap
    return sheet

def titled(im, title, h=26):
    out = Image.new('RGB', (im.width, im.height + h), 'white'); out.paste(im, (0, h))
    ImageDraw.Draw(out).text((6, 5), title, fill=(60, 60, 60), font=font('roman', 15)); return out

def render_knot(curve, size, stroke=6.5, gap=None, bg=PAPER):
    s, _ = svg(curve, *size, stroke=stroke, gap=gap)
    p = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=s.encode()))).convert('RGBA')
    c = Image.new('RGBA', p.size, bg + (255,)); c.alpha_composite(p); return c.convert('RGB')

# ------------------------------------------------------------------ 1. the traces over the scan
def fig_overlay():
    g = load_gray('HT', 'LXXX')
    cells = [to_height(_cell_image(g, rec_of(s)), 300) for s in range(80, 86)]   # row 7 of Plate LXXX, without its first column
    save(strip(cells), 'making-of-1-overlay.png')

# ------------------------------------------------------------------ 2. from ink to curve
def fig_stages(seqs=(82, 84)):
    g, rows = find_knots('HT', 'LXXX'); rows_im = []
    for seq in seqs:
        rec = rec_of(seq); gg, mask, _ = knot_crop('HT', g, rows[rec['row'] - 1][rec['col'] - 1], plate='LXXX')
        iso = isolate_knot(mask); sk = skeletonize(iso); report, G, curve = trace(mask, census[seq]['code'])
        H, W = gg.shape
        scan = Image.fromarray(gg.clip(0, 255).astype('uint8')).convert('RGB')
        ink_im = Image.fromarray(np.where(iso, 30, 255).astype('uint8')).convert('RGB')
        a = np.full((H, W, 3), 255, 'uint8'); a[ndimage.binary_dilation(iso)] = (225, 225, 225); a[sk] = (200, 30, 30)
        graph = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(graph)
        for e in G.edges.values(): d.line([tuple(p) for p in e['pts']], fill=(40, 90, 200), width=2)
        for x, y in G.nodes.values(): d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(220, 40, 40))
        over = Image.blend(scan, Image.new('RGB', scan.size, 'white'), .5); d = ImageDraw.Draw(over)
        P = [tuple(q) for q in curve]; d.line(P + [P[0]], fill=(220, 30, 30), width=3)
        rows_im.append([to_height(i, 300) for i in (scan, ink_im, Image.fromarray(a), graph, over, render_knot(curve, (W, H)))])
    titles = ['1  scan', '2  ink', '3  skeleton', '4  cleaned graph, crossings', '5  smooth curve', '6  rendered']
    widths = [max(r[k].width for r in rows_im) for k in range(6)]                 # one width per column, so the rows line up
    def aligned(r):
        out = Image.new('RGB', (sum(widths), 300), 'white'); x = 0
        for k, w in enumerate(widths): out.paste(r[k], (x + (w - r[k].width) // 2, 0)); x += w
        return out
    head = Image.new('RGB', (sum(widths), 26), 'white'); d = ImageDraw.Draw(head); x = 0
    for k, w in enumerate(widths): d.text((x + 6, 5), titles[k], fill=(60, 60, 60), font=font('roman', 15)); x += w
    save(stack([head, aligned(rows_im[0]), aligned(rows_im[1])], gap=6), 'making-of-2-stages.png')

# ------------------------------------------------------------------ 3. regions and Tait's code
def regions(rec):
    C = densify(np.array(rec['curve']), 1.0)
    faces = list(polygonize(unary_union(LineString(np.vstack([C, C[:1]])))))
    xs = np.array([[c[0], c[1]] for c in rec['crossings']]); whole = unary_union(faces); b = whole.bounds
    outer = box(b[0] - 60, b[1] - 60, b[2] + 60, b[3] + 60).difference(whole); allf = faces + [outer]
    corners = [sum(1 for x, y in xs if (f.boundary if f is not outer else whole.boundary).distance(Point(x, y)) < 2.5) for f in allf]
    adj = {i: {j for j in range(len(allf)) if j != i and allf[i].boundary.intersection(allf[j].boundary).length > 3} for i in range(len(allf))}
    col = {len(allf) - 1: 0}; todo = [len(allf) - 1]
    while todo:                                           # checkerboard colouring: neighbours across an edge differ
        i = todo.pop()
        for j in adj[i]:
            if j not in col: col[j] = 1 - col[i]; todo.append(j)
    return allf, corners, col, len(faces)

def fig_regions(seqs=(1, 82, 84)):
    tints = [(200, 220, 245), (250, 218, 190)]; panels = []
    for seq in seqs:
        rec = rec_of(seq); allf, cn, col, nf = regions(rec); W, H = rec['crop_size']
        classes = sorted(tuple(sorted([c for i, c in enumerate(cn) if col[i] == k], reverse=True)) for k in (0, 1))
        assert classes == partitions(census[seq]['code']), seq     # the corner counts are Tait's printed code
        im = Image.new('RGB', (W, H), tints[col[nf]]); d = ImageDraw.Draw(im)
        for i, f in enumerate(allf[:nf]):
            polys = getattr(f, 'geoms', [f])
            for p in polys: d.polygon(list(p.exterior.coords), fill=tints[col[i]])
        C = densify(np.array(rec['curve']), 1.0); P = [tuple(q) for q in C]; d.line(P + [P[0]], fill=INK, width=4)
        for i, f in enumerate(allf[:nf]):
            c = f.representative_point(); d.text((c.x - 6, c.y - 9), str(cn[i]), fill=(20, 20, 20), font=font('bold', 22))
        d.text((8, 6), f"outer region: {cn[nf]}", fill=(20, 20, 20), font=font('roman', 17))
        p = to_height(im, 240)
        d = ImageDraw.Draw(p); d.text((8, p.height - 22), 'Tait: ' + census[seq]['code'], fill=(20, 20, 20), font=font('bold', 16))
        panels.append(p)
    save(strip(panels, gap=8, bg='white'), 'making-of-3-regions.png')

# ------------------------------------------------------------------ 4. over and under, and the gaps
def fig_rendering(seq=82):
    rec = rec_of(seq); C = np.array(rec['curve']); size = tuple(rec['crop_size'])
    plain = Image.new('RGB', (size[0] * 3, size[1] * 3), PAPER); d = ImageDraw.Draw(plain)           # drawn 3x and reduced: smooth edges
    P = [(3 * x, 3 * y) for x, y in densify(C, 1.0)]; d.line(P + [P[0]], fill=INK, width=21, joint='curve')
    plain = plain.resize(size, Image.LANCZOS)
    ims = [plain, render_knot(C, size, gap=1.1), render_knot(C, size, gap=2.0)]
    titles = ['curve alone', 'over/under, gap 1.1', 'gap 2.0 (_white)']
    save(strip([titled(to_height(i, 230), t) for i, t in zip(ims, titles)], gap=8), 'making-of-4-rendering.png')

# ------------------------------------------------------------------ 5. glyphs
def glyph_cache():
    p = TENFOLD.output / 'glyphs' / 'collected.pkl'
    if p.exists(): return pickle.load(open(p, 'rb'))[0]
    return collect()[0]

def path_image(d, top, bottom, h, pad=0.12):
    """a glyph outline (glyph units, y down) as an image of height h, fitted to its ink"""
    s = h / (bottom - top); w = max(8, int(path_to_geom(d).bounds[2] * s) + 6)
    sv = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="-3 {top:.1f} {w / s:.1f} {bottom - top:.1f}">'
          f'<path d="{d}" fill="#1a1a1a" fill-rule="evenodd"/></svg>')
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=sv.encode(), background_color='white'))).convert('RGB')

def ink_image(a, h):
    """an ink map (0..1) cropped to its ink and scaled to height h"""
    ys, xs = np.nonzero(a > 0.35); a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return to_height(Image.fromarray((255 - 255 * np.clip(a, 0, 1)).astype('uint8')).convert('RGB'), h)

def fig_glyphs(names=('capitals/A', 'capitals/Ξ', 'digits/5', 'italic/k', 'greek/ζ')):
    """per glyph: three of its instances on the scan, their super-resolved average, the traced outline, and the
    outline after the hand edits of data/glyphs.yaml (where there are any)"""
    found = glyph_cache(); G = json.load(open(TENFOLD.traced / 'glyphs.json', encoding='utf-8'))['glyphs']
    H, CW = 118, 170; rows = []
    def cell(im, title):
        c = Image.new('RGB', (CW, H + 40), 'white'); c.paste(im, ((CW - im.width) // 2, 34 + (H + 6 - im.height) // 2))
        ImageDraw.Draw(c).text((6, 6), title, fill=(60, 60, 60), font=font('roman', 15)); return c
    for name in names:
        cl, ch = name.split('/'); inst = found[(cl, ch)]; g = G[name]
        avg = combine([o['crop'] for o in inst])[0]
        traced_d = g['traced']['d'] if 'traced' in g else g['d']
        b1, b2 = path_to_geom(g['d']).bounds, path_to_geom(traced_d).bounds           # fit both outlines (an edit can change the height)
        top, bottom = min(b1[1], b2[1]) - 25, max(b1[3], b2[3]) + 25
        cells = [cell(ink_image(ink(o['crop']), H), f'instance {i + 1}') for i, o in enumerate(inst[:3])]
        while len(cells) < 3: cells.append(Image.new('RGB', (CW, H + 40), 'white'))
        cells.append(cell(ink_image(avg, H), f'average of {len(inst)}' if len(inst) > 1 else 'single instance'))
        cells.append(cell(path_image(traced_d, top, bottom, H), 'traced'))
        cells.append(cell(path_image(g['d'], top, bottom, H), 'hand-edited' if 'traced' in g else 'no hand edits'))
        rows.append(strip(cells))
    save(stack(rows, gap=4), 'making-of-5-glyphs.png')

if __name__ == '__main__':
    fig_overlay(); fig_stages(); fig_regions(); fig_rendering(); fig_glyphs()
