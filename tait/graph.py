"""Skeleton -> planar 4-valent graph -> knot diagram, with validation."""
import numpy as np
from skimage.morphology import skeletonize
import math

N8 = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]

def skeleton_graph(mask):
    sk = skeletonize(mask)
    pts = set(zip(*np.nonzero(sk)))
    nb = {p: [(p[0]+dy, p[1]+dx) for dy, dx in N8 if (p[0]+dy, p[1]+dx) in pts] for p in pts}
    nodepix = {p for p in pts if len(nb[p]) != 2}
    # cluster node pixels
    cid, nodes = {}, {}
    for p in nodepix:
        if p in cid: continue
        k = len(nodes); stack = [p]; cid[p] = k; members = []
        while stack:
            q = stack.pop(); members.append(q)
            for r in nb[q]:
                if r in nodepix and r not in cid:
                    cid[r] = k; stack.append(r)
        m = np.array(members, float)
        nodes[k] = m.mean(0)[::-1]          # (x, y)
    edges, visited = {}, set()
    for p in nodepix:
        for q in nb[p]:
            if q in nodepix or q in visited: continue
            path = [p, q]; visited.add(q); prev, cur = p, q
            while True:
                nxt = [r for r in nb[cur] if r != prev and r not in path[-3:]]
                if not nxt: break
                end = [r for r in nxt if r in nodepix]
                if end:
                    path.append(end[0]); break
                r = nxt[0]
                if r in visited: break
                visited.add(r); path.append(r); prev, cur = cur, r
            if path[-1] in nodepix:
                a, b = cid[path[0]], cid[path[-1]]
                pl = np.array(path, float)[:, ::-1]
                pl = np.vstack([nodes[a], pl[1:-1], nodes[b]])
                edges[len(edges)] = dict(a=a, b=b, pts=pl)
    return Graph(nodes, edges)

def plen(pl): return float(np.sum(np.hypot(*np.diff(pl, axis=0).T))) if len(pl) > 1 else 0.0

