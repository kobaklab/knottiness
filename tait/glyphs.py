"""Tracing Tait's hand-lettered annotation glyphs from the scans.

The labels on the plates (type numbers, Kirkman's designations, region letters) were written by hand
on the lithographic stone, imitating type: instances of one letter differ in size (4-8 %) and shape.
Each glyph is traced from the Internet Archive photo (greyscale, the cleanest lettering):

  1. collect: every occurrence is located on the HathiTrust page (where the knots and labels are
     segmented) and then isolated in the greyscale photo;
  2. combine: all instances are enlarged 4x and affine-aligned to the most typical one; those that then
     match it closely are averaged ("shift-and-add" super-resolution: the instances' different
     sub-pixel positions resolve detail finer than a scan pixel), and the scan's blur is removed by
     deconvolution; letters drawn with more variation average fewer instances (data/glyphs.yaml can
     force a single one);
  3. trace: the outline is taken at 50 % ink for type-like glyphs (digits, capitals, upright), whose
     corners and straight edges are then rebuilt (crisp serifs), and at a lower level for the
     calligraphic italic and Greek ones (keeps hairlines); Bézier-fitted;
  4. stroke width: all glyphs are offset to a common median stroke width;
  5. metrics: baseline and descender from the scans (region letters stand in pairs on one baseline);
  6. hand edits (data/glyphs.yaml, `edit:`), see edit_glyph below.

Units: 1000 = median capital height; y down, baseline at y = 0, ink starting at x = 0."""
import json, re
from collections import defaultdict
import numpy as np
import yaml
from scipy import ndimage
from skimage.measure import find_contours
from PIL import Image
from . import TENFOLD
DATA_DIR, TRACED_DIR = TENFOLD.data, TENFOLD.traced
from .census import load
from .codes import letter_style
from .sources import find_knots, align, SOURCES
from .render import _ring_to_bezier

ORDER = [('digits', '0123456789'), ('capitals', 'ABCDEFGHIJKLMNPQRSTUVWXYZΔΘΞΣΦ'),
         ('italic', 'abcdefghklmnpqrstu'), ('upright', 'abcdefghklpqrstu'), ('greek', 'αβγδεζηθκλ')]
DESCENDERS = {'italic': set('fgpq'), 'upright': set('gpq'), 'greek': set('βγζη')}
SHARPEN = {'digits', 'capitals', 'upright'}      # type-like lettering: crisp serifs and corners
UP, LEVEL, MATCH, SMOOTH = 8, 0.38, 0.85, 0.7      # enlargement, ink level, averaging match, outline smoothing (px)
KH_HT = SOURCES['HT']['knot_h']; SCALE = SOURCES['IA']['knot_h'] / KH_HT

def glyph_class(ch, family):
    """the glyph class of a label letter: capitals, greek, or (lowercase Latin) italic / upright"""
    if ch.isupper(): return 'capitals'
    if ord(ch) > 0x370: return 'greek'
    return letter_style(ch, family)

def _comps(mask, min_px=15):
    lab, _ = ndimage.label(mask, structure=np.ones((3, 3)))
    return [(sl, lab[sl] == i + 1) for i, sl in enumerate(ndimage.find_objects(lab)) if (lab[sl] == i + 1).sum() > min_px]

def _merge_box(main, cl):
    """bounding box of a component plus the pieces within its width and at its height (bars, inner strokes)"""
    y0, y1, x0, x1 = main[0][0].start, main[0][0].stop, main[0][1].start, main[0][1].stop; h = y1 - y0
    for sl, m in cl:
        a, b = sl[1].start, sl[1].stop
        if min(b, x1) - max(a, x0) > 0.5 * (b - a) and sl[0].start >= y0 - 0.35 * h and sl[0].stop <= y1 + 0.35 * h:
            y0, y1, x0, x1 = min(y0, sl[0].start), max(y1, sl[0].stop), min(x0, a), max(x1, b)
    return y0, y1, x0, x1

def _text_mask(ink, kh):
    """ink without the knots (and other long strokes)"""
    lab, _ = ndimage.label(ink, structure=np.ones((3, 3))); big = np.zeros(lab.max() + 1, bool)
    for i, sl in enumerate(ndimage.find_objects(lab)):
        if max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) > 0.3 * kh: big[i + 1] = True
    return ink & ~big[lab]

