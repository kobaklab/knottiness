"""Render a closed centreline as an alternating knot diagram (thin line with gaps).

The knot is drawn as one filled outline. At each crossing the under-strand is cut away where it
passes through the over-strand's band (the over-strand's width plus a margin on both sides), so the
gap edges run parallel to the over-strand whatever the crossing angle. No background-coloured
patches are used, so the result works on any background."""
import numpy as np

DEFAULT_STROKE = 6.5      # line width of the rendered knots, in working px (median knot height 314): the posters' width

def self_intersections(C):
    N = len(C); A = C; B = np.roll(C, -1, 0); out = []
    d = B - A
    for i in range(N):
        p, r = A[i], d[i]
        j = np.arange(i + 2, N)
        if i == 0: j = j[j != N - 1]
        q, s = A[j], d[j]
        den = r[0] * s[:, 1] - r[1] * s[:, 0]
        ok = np.abs(den) > 1e-12
        qp = q - p
        t = np.where(ok, (qp[:, 0] * s[:, 1] - qp[:, 1] * s[:, 0]) / np.where(ok, den, 1), -1)
        v = np.where(ok, (qp[:, 0] * r[1] - qp[:, 1] * r[0]) / np.where(ok, den, 1), -1)
        hit = ok & (t >= 0) & (t < 1) & (v >= 0) & (v < 1)
        for jj, tt, vv in zip(j[hit], t[hit], v[hit]): out.append((i + tt, jj + vv))
    return out

def densify(C, step=1.0):
    """smooth closed curve through stored points (periodic interpolating spline), ~step px apart"""
    from scipy.interpolate import splprep, splev
    C = np.asarray(C, float)
    tck, _ = splprep([C[:, 0], C[:, 1]], s=0, per=1)
    L = np.sum(np.hypot(*np.diff(np.vstack([C, C[:1]]), axis=0).T))
    return np.array(splev(np.linspace(0, 1, int(L / step), endpoint=False), tck)).T

# ---------------------------------------------------------------------------------------------
# Filled-outline rendering with geometric gaps
# ---------------------------------------------------------------------------------------------
def _arc_window(C, s, centre, lo, hi):
    """indices of the closed curve C within arc-length [centre+lo, centre+hi] (s = cumulative length)"""
    L = s[-1]
    t = np.linspace(centre + lo, centre + hi, max(2, int((hi - lo) / 0.5)))
    return np.stack([np.interp(t % L, s, np.append(C[:, 0], C[0, 0])[:len(s)]),
                     np.interp(t % L, s, np.append(C[:, 1], C[0, 1])[:len(s)])], 1), t

def knot_shape(curve, stroke=DEFAULT_STROKE, margin=None, reach=None):
    """the knot as one filled shapely geometry: the curve's outline, with each under-strand removed
    wherever it passes through the over-strand's band (its width plus `margin` on both sides).
    Gap edges are therefore always parallel to the over-strand, whatever the crossing angle."""
    import shapely
    from shapely.geometry import LineString, LinearRing
    from shapely.ops import unary_union
    margin = stroke * 1.1 if margin is None else margin
    C = densify(curve, 0.5); n = len(C)
    seg = np.hypot(*np.diff(np.vstack([C, C[:1]]), axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])                   # s[i] = arc length at point i; s[n] = L
    L = s[-1]
    X = self_intersections(C)
    ev = sorted([(a, k) for k, (a, b) in enumerate(X)] + [(b, k) for k, (a, b) in enumerate(X)])
    over = {}
    for m, (pos, k) in enumerate(ev):
        if m % 2 == 0: over[k] = pos
    half = stroke / 2
    reach = reach or 12 * (half + margin)
    whole = LinearRing(C).buffer(half, join_style=1, quad_segs=8)
    band_r = half + margin
    # arc-length positions of all passages through crossings: a cut (or band) must never extend past
    # the midpoint to the neighbouring passage along the same strand, where the strand may be on top
    pas = np.sort([np.interp(p, np.arange(n + 1), s) for ab in X for p in ab])
    def room(sp):
        i = np.searchsorted(pas, sp); prev = pas[i - 1] if i > 0 else pas[-1] - L
        j = np.searchsorted(pas, sp, side='right'); nxt = pas[j] if j < len(pas) else pas[0] + L
        prev = prev if prev < sp - 1e-6 else (pas[i - 2] if i > 1 else pas[-2] - L)
        return (sp - prev) / 2, (nxt - sp) / 2
    cuts = []
    for k, (a, b) in enumerate(X):
        po = over[k]; pu = b if po == a else a
        so = np.interp(po, np.arange(n + 1), s); su = np.interp(pu, np.arange(n + 1), s)
        O, _ = _arc_window(C, s, so, -reach, reach)
        U, tu = _arc_window(C, s, su, -reach, reach)
        Oline = LineString(O)
        ub, ua = room(su)                                     # allowed extent of the cut along the under-strand
        ob, oa = room(so)                                     # ... and of the band along the over-strand
        # walk out from the crossing along the under-strand while its stroke still touches the band
        dist = shapely.distance(Oline, shapely.points(U))
        c = len(U) // 2; lim = band_r + half
        i0 = c
        while i0 > 0 and dist[i0 - 1] < lim: i0 -= 1
        i1 = c
        while i1 < len(U) - 1 and dist[i1 + 1] < lim: i1 += 1
        i0 = max(0, i0 - 2); i1 = min(len(U) - 1, i1 + 2)
        ds = tu - su                                          # arc offset of each window point from the crossing
        while i0 < c and ds[i0] < -ub: i0 += 1
        while i1 > c and ds[i1] > ua: i1 -= 1
        under_piece = LineString(U[i0:i1 + 1]).buffer(half + 0.3, cap_style=2, join_style=1)
        # the over-strand band, only as long as needed around this crossing
        ext = (tu[i1] - tu[i0]) / 2 + 2 * band_r
        Ob, _ = _arc_window(C, s, so, -min(ext, ob), min(ext, oa))
        band = LineString(Ob).buffer(band_r, cap_style=2, join_style=1)
        over_piece = LineString(Ob).buffer(half, cap_style=2, join_style=1)
        cuts.append(under_piece.intersection(band).difference(over_piece))
    return whole.difference(unary_union(cuts))