class Graph:
    def __init__(self, nodes, edges):
        self.nodes = dict(nodes); self.edges = dict(edges)
        self.eid = max(edges, default=-1) + 1
    def deg(self, n): return sum((e['a'] == n) + (e['b'] == n) for e in self.edges.values())
    def inc(self, n): return [k for k, e in self.edges.items() if e['a'] == n or e['b'] == n]
    def add_edge(self, a, b, pts):
        self.edges[self.eid] = dict(a=a, b=b, pts=pts); self.eid += 1
    def oriented(self, k, n):
        """edge polyline starting at node n"""
        e = self.edges[k]; return e['pts'] if e['a'] == n else e['pts'][::-1]
    def end_dir(self, k, n, d):
        pl = self.oriented(k, n)
        s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(pl, axis=0).T))])
        t = min(d, s[-1] * 0.5) if self.edges[k]['a'] != self.edges[k]['b'] else min(d, s[-1] * 0.3)
        p = np.array([np.interp(t, s, pl[:, 0]), np.interp(t, s, pl[:, 1])])
        v = p - self.nodes[n]
        return v / (np.linalg.norm(v) + 1e-9)

    # ---------- clean-up operations ----------
    def dissolve_deg2(self):
        changed = True
        while changed:
            changed = False
            for n in list(self.nodes):
                inc = self.inc(n)
                if len(inc) == 2 and self.deg(n) == 2:
                    k1, k2 = inc
                    p1 = self.oriented(k1, n)[::-1]; p2 = self.oriented(k2, n)
                    o1 = self.edges[k1]['a'] if self.edges[k1]['b'] == n else self.edges[k1]['b']
                    o2 = self.edges[k2]['b'] if self.edges[k2]['a'] == n else self.edges[k2]['a']
                    del self.edges[k1], self.edges[k2], self.nodes[n]
                    self.add_edge(o1, o2, np.vstack([p1, p2[1:]])); changed = True; break
    def prune_spurs(self, L):
        changed = True
        while changed:
            changed = False
            for k, e in list(self.edges.items()):
                a, b = e['a'], e['b']
                if a == b: continue
                da, db = self.deg(a), self.deg(b)
                if (da == 1 and db >= 3 or db == 1 and da >= 3) and plen(e['pts']) < L:
                    del self.edges[k]; del self.nodes[a if da == 1 else b]; changed = True
            self.dissolve_deg2()
    def drop_isolated_nodes(self):
        for n in list(self.nodes):
            if self.deg(n) == 0: del self.nodes[n]
    def bridge_gaps(self, gmax, dir_d):
        """join loose ends to each other or to nearby 3-junctions, greedily by distance"""
        while True:
            ends = [n for n in self.nodes if self.deg(n) == 1]
            j3 = [n for n in self.nodes if self.deg(n) == 3]
            best = None
            for i, u in enumerate(ends):
                du = -self.end_dir(self.inc(u)[0], u, dir_d)          # outward direction
                short_u = plen(self.edges[self.inc(u)[0]]['pts']) < 6
                for v in ends[i+1:] + j3:
                    vec = self.nodes[v] - self.nodes[u]; dist = np.linalg.norm(vec)
                    if dist > gmax or dist < 1e-6: continue
                    if self.inc(v) and self.inc(u)[0] in self.inc(v) and self.deg(v) == 1: continue
                    c1 = 1 if short_u else float(du @ vec) / dist
                    if self.deg(v) == 1:
                        dv = -self.end_dir(self.inc(v)[0], v, dir_d)
                        short_v = plen(self.edges[self.inc(v)[0]]['pts']) < 6
                        c2 = 1 if short_v else float(dv @ -vec) / dist
                    else:
                        c2 = 1
                    if c1 > 0.6 and c2 > 0.6:
                        score = dist * (2.2 - c1 - c2)
                        if best is None or score < best[0]: best = (score, u, v)
            if best is None: break
            _, u, v = best
            self.add_edge(u, v, np.vstack([self.nodes[u], self.nodes[v]]))
        self.dissolve_deg2()
    def keep_largest_component(self):
        adj = {n: set() for n in self.nodes}
        for e in self.edges.values(): adj[e['a']].add(e['b']); adj[e['b']].add(e['a'])
        seen, comps = set(), []
        for n in self.nodes:
            if n in seen: continue
            stack, comp = [n], set([n]); seen.add(n)
            while stack:
                q = stack.pop()
                for r in adj[q]:
                    if r not in seen: seen.add(r); comp.add(r); stack.append(r)
            L = sum(plen(e['pts']) for e in self.edges.values() if e['a'] in comp)
            comps.append((L, comp))
        if not comps: return
        keep = max(comps, key=lambda c: c[0])[1]
        for k, e in list(self.edges.items()):
            if e['a'] not in keep: del self.edges[k]
        for n in list(self.nodes):
            if n not in keep: del self.nodes[n]
    def remove_monogons(self, Lmax):
        """delete small loops from a crossing back to itself: Tait's (reduced) diagrams have no
        1-sided regions, so these are artefacts, e.g. the bowl of a label letter touching the knot"""
        for k, e in list(self.edges.items()):
            if e['a'] == e['b'] and plen(e['pts']) < Lmax: del self.edges[k]
        self.drop_isolated_nodes(); self.dissolve_deg2()

    def collapse_tiny_bigons(self, Lmax):
        """two crossings joined by two very short edges = one crossing split by an ink blot"""
        changed = True
        while changed:
            changed = False
            pairs = {}
            for k, e in self.edges.items():
                if e['a'] != e['b'] and plen(e['pts']) < Lmax:
                    pairs.setdefault(tuple(sorted((e['a'], e['b']))), []).append(k)
            for (u, v), ks in pairs.items():
                if len(ks) >= 2:
                    for k in ks[:2]: del self.edges[k]
                    self.nodes[u] = (self.nodes[u] + self.nodes[v]) / 2
                    for e in self.edges.values():
                        if e['a'] == v: e['a'] = u
                        if e['b'] == v: e['b'] = u
                    del self.nodes[v]; changed = True; break
        self.drop_isolated_nodes(); self.dissolve_deg2()

    def merge_junctions(self, Lmax):
        """pair up 3-valent junctions (a crossing split in two by the skeleton) via their shortest edge"""
        while True:
            cand = []
            for k, e in self.edges.items():
                a, b = e['a'], e['b']
                if a != b and self.deg(a) == 3 and self.deg(b) == 3:
                    L = plen(e['pts'])
                    if L < Lmax: cand.append((L, k))
            if not cand: break
            _, k = min(cand); e = self.edges.pop(k)
            a, b = e['a'], e['b']
            self.nodes[a] = (self.nodes[a] + self.nodes[b]) / 2
            for kk, ee in self.edges.items():
                if ee['a'] == b: ee['a'] = a
                if ee['b'] == b: ee['b'] = a
            del self.nodes[b]