def collect():
    """-> (found, occ, maps): occ = {(class, char): [occurrence, ...]} in plate order, each with the HT box
    and, where the glyph could be isolated in the greyscale photo, its crop and IA box; found = only those;
    maps = {plate: (IA grey page, IA text mask, HT->IA affine, HT grey page)}"""
    rows = load(); found = defaultdict(list); occ = defaultdict(list); maps = {}
    for plate in ('LXXX', 'LXXXI'):
        gH, rH = find_knots('HT', plate); gI, rI = find_knots('IA', plate)
        A, _ = align(rI, rH, KH_HT)
        if A is None: raise SystemExit(f'{plate}: the Internet Archive scan cannot be aligned to the HathiTrust page (fewer than 10 knots in agreeing rows)')
        Ainv = np.linalg.inv(np.vstack([A, [0, 0, 1]]))[:2]
        textH = _text_mask(gH < 128, KH_HT)
        kI = SOURCES['IA']['knot_h']; textI = _text_mask(gI < ndimage.uniform_filter(gI, 61) - 30, kI)
        maps[plate] = (gI, textI, Ainv, gH)
        kh = KH_HT
        for r in rows:
            if r['plate'] != plate or (plate == 'LXXX' and r['col'] == 1): continue   # LXXX first column: cropped in HT
            t = json.load(open(TRACED_DIR / f"{r['seq']:03d}.json"))
            cy0, cy1, cx0, cx1 = t['ref_cell']; by0, by1, bx0, bx1 = t['ref_box']; xm = (bx0 + bx1) // 2
            regs = {'TL': (max(cy0, by0 - int(.32 * kh)), by0 + int(.14 * kh), cx0, xm),
                    'TR': (max(cy0, by0 - int(.32 * kh)), by0 + int(.14 * kh), xm, cx1),
                    'BL': (by1 - int(.22 * kh), min(cy1 + int(.05 * kh), by1 + int(.28 * kh)), cx0, xm),
                    'BR': (by1 - int(.22 * kh), min(cy1 + int(.05 * kh), by1 + int(.28 * kh)), xm, cx1)}
            def get(reg):
                y0, y1, x0, x1 = regs[reg]; y0, x0 = max(0, y0), max(0, x0)
                return _comps(textH[y0:y1, x0:x1]), (y0, x0)
            def add(key, bb, off, corner):
                y0, y1, x0, x1 = bb
                occ[key].append(dict(plate=plate, seq=r['seq'], corner=corner,
                                     ht=(y0 + off[0], y1 + off[0], x0 + off[1], x1 + off[1])))
            code = r['code'].rstrip('*')
            for reg, c in (('BL', code[0]), ('BR', code[1] if len(code) > 1 else None)):
                if c is None: continue
                cl, off = get(reg); cl = [x for x in cl if (x[0][0].stop - x[0][0].start) > 0.06 * kh]   # no fragments
                if cl:
                    pick = min(cl, key=lambda q: q[0][1].start) if reg == 'BL' else max(cl, key=lambda q: q[0][1].stop)
                    add((glyph_class(c, r['family']), c), _merge_box(pick, cl), off, reg)
            if r['kirkman']:
                cl, off = get('TR')
                if cl:
                    main = max(cl, key=lambda q: q[0][0].stop - q[0][0].start)
                    add(('capitals', r['kirkman'].rstrip('0123456789')), _merge_box(main, cl), off, 'TR')
            if r['form'] == 1:
                cl, off = get('TL')
                cl = sorted([c for c in cl if (c[0][0].stop - c[0][0].start) > 0.05 * kh], key=lambda q: q[0][1].start)
                if len(cl) == len(str(r['type'])):
                    for (sl, m), dch in zip(cl, str(r['type'])):
                        add(('digits', dch), (sl[0].start, sl[0].stop, sl[1].start, sl[1].stop), off, 'TL')
        # isolate each occurrence in the greyscale photo
        for key, lst in occ.items():
            for o in lst:
                if o['plate'] != plate or 'crop' in o: continue
                o.update(_isolate(gI, textI, Ainv, o['ht']) or {})
    for key, lst in occ.items():
        found[key] = [o for o in lst if 'crop' in o]
    return found, occ, maps

COLLECTED_CACHE = TRACED_DIR.parent / 'output' / 'glyphs' / 'collected.pkl'

