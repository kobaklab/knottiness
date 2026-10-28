"""Combinatorics of a traced knot diagram, computed from its smooth centreline alone.

faces(curve)  -> list of faces, each a list of crossing ids around it
flaps(curve)  -> Kirkman's flap signature {e: F_e}: a flap of e loops is a chain of e bigons
                 (two-sided regions) linked through shared crossings, i.e. a twist of e+1 crossings."""
import math
import numpy as np
from collections import Counter
from .render import densify, self_intersections

def _tangent(C, p):
    n = len(C); i = int(p) % n
    d = C[(i + 1) % n] - C[(i - 1) % n]
    return d / np.linalg.norm(d)

def faces(curve):
    C = densify(curve, 1.0); X = self_intersections(C)
    # passages along the curve: (param, crossing id)
    P = sorted([(a, k) for k, (a, b) in enumerate(X)] + [(b, k) for k, (a, b) in enumerate(X)])
    m = len(P)
    # edge i runs from passage i to passage i+1; its two ends ("half-edges") with outgoing directions
    ends = {}            # crossing -> list of (edge, end) with end 0 = start of edge, 1 = end of edge
    ang = {}
    for i, (p, k) in enumerate(P):
        t = _tangent(C, p)
        ends.setdefault(k, []).append((i, 0)); ang[(i, 0)] = math.atan2(t[1], t[0])         # leaves along +t
        j = (i - 1) % m
        ends[k].append((j, 1)); ang[(j, 1)] = math.atan2(-t[1], -t[0])                     # edge j arrives, points back along -t
    rot = {k: sorted(v, key=lambda h: ang[h]) for k, v in ends.items()}
    cross_of = {}
    for k, v in ends.items():
        for h in v: cross_of[h] = k
    seen, out = set(), []
    for start in [(i, e) for i in range(m) for e in (0, 1)]:
        if start in seen: continue
        f, h = [], start
        while h not in seen:
            seen.add(h); f.append(cross_of[h])
            arrive = (h[0], 1 - h[1])                    # walk along the edge to its other end
            r = rot[cross_of[arrive]]; h = r[(r.index(arrive) + 1) % len(r)]
        out.append(f)
    return out

def flaps(curve):
    """{e: number of flaps of e loops}"""
    F = faces(curve)
    bigons = [frozenset(f) for f in F if len(f) == 2]
    # link bigons sharing a crossing; flaps = connected components
    parent = list(range(len(bigons)))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i in range(len(bigons)):
        for j in range(i + 1, len(bigons)):
            if bigons[i] & bigons[j]: parent[find(i)] = find(j)
    sizes = Counter(find(i) for i in range(len(bigons)))
    return dict(Counter(sizes.values()))

# Kirkman 1885, lists of ten-crossing unifilars: list letter -> flap signature {e: F_e}
KIRKMAN_LISTS = {
    'A': {1: 1}, 'B': {1: 2}, 'C': {1: 3}, 'D': {1: 4}, 'E': {1: 5},
    'F': {2: 1}, 'G': {2: 1, 1: 1}, 'H': {2: 1, 1: 2}, 'I': {2: 1, 1: 3},
    'J': {2: 2}, 'K': {2: 2, 1: 1}, 'L': {2: 2, 1: 2}, 'M': {2: 3},
    'N': {3: 1, 1: 1}, 'P': {3: 1, 1: 2}, 'Q': {3: 1, 1: 3}, 'R': {3: 1, 2: 1},
    'S': {3: 1, 2: 1, 1: 1}, 'T': {3: 1, 2: 2}, 'U': {3: 2}, 'V': {4: 1, 1: 1},
    'W': {4: 1, 1: 2}, 'X': {4: 1, 2: 1}, 'Y': {4: 1, 2: 1, 1: 1}, 'Z': {4: 1, 3: 1},
    'Δ': {5: 1, 1: 1}, 'Θ': {5: 1, 2: 1}, 'Ξ': {5: 1, 3: 1}, 'Σ': {6: 1, 1: 1}, 'Φ': {7: 1, 1: 1},
}
KIRKMAN_LIST_LENGTH = dict(A=3, B=36, C=79, D=47, E=3, F=2, G=12, H=62, I=30, J=4, K=21, L=8, M=2,
                           N=5, P=16, Q=2, R=3, S=8, T=2, U=1, V=3, W=4, X=1, Y=3, Z=1,
                           **{'Δ': 1, 'Θ': 1, 'Ξ': 1, 'Σ': 1, 'Φ': 1})
