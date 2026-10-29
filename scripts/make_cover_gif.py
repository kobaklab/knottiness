"""The animated and the social versions of the README cover (docs/):

  cover.gif                    the cover, animated: header and two rows of knots
  cover_16x9.png, .gif         16:9 versions for social media (as many rows as fit), 1500 px wide

  uv run scripts/make_cover_gif.py            (after both build_poster.py scripts; reads the tenfold SVGs in output/)

Every knot is drawn along its line from a random starting point, and all knots are complete in the same frame (each
at its own speed, in proportion to its length); the labels and the header stand from the start.

How: the finished knot is one outline cut into pieces by the gaps of its under-crossings. A piece is shown only where it lies
within reach of the part of its own centreline that has been drawn so far, so the gaps are right in every frame."""
import io, json, random, re
import numpy as np
import cairosvg, shapely
from PIL import Image, ImageDraw
from shapely.geometry import LineString
from shapely.ops import unary_union
from tait import ROOT, TENFOLD
from tait.layout import Y_GRID as Y_GRID_MM, ROW_H as ROW_MM
from tait.census import load
from tait.poster import knot_svg
from tait.render import densify, knot_shape

DOCS = ROOT / 'docs'
SS = 3                                 # supersampling of the drawing
DRAW_FRAMES, FRAME_MS, HOLD_MS = 72, 40, 2500
PAPER, INK = (246, 240, 220), (26, 26, 26)

svg_text = (TENFOLD.output / 'tenfold_knottiness_page1.svg').read_text(encoding='utf-8')
lines = svg_text.split('\n')
knot_lines = [l for l in lines if l.startswith('<path id="knot-')]
bare = '\n'.join(l for l in lines if not l.startswith('<path id="knot-'))
VX, _, VW, _ = map(float, re.search(r'viewBox="([^"]+)"', svg_text).group(1).split())     # the page's left edge in sheet coordinates
census = {r['seq']: r for r in load(TENFOLD.data / 'census.csv')}
STROKE = knot_svg(TENFOLD, 1)[1]

def render(text, W): return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=text.encode(), output_width=W))).convert('RGB')

def row_end(ink, n_rows, mm):
    """the last line of ink of the labels of row n_rows (the line before the blank gap that follows it)"""
    guess = (Y_GRID_MM + n_rows * ROW_MM) * mm
    lo, hi = int(guess - 3 * mm), int(guess + 3 * mm)
    return int(np.flatnonzero(ink[lo:hi] == 0)[0]) + lo

def crop_box(W, kind):
    """(first line, last line + 1, rows, height, last line of ink) of the crop of the page"""
    full = render(svg_text, W); mm = W / VW
    ink = (np.array(full.convert('L')) < 128).sum(1); ink_top = int(np.flatnonzero(ink > 0)[0])
    if kind == 'cover':                                    # as docs/cover.png: from 10.5 mm, two rows, margin below = margin above
        top = int(10.5 * mm); margin = int(np.flatnonzero(ink[top:] > 0)[0]); end = row_end(ink, 2, mm)
        return top, end + margin, 2, (end - top) + margin, end
    H = round(W * 9 / 16); m_min = int(np.flatnonzero(ink[int(10.5 * mm):] > 0)[0])      # at least the cover's margin
    rows = max(n for n in range(1, 14) if (row_end(ink, n, mm) - ink_top) + 2 * m_min <= H)
    m = (H - (row_end(ink, rows, mm) - ink_top)) // 2                 # equal white space above the header and below the labels
    return ink_top - m, ink_top - m + H, rows, H, row_end(ink, rows, mm)