def load_collected(fresh=False):
    """collect(), cached in tenfold/output/glyphs/collected.pkl (maps stored as uint8). The cache is not
    keyed to its inputs, so a cache older than the knot traces or the census is reported: pass fresh=True
    (trace_glyphs.py --fresh) to collect again from the scans (about 3 minutes)."""
    import os, pickle, time
    if COLLECTED_CACHE.exists() and not fresh:
        newest = max(os.path.getmtime(q) for q in [*TRACED_DIR.glob('[0-9]*.json'), DATA_DIR / 'census.csv'])
        made = os.path.getmtime(COLLECTED_CACHE)
        print(f'using the cached glyph instances {COLLECTED_CACHE.name} (made {time.strftime("%Y-%m-%d %H:%M", time.localtime(made))}); '
              '--fresh collects them again from the scans')
        if made < newest:
            print('WARNING: the cache is older than the knot traces or census.csv; if they changed, use --fresh')
        return pickle.load(open(COLLECTED_CACHE, 'rb'))
    found, occ, maps = collect()
    maps = {p: (gI.clip(0, 255).astype(np.uint8), txt, A, gH.clip(0, 255).astype(np.uint8)) for p, (gI, txt, A, gH) in maps.items()}
    COLLECTED_CACHE.parent.mkdir(parents=True, exist_ok=True)
    pickle.dump((found, occ, maps), open(COLLECTED_CACHE, 'wb'), protocol=5)
    return found, occ, maps

def _isolate(gI, txt, Ainv, ht, mode='nearest'):
    """find the glyph near its mapped position in the greyscale photo; whiten everything else"""
    y0, y1, x0, x1 = ht
    cx, cy = Ainv @ [(x0 + x1) / 2, (y0 + y1) / 2, 1]; h = (y1 - y0) * SCALE; w = (x1 - x0) * SCALE; pad = 0.9 * h
    Y0, Y1, X0, X1 = int(cy - h / 2 - pad), int(cy + h / 2 + pad), int(cx - w / 2 - pad), int(cx + w / 2 + pad)
    if Y0 < 0 or X0 < 0 or Y1 > gI.shape[0] or X1 > gI.shape[1]: return None
    cl = [c for c in _comps(txt[Y0:Y1, X0:X1]) if (c[0][0].stop - c[0][0].start) > 0.25 * h]
    if not cl: return None
    if mode == 'tallest': main = max(cl, key=lambda q: q[0][0].stop - q[0][0].start)
    elif mode == 'left': main = min(cl, key=lambda q: q[0][1].start)
    elif mode == 'right': main = max(cl, key=lambda q: q[0][1].stop)
    else:
        tall = [q for q in cl if (q[0][0].stop - q[0][0].start) > 0.6 * h] or cl
        main = min(tall, key=lambda q: np.hypot((q[0][1].start + q[0][1].stop) / 2 - (cx - X0),
                                                (q[0][0].start + q[0][0].stop) / 2 - (cy - Y0)))
    gy0, gy1, gx0, gx1 = _merge_box(main, cl)
    if not (0.6 * h < gy1 - gy0 < 1.5 * h): return None
    # proportions must match the glyph found on the HathiTrust page (rejects a neighbouring glyph)
    r_ht = (x1 - x0) / max(1, y1 - y0); r_ia = (gx1 - gx0) / max(1, gy1 - gy0)
    if max(r_ia / r_ht, r_ht / r_ia) > 1.45: return None
    lab, _ = ndimage.label(txt[Y0:Y1, X0:X1], structure=np.ones((3, 3))); keep = np.zeros_like(lab, bool)
    for sl, m in [main] + cl:
        if sl[1].start >= gx0 and sl[1].stop <= gx1 and sl[0].start >= gy0 and sl[0].stop <= gy1: keep[sl] |= m
    keep = ndimage.binary_dilation(keep, iterations=2)
    crop = gI[Y0:Y1, X0:X1].astype(float).copy(); crop[~keep] = np.percentile(crop, 90)
    p = 3
    return dict(crop=crop[max(0, gy0 - p):gy1 + p, max(0, gx0 - p):gx1 + p],
                box=(Y0 + gy0, Y0 + gy1, X0 + gx0, X0 + gx1), mode=mode)

def ink(g):
    paper = np.percentile(g, 90); dark = np.percentile(g, 2)
    return np.clip((paper - g) / max(paper - dark, 1), 0, 1)

K_SR = 4            # super-resolution factor of the combined ink map
PSF_SIGMA = 0.7     # optical blur of the scan, in scan pixels (for deconvolution)