def _corners(P, min_deg=8.0):
    """indices of the sharp corners of a closed polygon: vertices with a turn of at least min_deg
    whose neighbours are nearly straight (a corner is a single kink; a tight curve turns gradually)"""
    v1 = P - np.roll(P, 1, 0); v2 = np.roll(P, -1, 0) - P
    ang = np.degrees(np.abs(np.arctan2(v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0], (v1 * v2).sum(1))))
    nb = np.maximum(np.roll(ang, 1), np.roll(ang, -1))
    return list(np.nonzero((ang >= min_deg) & (ang > 3 * nb))[0])

# ---------------------------------------------------------------------------------------------
# Adaptive cubic Bézier fitting (P. J. Schneider, "An Algorithm for Automatically Fitting Digitized
# Curves", Graphics Gems, 1990): one cubic per stretch where possible, split only where the fit
# would deviate from the points by more than the tolerance.
# ---------------------------------------------------------------------------------------------
def _bez(ctrl, t):
    t = np.asarray(t)[:, None]; mt = 1 - t
    return mt**3 * ctrl[0] + 3 * mt**2 * t * ctrl[1] + 3 * mt * t**2 * ctrl[2] + t**3 * ctrl[3]

def _bez_d1(ctrl, t):
    t = np.asarray(t)[:, None]; mt = 1 - t
    return 3 * mt**2 * (ctrl[1] - ctrl[0]) + 6 * mt * t * (ctrl[2] - ctrl[1]) + 3 * t**2 * (ctrl[3] - ctrl[2])

def _bez_d2(ctrl, t):
    t = np.asarray(t)[:, None]
    return 6 * (1 - t) * (ctrl[2] - 2 * ctrl[1] + ctrl[0]) + 6 * t * (ctrl[3] - 2 * ctrl[2] + ctrl[1])

def _fit_one(P, u, t0, t1):
    """least-squares cubic with fixed end points and end tangent directions t0, t1"""
    A1 = t0[None, :] * (3 * u * (1 - u)**2)[:, None]
    A2 = t1[None, :] * (3 * u**2 * (1 - u))[:, None]
    C = np.array([[np.sum(A1 * A1), np.sum(A1 * A2)], [np.sum(A1 * A2), np.sum(A2 * A2)]])
    base = _bez(np.array([P[0], P[0], P[-1], P[-1]]), u)
    X = np.array([np.sum(A1 * (P - base)), np.sum(A2 * (P - base))])
    det = C[0, 0] * C[1, 1] - C[0, 1] ** 2
    seg = np.linalg.norm(P[-1] - P[0])
    if abs(det) > 1e-12:
        a1 = (X[0] * C[1, 1] - X[1] * C[0, 1]) / det; a2 = (C[0, 0] * X[1] - C[0, 1] * X[0]) / det
    else:
        a1 = a2 = seg / 3
    if a1 < 1e-6 * seg or a2 < 1e-6 * seg: a1 = a2 = seg / 3       # degenerate: fall back to thirds
    return np.array([P[0], P[0] + a1 * t0, P[-1] + a2 * t1, P[-1]])

def _reparam(ctrl, P, u):
    """one Newton step per point towards the closest point on the curve"""
    d = _bez(ctrl, u) - P; d1 = _bez_d1(ctrl, u); d2 = _bez_d2(ctrl, u)
    num = np.sum(d * d1, 1); den = np.sum(d1 * d1, 1) + np.sum(d * d2, 1)
    with np.errstate(divide='ignore', invalid='ignore'):
        un = np.where(np.abs(den) > 1e-12, u - num / den, u)
    return np.clip(un, 0, 1)

