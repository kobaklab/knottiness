"""Trace one knot crop -> validated diagram + smooth centreline."""
import numpy as np
from scipy import ndimage
from skimage.morphology import convex_hull_image
from .graph import skeleton_graph, build_diagram
from .codes import partitions as code_partitions, parse
from .sources import S

def isolate_knot(mask):
    lab, n = ndimage.label(mask, structure=np.ones((3, 3)))
    if n == 0: return mask
    sizes = ndimage.sum(mask, lab, range(1, n + 1)); big = 1 + int(np.argmax(sizes))
    hull = ndimage.binary_dilation(convex_hull_image(lab == big), iterations=3)
    keep = [i + 1 for i in range(n) if (hull & (lab == i + 1)).sum() >= 0.6 * sizes[i] and sizes[i] > 4]
    return np.isin(lab, keep)

def parse_partitions(p):
    """Tait's partition pair as transcribed ('5333/43322', or '332*' for a barred = amphicheiral one)
    -> unordered pair of sorted partitions, comparable with a traced diagram's classes"""
    pair = [p.rstrip('*')] * 2 if p.endswith('*') else p.split('/')
    return sorted(tuple(sorted((int(c) for c in q), reverse=True)) for q in pair)

def trace(mask, code=None, partitions=None, crossings=10):
    """Trace one knot and validate it: one strand, the expected number of crossings, and the expected
    corner counts of the two mesh classes: from a Tait region code of the tenfold census (code, which
    also fixes the class of the outer region), or from a partition pair (partitions, as transcribed)."""
    report = {}
    G = skeleton_graph(isolate_knot(mask))
    G.prune_spurs(0.05 * S); G.drop_isolated_nodes()
    G.merge_junctions(0.20 * S)          # re-join crossings the skeleton split in two, before bridging,
    G.dissolve_deg2()                    # so a finished crossing never accepts a bridge from a stray dot
    G.bridge_gaps(0.10 * S, 0.04 * S)
    G.keep_largest_component()
    G.prune_spurs(0.05 * S)
    G.merge_junctions(0.20 * S)
    G.dissolve_deg2(); G.drop_isolated_nodes()
    for _ in range(2):                                  # artefact clean-up, then re-tidy
        G.remove_monogons(0.5 * S)
        G.collapse_tiny_bigons(0.05 * S)
        G.prune_spurs(0.05 * S)
        G.merge_junctions(0.20 * S)
        G.dissolve_deg2(); G.drop_isolated_nodes()
    report['crossings'] = len(G.nodes)
    D, problems = build_diagram(G, 0.07 * S)
    report['problems'] = problems
    if D is None:
        report['ok'] = False; report['warnings'] = []; return report, G, None
    report['strands'] = len(D['strands'])
    report['classes'] = D['classes']
    report['outer_class'] = D['outer_class']
    report['warnings'] = []
    if code is not None:
        report['expected'] = code_partitions(code)
        second = tuple(sorted(parse(code)[1][1], reverse=True))
        report['outer_ok'] = D['outer_class'] == second
        if not report['outer_ok']: report['warnings'] = ['outer region not in the class of the 2nd letter (Tait\'s convention)']
    else:
        report['expected'] = parse_partitions(partitions)
    checks = [len(G.nodes) == crossings, len(D['strands']) == 1, D['classes'] == report['expected'], not problems]
    if len(G.nodes) != crossings: problems.append(f'{len(G.nodes)} crossings')
    report['ok'] = all(checks)
    if len(D['strands']) != 1: problems.append(f"{len(D['strands'])} strands")
    if D['classes'] != report['expected']: problems.append('region code mismatch')
    curve = centreline(G, D['strands'][0]) if len(D['strands']) == 1 else None
    return report, G, curve

def raw_path(G, strand, trim):
    """concatenate the strand's skeleton polylines, cutting away the distorted junction zone at each crossing"""
    parts = []
    for (k, i) in strand:
        pl = G.edges[k]['pts'] if i == 0 else G.edges[k]['pts'][::-1]
        s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(pl, axis=0).T))])
        L = s[-1]; t0, t1 = min(trim, 0.3 * L), max(L - trim, 0.7 * L)
        keep = (s >= t0) & (s <= t1)
        parts.append(pl[keep] if keep.sum() >= 2 else pl[[0, -1]].mean(0, keepdims=True))
    return np.vstack(parts)

def resample_closed(P, step):
    Q = np.vstack([P, P[:1]])
    s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(Q, axis=0).T))])
    n = max(50, int(s[-1] / step))
    u = np.linspace(0, s[-1], n, endpoint=False)
    return np.stack([np.interp(u, s, Q[:, 0]), np.interp(u, s, Q[:, 1])], 1)

def centreline(G, strand, trim=0.05 * S, tol=0.006 * S, out_step=1.0):
    """periodic cubic smoothing spline through the traced path.
    tol = allowed RMS deviation from the traced skeleton (px at working scale; 0.006*S ~ 1.9 px)"""
    from scipy.interpolate import splprep, splev
    R = resample_closed(raw_path(G, strand, trim), 3.0)
    tck, _ = splprep([R[:, 0], R[:, 1]], s=len(R) * tol ** 2, per=1)
    L = np.sum(np.hypot(*np.diff(np.vstack([R, R[:1]]), axis=0).T))
    u = np.linspace(0, 1, int(L / out_step), endpoint=False)
    return np.array(splev(u, tck)).T