def combine(crops, match=MATCH, deconvolve=True):
    """Super-resolved ink map of a glyph from its instances ("shift-and-add"):
    each instance is enlarged K_SR times, affine-aligned to the most typical one (OpenCV ECC: separate
    horizontal and vertical scale, shear, rotation, shift) and averaged if it then matches well. Because
    the instances sit at different sub-pixel positions on the scan, the average resolves detail finer
    than one scan pixel; Richardson-Lucy deconvolution then removes the scan's optical blur.
    Returns (ink map at K_SR x scan resolution, number averaged, reference index, padding)."""
    import cv2
    from skimage.restoration import richardson_lucy
    I = [ink(c).astype(np.float32) for c in crops]
    if len(I) > 2:          # reference: best average correlation with all others (a stray instance never wins)
        small = [np.array(Image.fromarray((255 * a).astype('uint8')).resize((24, 32), Image.BILINEAR), float).ravel() for a in I]
        Cm = np.corrcoef(np.array(small)); np.fill_diagonal(Cm, np.nan)
        ri = int(np.nanargmax(np.nanmean(Cm, axis=1)))
    else:
        ri = int(np.argsort([i.shape[0] for i in I])[len(I) // 2])
    H = I[ri].shape[0]
    up = lambda a: cv2.resize(a, (max(1, int(round(a.shape[1] * H / a.shape[0] * K_SR))), H * K_SR), interpolation=cv2.INTER_CUBIC)
    ref = up(I[ri]); pad = 8 * K_SR
    R = np.zeros((ref.shape[0] + 2 * pad, ref.shape[1] + 2 * pad + 10 * K_SR), np.float32)
    R[pad:pad + ref.shape[0], pad:pad + ref.shape[1]] = ref
    stack = [R]; crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 150, 1e-5)
    for j, a in enumerate(I):
        if j == ri: continue
        u = up(a); A = np.zeros_like(R); h, w = u.shape; w = min(w, A.shape[1] - pad); A[pad:pad + h, pad:pad + w] = u[:, :w]
        try:
            cc, M = cv2.findTransformECC(R, A, np.eye(2, 3, dtype=np.float32), cv2.MOTION_AFFINE, crit, None, 5)
        except cv2.error:
            continue
        if cc > match:
            stack.append(cv2.warpAffine(A, M, (R.shape[1], R.shape[0]), flags=cv2.INTER_CUBIC + cv2.WARP_INVERSE_MAP))
    avg = np.clip(np.mean(stack, axis=0), 0, 1).astype(float)
    if deconvolve:
        sg = PSF_SIGMA * K_SR; r = int(3 * sg) + 1; yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
        psf = np.exp(-(xx * xx + yy * yy) / (2 * sg * sg)); psf /= psf.sum()
        avg = richardson_lucy(avg, psf, num_iter=20, clip=True)
    return avg, len(stack), ri, pad

def outline(avg, level=LEVEL, smooth=SMOOTH, cuts=(), speck=0.04, sharpen=False):
    """ink map -> (shapely geometry at UP x, true-weight mask). The outline is taken at `level` (low, to keep
    hairlines); the mask at 50 % ink marks the real stroke edges, for measuring the stroke width.
    cuts: rectangles (fractions of the ink box) to erase. Separate parts smaller than `speck` x the largest
    part are dropped."""
    from shapely.geometry import Polygon
    big = ndimage.gaussian_filter(ndimage.zoom(avg, UP / K_SR, order=3), (0.12 if sharpen else 0.25) * UP)
    if cuts:
        ys, xs = np.nonzero(big > level); y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        for fx0, fy0, fx1, fy1 in cuts:
            big[int(y0 + fy0 * (y1 - y0)):int(y0 + fy1 * (y1 - y0)), int(x0 + fx0 * (x1 - x0)):int(x0 + fx1 * (x1 - x0))] = 0
    geom = None
    for r in find_contours(np.pad(big, 2), level):
        if len(r) < 12: continue
        xy = np.stack([r[:, 1] - 2, r[:, 0] - 2], 1)
        if np.hypot(*(xy[0] - xy[-1])) > 1: continue
        if sharpen:
            xy = sharpen_ring(xy[:-1], smooth)
        else:
            s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]); n = max(16, int(s[-1]))
            u = np.linspace(0, s[-1], n, endpoint=False)
            xy = np.stack([np.interp(u, s, xy[:, 0]), np.interp(u, s, xy[:, 1])], 1)
            xy = np.stack([ndimage.gaussian_filter1d(xy[:, j], smooth * UP, mode='wrap') for j in (0, 1)], 1)
        if len(xy) < 3: continue                                          # degenerate (tiny) ring
        p = Polygon(xy).buffer(0)
        if p.is_empty: continue
        geom = p if geom is None else geom.symmetric_difference(p)          # even-odd: holes stay holes
    parts = list(getattr(geom, 'geoms', [geom])); amax = max(q.area for q in parts)
    from shapely.ops import unary_union
    geom = unary_union([q for q in parts if q.area >= speck * amax])
    return geom, big > 0.5