def _fit_cubics(P, t0, t1, tol, depth=0):
    """list of cubics (4x2 arrays) through points P (open stretch), end tangents t0 (out of P[0]), t1 (into P[-1], reversed)"""
    if len(P) == 2:
        dist = np.linalg.norm(P[1] - P[0]) / 3
        return [np.array([P[0], P[0] + dist * t0, P[1] + dist * t1, P[1]])]
    d = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(P, axis=0).T))]); u = d / d[-1]
    ctrl = _fit_one(P, u, t0, t1)
    for _ in range(4):
        err = np.hypot(*(_bez(ctrl, u) - P).T); i = int(np.argmax(err))
        if err[i] <= tol: return [ctrl]
        u = _reparam(ctrl, P, u); ctrl = _fit_one(P, u, t0, t1)
    err = np.hypot(*(_bez(ctrl, u) - P).T); i = int(np.argmax(err))
    if err[i] <= tol or depth > 30: return [ctrl]
    i = min(max(i, 1), len(P) - 2)                                   # split at the worst point
    tc = P[i - 1] - P[i + 1]; tc /= (np.linalg.norm(tc) + 1e-12)
    return _fit_cubics(P[:i + 1], t0, tc, tol, depth + 1) + _fit_cubics(P[i:], -tc, t1, tol, depth + 1)

def _unit(v): return v / (np.linalg.norm(v) + 1e-12)

def _ring_to_bezier(xy, tol=0.1, ox=0.0, oy=0.0):
    """closed polygon ring -> SVG path of cubic Béziers fitted within `tol` px. Sharp corners (the
    ends of the gap cuts) stay sharp; between corners the fit keeps a continuous tangent."""
    P = np.asarray(xy, float)[:-1]
    keep = np.hypot(*(P - np.roll(P, 1, 0)).T) > 1e-9; P = P[keep]
    n = len(P)
    if n < 4: return 'M' + ' L'.join(f'{x - ox:.2f},{y - oy:.2f}' for x, y in P) + ' Z'
    corners = _corners(P)
    k = 3                                                            # points used for end tangents
    if corners:
        P = np.roll(P, -corners[0], 0); corners = sorted((c - corners[0]) % n for c in corners)
        stretches = [P[c0:c1 + 1] for c0, c1 in zip(corners, corners[1:])] + [np.vstack([P[corners[-1]:], P[:1]])]
        cubics = []
        for S in stretches:
            if len(S) < 2: continue
            t0 = _unit(S[min(k, len(S) - 1)] - S[0]); t1 = _unit(S[max(-k - 1, -len(S))] - S[-1])
            cubics += _fit_cubics(S, t0, t1, tol)
    else:                                                            # smooth closed loop: split in two halves
        h = n // 2
        S1, S2 = P[:h + 1], np.vstack([P[h:], P[:1]])
        ta = _unit(P[1] - P[-1]); tb = _unit(P[h + 1] - P[h - 1])
        cubics = _fit_cubics(S1, ta, -tb, tol) + _fit_cubics(S2, tb, -ta, tol)
    f = lambda p: f'{p[0] - ox:.2f},{p[1] - oy:.2f}'
    out = [f'M{f(cubics[0][0])}'] + [f'C{f(c[1])} {f(c[2])} {f(c[3])}' for c in cubics]
    return ' '.join(out) + ' Z'


def svg(C, width_px, height_px, offset=(0, 0), stroke=DEFAULT_STROKE, gap=None, ink='#1a1a1a', bg='#f6f0dc', with_bg=True):
    """the knot as an SVG: one filled path of cubic Béziers (fitted within 0.1 px of the exact
    outline; sharp corners at the gap cuts kept), gaps cut geometrically (see knot_shape).
    `gap` = margin on each side of an over-strand, in multiples of the stroke width (default 1.1)."""
    margin = stroke * (1.1 if gap is None else gap)
    shape = knot_shape(C, stroke=stroke, margin=margin)
    rings = [r for p in getattr(shape, 'geoms', [shape]) for r in [p.exterior, *p.interiors]]
    d = ' '.join(_ring_to_bezier(np.asarray(r.coords), ox=offset[0], oy=offset[1]) for r in rings)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width_px:.0f} {height_px:.0f}" '
           f'width="{width_px:.0f}" height="{height_px:.0f}">', f'<!-- stroke={stroke:g} margin={margin:g} -->']
    if with_bg: out.append(f'<rect width="100%" height="100%" fill="{bg}"/>')
    out.append(f'<path d="{d}" fill="{ink}" fill-rule="evenodd"/>')
    out.append('</svg>')
    return '\n'.join(out), len(getattr(shape, 'geoms', [shape]))   # number of separate pieces (one per crossing)