def knots_of(rows):
    out = []; rng = random.Random(7)
    for l in knot_lines:
        mt = re.match(r'<path id="knot-(\d+)" transform="translate\(([-\d.]+),([-\d.]+)\) scale\(([-\d.e]+)\)"', l)
        seq = int(mt.group(1)); tx, ty, k = float(mt.group(2)), float(mt.group(3)), float(mt.group(4))
        if census[seq]['row'] > rows or census[seq]['plate'] != 'LXXX': continue
        curve = np.array(json.load(open(TENFOLD.traced / f'{seq:03d}.json'))['curve'])
        C = densify(curve, 0.5); s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(np.vstack([C, C[:1]]), axis=0).T))]); L = s[-1]
        u = (s[:-1] - rng.uniform(0, L)) % L                       # distance along the drawing from a random starting point
        pieces = []
        for P in getattr(knot_shape(curve, stroke=STROKE, margin=STROKE * 1.1), 'geoms', []):
            inside = shapely.contains_xy(P, C[:, 0], C[:, 1]); idx = np.flatnonzero(inside)
            runs = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1) if len(idx) else []
            if len(runs) > 1 and inside[0] and inside[-1]: runs[0] = np.concatenate([runs[-1], runs[0]]); runs.pop()
            run = max(runs, key=len)                                # the piece's own stretch (the others are strands crossing over it)
            pieces.append(dict(poly=P, idx=run, u=u[run], done=False))
        out.append(dict(seq=seq, t=(tx, ty, k), C=C, L=L, pieces=pieces))
    return out

def palette():
    img = Image.new('P', (1, 1)); pal = []
    for i in range(32): f = i / 31; pal += [round(PAPER[c] + (INK[c] - PAPER[c]) * f) for c in range(3)]
    img.putpalette(pal + [0] * (768 - len(pal))); return img

def build(W, kind):
    top, bottom, rows, H, end = crop_box(W, kind); mm = W / VW
    full = render(svg_text, W); still = full.crop((0, top, W, top + H))      # the finished picture, not reduced to the GIF's palette
    background = Image.new('RGB', (W, H), PAPER); background.paste(render(bare, W).crop((0, top, W, min(bottom, full.height))), (0, 0))
    for im in (still, background): ImageDraw.Draw(im).rectangle([0, end - top + 1, W, H], fill=PAPER)     # nothing of the next row below the labels
    knots = knots_of(rows); print(kind, W, 'px:', rows, 'rows,', len(knots), 'knots')
    def to_px(poly, t):
        tx, ty, k = t
        return [(((tx + k * x - VX) * mm) * SS, ((ty + k * y) * mm - top) * SS) for x, y in poly.exterior.coords]
    done_mask = Image.new('L', (W * SS, H * SS), 0); dd = ImageDraw.Draw(done_mask)
    ink_im = Image.new('RGB', (W, H), INK); pal = palette(); frames = []
    for f in range(1, DRAW_FRAMES + 1):
        p = f / DRAW_FRAMES; partial = []
        for kn in knots:
            t = p * kn['L'] * (1 + 1e-9)                          # every knot is at the same fraction of its length
            for pc in kn['pieces']:
                if pc['done']: continue
                on = pc['u'] <= t
                if not on.any(): continue
                if on.all():
                    pc['done'] = True
                    for g in getattr(pc['poly'], 'geoms', [pc['poly']]): dd.polygon(to_px(g, kn['t']), fill=255)
                    continue
                idx = pc['idx']; blocks = np.split(np.flatnonzero(on), np.flatnonzero(np.diff(np.flatnonzero(on)) > 1) + 1)
                parts = [LineString(kn['C'][idx[b]]).buffer(STROKE * 0.8, cap_style=2, join_style=1) for b in blocks if len(b) > 1]
                if parts: partial.append((pc['poly'].intersection(unary_union(parts)), kn['t']))
        mask = done_mask.copy(); d = ImageDraw.Draw(mask)
        for shown, tt in partial:
            for g in getattr(shown, 'geoms', [shown]):
                if g.geom_type == 'Polygon' and not g.is_empty: d.polygon(to_px(g, tt), fill=255)
        frames.append(Image.composite(ink_im, background, mask.resize((W, H), Image.LANCZOS)).quantize(palette=pal, dither=Image.Dither.NONE))
    return frames, still

def save_gif(frames, name):
    out = DOCS / name; frames = frames + [frames[-1].copy()]
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=[FRAME_MS] * (len(frames) - 1) + [HOLD_MS], loop=0, optimize=True, disposal=1)
    print('wrote', out.relative_to(ROOT), len(frames), 'frames,', round(out.stat().st_size / 1024), 'KB')

if __name__ == '__main__':
    frames, _ = build(1500, 'cover'); save_gif(frames, 'cover.gif')
    frames, still = build(1500, 'social')
    still.save(DOCS / 'cover_16x9.png', optimize=True); print('wrote docs/cover_16x9.png', round((DOCS / 'cover_16x9.png').stat().st_size / 1024), 'KB', still.size)
    save_gif(frames, 'cover_16x9.gif')