def sharpen_ring(xy, smooth=SMOOTH, corner_deg=35.0, straight_px=0.35, straight_rel=0.06):
    """For type-like lettering: rebuild sharp corners and straight edges on a traced (blurred) outline.
    Corners are found where the outline turns sharply; between corners, nearly straight stretches become
    exact straight lines (serifs, stems, bars), and where two straight stretches meet the corner is put
    at the intersection of their lines (restoring square corners); curved stretches are smoothed.
    xy: closed ring (UP x pixels), without the repeated end point."""
    q = np.vstack([xy, xy[:1]]); s_ = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(q, axis=0).T))])
    n = max(24, int(s_[-1])); u = np.linspace(0, s_[-1], n, endpoint=False)
    P = np.stack([np.interp(u, s_, q[:, 0]), np.interp(u, s_, q[:, 1])], 1)
    P = np.stack([ndimage.gaussian_filter1d(P[:, j], 0.2 * UP, mode='wrap') for j in (0, 1)], 1)
    w = max(3, int(0.4 * UP))
    v1 = P - np.roll(P, w, 0); v2 = np.roll(P, -w, 0) - P
    ang = np.degrees(np.abs(np.arctan2(v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0], (v1 * v2).sum(1))))
    peak = (ang == ndimage.maximum_filter1d(ang, 2 * w + 1, mode='wrap')) & (ang > corner_deg)
    C = list(np.nonzero(peak)[0])
    C = [c for i, c in enumerate(C) if i == 0 or c - C[i - 1] > w]
    if len(C) < 2:
        return np.stack([ndimage.gaussian_filter1d(P[:, j], smooth * UP, mode='wrap') for j in (0, 1)], 1)
    segs = []                                          # (start corner, end corner, points, line or None)
    for i, c0 in enumerate(C):
        c1 = C[(i + 1) % len(C)]
        idx = np.arange(c0, c1 + 1) if c1 > c0 else np.r_[np.arange(c0, n), np.arange(0, c1 + 1)]
        S = P[idx]; L = np.hypot(*(S[-1] - S[0])) + 1e-9
        inner = S[w:-w] if len(S) > 2 * w + 2 else S
        ctr = inner.mean(0); _, _, vt = np.linalg.svd(inner - ctr); d = vt[0]
        dev = np.abs((inner - ctr) @ np.array([-d[1], d[0]])).max() if len(inner) else 0
        straight = dev < max(straight_px * UP, straight_rel * L)
        segs.append((S, (ctr, d) if straight else None))
    def meet(a, b, fallback):
        (p1, d1), (p2, d2) = a, b
        M = np.array([d1, -d2]).T
        if abs(np.linalg.det(M)) < 1e-6: return fallback
        t = np.linalg.solve(M, p2 - p1); X = p1 + t[0] * d1
        return X if np.hypot(*(X - fallback)) < 2.5 * UP else fallback
    corners = []
    for i in range(len(segs)):
        prev, cur = segs[i - 1], segs[i]
        P0 = cur[0][0]
        corners.append(meet(prev[1], cur[1], P0) if prev[1] is not None and cur[1] is not None else P0)
    out = []
    for i, (S, line) in enumerate(segs):
        out.append(corners[i])
        if line is None and len(S) > 2:                # curved stretch: smooth, ends pinned to its corners
            inner = S[1:-1]
            sm = np.stack([ndimage.gaussian_filter1d(inner[:, j], smooth * UP, mode='nearest') for j in (0, 1)], 1)
            k = min(len(sm), w)                        # blend towards the unsmoothed ends near the corners
            wgt = np.ones(len(sm)); wgt[:k] = np.linspace(0, 1, k); wgt[-k:] = np.minimum(wgt[-k:], np.linspace(1, 0, k))
            out.extend(list(inner * (1 - wgt[:, None]) + sm * wgt[:, None]))
    return np.array(out)