def build_diagram(G, dir_d):
    """At each 4-valent node pair edge-ends into straight-through strands; trace strands and faces."""
    problems = []
    degs = {n: G.deg(n) for n in G.nodes}
    if any(d != 4 for d in degs.values()):
        problems.append('node degrees ' + ''.join(str(d) for d in sorted(degs.values())))
        return None, problems
    ends = {n: [] for n in G.nodes}          # (edge, endindex, direction)
    for k, e in G.edges.items():
        ends[e['a']].append((k, 0)); ends[e['b']].append((k, 1))
    def direc(k, i):
        e = G.edges[k]; pl = e['pts'] if i == 0 else e['pts'][::-1]
        n = e['a'] if i == 0 else e['b']
        s = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(pl, axis=0).T))])
        t = min(dir_d, s[-1] * (0.3 if e['a'] == e['b'] else 0.5))
        p = np.array([np.interp(t, s, pl[:, 0]), np.interp(t, s, pl[:, 1])])
        v = p - G.nodes[n]; return v / (np.linalg.norm(v) + 1e-9)
    rot, pair = {}, {}
    for n, es in ends.items():
        D = {h: direc(*h) for h in es}
        rot[n] = sorted(es, key=lambda h: math.atan2(D[h][1], D[h][0]))   # clockwise on screen
        r = rot[n]
        # straight-through = opposite in cyclic order; check it is also the most anti-parallel pairing
        opp = [(r[0], r[2]), (r[1], r[3])]
        best = min([[(r[0], r[1]), (r[2], r[3])], [(r[0], r[2]), (r[1], r[3])], [(r[0], r[3]), (r[1], r[2])]],
                   key=lambda P: sum(float(D[x] @ D[y]) for x, y in P))
        if sorted(best) != sorted(opp):
            problems.append(f'node {n}: strands touch rather than cross')
        for x, y in opp: pair[x] = y; pair[y] = x
    # strands
    used, strands = set(), []
    for k0 in G.edges:
        if k0 in used: continue
        seq, h = [], (k0, 0)
        while h[0] not in used:
            k, i = h; used.add(k); seq.append(h)
            h = pair[(k, 1 - i)]          # arrive at the far end, continue straight through
        strands.append(seq)
    # faces
    darts = {(k, i) for k in G.edges for i in (0, 1)}
    face_of, faces = {}, []
    for d0 in sorted(darts):
        if d0 in face_of: continue
        f, d = [], d0
        while d not in face_of:
            face_of[d] = len(faces); f.append(d)
            k, i = d; arrive = (k, 1 - i); e = G.edges[k]
            n = e['b'] if i == 0 else e['a']
            r = rot[n]; d = r[(r.index(arrive) + 1) % len(r)]
        faces.append(f)
    # checkerboard colouring
    col = {0: 0}; queue = [0]; ok = True
    while queue:
        f = queue.pop()
        for (k, i) in faces[f]:
            g = face_of[(k, 1 - i)]
            if g not in col: col[g] = 1 - col[f]; queue.append(g)
            elif col[g] == col[f] and g != f: ok = False
    if not ok: problems.append('faces not 2-colourable')
    # outer face = the face whose boundary polygon encloses the largest area
    def area(f):
        P = np.vstack([G.edges[k]['pts'] if i == 0 else G.edges[k]['pts'][::-1] for (k, i) in f])
        return 0.5 * abs(np.dot(P[:, 0], np.roll(P[:, 1], -1)) - np.dot(P[:, 1], np.roll(P[:, 0], -1)))
    outer = max(range(len(faces)), key=lambda f: area(faces[f]))
    outer_class = tuple(sorted((len(faces[f]) for f in range(len(faces)) if col.get(f) == col[outer]), reverse=True))
    classes = sorted(tuple(sorted((len(faces[f]) for f in range(len(faces)) if col.get(f) == c), reverse=True)) for c in (0, 1))
    return dict(strands=strands, pair=pair, rot=rot, faces=faces, classes=classes, outer_class=outer_class), problems