def smooth_geom(geom, smooth=SMOOTH):
    """smooth every ring of a geometry along its length (scan pixels; geometry at UP x)"""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    out = None
    for p in getattr(geom, 'geoms', [geom]):
        rings = []
        for ring in [p.exterior, *p.interiors]:
            xy = np.asarray(ring.coords)[:-1]
            s_ = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(np.vstack([xy, xy[:1]]), axis=0).T))])
            n = max(16, int(s_[-1])); u = np.linspace(0, s_[-1], n, endpoint=False)
            q = np.vstack([xy, xy[:1]])
            xy = np.stack([np.interp(u, s_, q[:, 0]), np.interp(u, s_, q[:, 1])], 1)
            rings.append(np.stack([ndimage.gaussian_filter1d(xy[:, j], smooth * UP, mode='wrap') for j in (0, 1)], 1))
        poly = Polygon(rings[0], rings[1:]).buffer(0)
        out = poly if out is None else unary_union([out, poly])
    return out

def geom_stroke_width(geom):
    """the same measure for a shapely geometry: 2 * area / boundary length"""
    return 2 * geom.area / geom.length if geom.length > 0 else 0.0

def to_path(geom, ox, oy, k):
    """shapely geometry (UP x px) -> SVG path in glyph units: (x - ox) * k, (y - oy) * k"""
    polys = getattr(geom, 'geoms', [geom]); d = []
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            xy = (np.asarray(ring.coords) - [ox, oy]) * k
            d.append(_ring_to_bezier(xy, tol=0.15 * UP * k))
    return ' '.join(d)

def load_choices(poster=TENFOLD):
    return yaml.safe_load(open(poster.data / 'glyphs.yaml', encoding='utf-8')) or {}

# ---------------------------------------------------------------------------------------------
# Hand edits of the traced outlines (data/glyphs.yaml, key 'edit'). They work on the finished glyph,
# in glyph units (1000 = capital height, y down, baseline at y = 0), and are applied in order. Most
# replace the outline inside a region by something else: the region is a `box` [x0, y0, x1, y1] or a
# `region` polygon [[x, y], ...]; over `fade` units inside its edge the old and the new outline are
# morphed into each other (signed-distance blending), so the patch joins without a seam. For a box,
# fade can be given per edge as [left, top, right, bottom]; an edge with fade 0 should lie on blank
# paper (or on ink that the new outline continues exactly).
#
#   {height: H, bands: [[y0, y1], ...]}   make the glyph H tall (baseline fixed) by stretching or
#        squeezing only the given horizontal bands (default: the middle 70 % of the glyph), so that
#        serifs, bars and bowls outside the bands keep their exact shape and thickness
#   {copy: 'capitals/X', dx: .., dy: .., flip: x|y, axis: c, box|region, fade}   inside the region,
#        take the outline of another glyph (its original trace; omit `copy` for the glyph itself),
#        first mirrored about x = c (flip: x) or y = c (flip: y), then shifted by (dx, dy)
#   {mirror: [x0, y0, x1, y1], axis: c, fade}   short for a copy of the glyph itself, flipped about x = c
#   {thin: d, box|region, fade}           make the strokes d units thinner on each side (negative:
#        thicker); without a region, the whole glyph
#   {smooth: s, box|region, fade}         round off irregularities smaller than about s units
#   {add: [[x, y], ...]} / {cut: [[x, y], ...]}   add or erase a polygon of ink
#
# Coordinates refer to the outline as it is at that step; the ink is moved back to start at x = 0
# only at the end.
# ---------------------------------------------------------------------------------------------
_PATH_TOK = re.compile(r'[MLCZ]|-?\d+(?:\.\d+)?(?:e-?\d+)?')

def path_to_geom(d, n=16):
    """SVG path (absolute M, L, C, Z; even-odd) -> shapely geometry, Béziers flattened"""
    from shapely.geometry import Polygon
    toks = _PATH_TOK.findall(d); rings, cur, pos, cmd, i = [], [], None, None, 0
    t = np.linspace(0, 1, n + 1)[1:, None]
    while i < len(toks):
        if toks[i] in 'MLCZ':
            cmd = toks[i]; i += 1
            if cmd == 'Z':
                if cur: rings.append(np.array(cur)); cur = []
                continue
        if cmd == 'M':
            pos = np.array(toks[i:i + 2], float); cur = [pos]; i += 2; cmd = 'L'
        elif cmd == 'L':
            pos = np.array(toks[i:i + 2], float); cur.append(pos); i += 2
        else:
            c = np.array(toks[i:i + 6], float).reshape(3, 2); P = np.vstack([pos, c]); i += 6
            cur.extend((1 - t)**3 * P[0] + 3 * (1 - t)**2 * t * P[1] + 3 * (1 - t) * t**2 * P[2] + t**3 * P[3]); pos = c[2]
    geom = None
    for r in rings:
        p = Polygon(r).buffer(0)
        geom = p if geom is None else geom.symmetric_difference(p)
    return geom

def geom_to_path(geom, tol=1.0):
    d = []
    for p in getattr(geom, 'geoms', [geom]):
        for ring in [p.exterior, *p.interiors]:
            d.append(_ring_to_bezier(np.asarray(ring.coords), tol=tol))
    return ' '.join(d)

def _band_map(top, H, bands=None):
    """y -> y for a height change from -top to H, spread over the bands (y <= 0 only)"""
    if not bands: bands = [[0.85 * top, 0.15 * top]]
    bands = sorted([sorted(b) for b in bands]); L = sum(b[1] - b[0] for b in bands)
    k = (H + top) / L                                    # extra length per unit of band
    ys, fs = [0.0], [0.0]                                # breakpoints, going up from the baseline
    for y0, y1 in reversed(bands):
        y1 = min(y1, 0.0)
        fs.append(fs[-1] + (y1 - ys[-1])); ys.append(y1)                 # unchanged below the band
        fs.append(fs[-1] + (y0 - y1) * (1 + k)); ys.append(y0)           # stretched inside it
    fs.append(fs[-1] - 1e4); ys.append(ys[-1] - 1e4)
    ys, fs = np.array(ys[::-1]), np.array(fs[::-1])
    return lambda y: np.where(y > 0, y, np.interp(y, ys, fs))

def _polys(geom):
    return [p for p in getattr(geom, 'geoms', [geom]) if p.geom_type == 'Polygon']

def _sdf(geom, gx0, gy0, nx, ny, res):
    """signed distance (glyph units, negative inside) on a grid of nx x ny pixels at res px/unit"""
    from PIL import ImageDraw
    im = Image.new('1', (nx, ny), 0); dr = ImageDraw.Draw(im)
    f = lambda ring: [((x - gx0) * res, (y - gy0) * res) for x, y in ring.coords]
    for p in _polys(geom):
        dr.polygon(f(p.exterior), fill=1)
        for r in p.interiors: dr.polygon(f(r), fill=0)
    m = np.array(im, bool)
    return (ndimage.distance_transform_edt(~m) - ndimage.distance_transform_edt(m)) / res

def _weight(XX, YY, op):
    """blending weight of the new outline: 1 deep inside the region, 0 outside, smoothstep in the fade zone"""
    fade = op.get('fade', 0.0)
    if 'region' in op:
        from PIL import ImageDraw
        res = 1 / (XX[0, 1] - XX[0, 0]); gx0, gy0 = XX[0, 0] - 0.5 / res, YY[0, 0] - 0.5 / res
        im = Image.new('1', (XX.shape[1], XX.shape[0]), 0)
        ImageDraw.Draw(im).polygon([((x - gx0) * res, (y - gy0) * res) for x, y in op['region']], fill=1)
        inside = np.array(im, bool)
        w = np.clip(ndimage.distance_transform_edt(inside) / res / fade, 0, 1) if fade else inside.astype(float)
    else:
        x0, y0, x1, y1 = op['box']
        fl, ft, fr, fb = fade if isinstance(fade, (list, tuple)) else [fade] * 4
        w = ((XX >= x0) & (XX <= x1) & (YY >= y0) & (YY <= y1)).astype(float)
        for dist, f in ((XX - x0, fl), (YY - y0, ft), (x1 - XX, fr), (y1 - YY, fb)):
            if f > 0: w = np.minimum(w, np.clip(dist / f, 0, 1))
    return w * w * (3 - 2 * w)                           # smoothstep: no kinks where the morph starts and ends

def _region(op, geom):
    from shapely.geometry import Polygon, box as Box
    if 'region' in op: return Polygon(op['region']).buffer(0)
    if 'box' in op: return Box(*op['box'])
    x0, y0, x1, y1 = geom.bounds; return Box(x0 - 50, y0 - 50, x1 + 50, y1 + 50)

def _replace(geom, op, new_sdf, res=2.0):
    """replace the outline inside the op's region by the zero level of new_sdf(old_sdf, X, Y),
    morphing over the fade zone"""
    from shapely.geometry import Polygon
    R = _region(op, geom); x0, y0, x1, y1 = R.bounds; mg = 4
    gx0, gy0 = x0 - mg, y0 - mg; nx, ny = int((x1 - x0 + 2 * mg) * res) + 1, int((y1 - y0 + 2 * mg) * res) + 1
    X = gx0 + (np.arange(nx) + 0.5) / res; Y = gy0 + (np.arange(ny) + 0.5) / res; XX, YY = np.meshgrid(X, Y)
    if 'box' not in op and 'region' not in op: op = dict(op, box=list(R.bounds))
    so = _sdf(geom, gx0, gy0, nx, ny, res)
    w = _weight(XX, YY, op)
    s = ndimage.gaussian_filter((1 - w) * so + w * new_sdf(so, gx0, gy0, nx, ny, res), 0.5 * res)
    s = np.pad(s, 1, constant_values=1e3)
    new = None
    for c in find_contours(s, 0.0):
        if len(c) < 8: continue
        p = Polygon(np.stack([gx0 + (c[:, 1] - 0.5) / res, gy0 + (c[:, 0] - 0.5) / res], 1)).buffer(0)
        new = p if new is None else new.symmetric_difference(p)
    out = geom.difference(R)
    if new is not None: out = out.union(new.intersection(R))
    return out.buffer(0.3, join_style=2).buffer(-0.3, join_style=2)

def edit_glyph(d, ops, tol=1.0, lookup=None):
    """traced path + list of edit operations -> dict(d, width, top, bottom) in glyph units.
    lookup(name) -> path of another glyph (for copy)"""
    from shapely.geometry import Polygon
    from shapely.ops import transform, unary_union
    from shapely.affinity import scale, translate
    g = path_to_geom(d)
    for op in ops:
        op = dict(op)
        if 'height' in op:
            f = _band_map(g.bounds[1], float(op['height']), op.get('bands'))
            g = transform(lambda x, y, z=None: (x, f(np.asarray(y))), g)
        elif 'mirror' in op or 'copy' in op:
            if 'mirror' in op: op.update(box=op['mirror'], flip='x')
            src = path_to_geom(lookup(op['copy'])) if op.get('copy') else g
            if op.get('flip') == 'x': src = scale(src, xfact=-1, yfact=1, origin=(float(op['axis']), 0))
            elif op.get('flip') == 'y': src = scale(src, xfact=1, yfact=-1, origin=(0, float(op['axis'])))
            src = translate(src, op.get('dx', 0), op.get('dy', 0))
            g = _replace(g, op, lambda so, *grid: _sdf(src, *grid))
        elif 'thin' in op:
            g = _replace(g, op, lambda so, *grid: so + float(op['thin']))
        elif 'smooth' in op:
            sg = float(op['smooth'])
            g = _replace(g, op, lambda so, gx0, gy0, nx, ny, res: ndimage.gaussian_filter(so, sg * res))
        elif 'add' in op:
            g = unary_union([g, Polygon(op['add']).buffer(0)])
        elif 'cut' in op:
            g = g.difference(Polygon(op['cut']).buffer(0))
        else:
            raise ValueError(f'unknown glyph edit: {op}')
        g = g.buffer(0)
    g = g.buffer(-1, join_style=1).buffer(1, join_style=1)   # no slivers or hairline spikes (they upset the Bézier fit)
    parts = _polys(g); amax = max(p.area for p in parts)
    g = unary_union([p for p in parts if p.area > 0.01 * amax])
    g = translate(g, -g.bounds[0], 0)
    x0, y0, x1, y1 = g.bounds
    return dict(d=geom_to_path(g, tol), width=round(x1 - x0, 1), top=round(y0, 1), bottom=round(max(y1, 0.0), 1))

def apply_edits(glyphs, choices):
    """apply the 'edit' lists of data/glyphs.yaml to the glyph entries of traced/glyphs.json (in place).
    The untouched trace is kept under 'traced', so edits can be re-applied or removed without re-tracing.
    Copies from other glyphs always take their untouched trace."""
    for g in glyphs.values():
        if 'traced' in g: g.update(g.pop('traced'))           # back to the trace
        g.pop('edited', None)
    lookup = lambda name: glyphs[name]['traced']['d'] if 'traced' in glyphs[name] else glyphs[name]['d']
    for name, g in glyphs.items():
        ops = (choices.get(name) or {}).get('edit')
        if not ops: continue
        try:
            new = edit_glyph(g['d'], ops, lookup=lookup)
        except Exception as e:
            raise SystemExit(f'{name}: edit failed: {e}')
        g['traced'] = {k: g[k] for k in ('d', 'width', 'top', 'bottom')}
        g.update(new); g['edited'] = len(ops)
    return glyphs
