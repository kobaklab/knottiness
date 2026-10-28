"""Plate images from the different scans: loading, ink detection, knot segmentation.

All tracing happens at a common working scale S (median knot height in pixels), so
thresholds are expressed as fractions of S and behave the same for every source."""
import numpy as np
from PIL import Image
from scipy import ndimage
from . import TENFOLD, SEVEN_ORDERS

S = 314.0   # working scale: median knot height (px) after normalisation

# plate -> its poster (where its source files are)
PLATES = {'LXXX': TENFOLD, 'LXXXI': TENFOLD, 'XLIV': SEVEN_ORDERS}

# name -> settings shared by both tenfold plates (Pl. LXXX, LXXXI)
SOURCES = {
    'HT': dict(desc='HathiTrust (Google scan, Penn State copy), bitonal', threshold='fixed', knot_h=314),
    'KA': dict(desc='Knot Atlas PNG (2005), bitonal',                  threshold='fixed', knot_h=150),
    'IA': dict(desc='Internet Archive camera scan, colour, 350 ppi',     threshold='adaptive', knot_h=184,
               rotate=-90, crop=(100, 1300, 2780, 5100)),   # crop = page area after rotation (x0, y0, x1, y1)
}
# plate -> its own settings, where they differ from SOURCES
PLATE_SOURCES = {
    'XLIV': {
        'PDF': dict(desc='Cambridge Core PDF of the paper (ABBYY, 2011), plate page: bitonal 300 ppi',
                    threshold='fixed', knot_h=170, pdf_page=17),
        'HT': dict(desc='HathiTrust (Google scan, Penn State copy), 600 dpi, bitonal', threshold='fixed', knot_h=343),
        'KA': dict(desc='Knot Atlas PNG, bitonal', threshold='fixed', knot_h=163),
        'IA': dict(desc='Internet Archive camera scan, colour', threshold='adaptive', knot_h=199,
                   rotate=-90, crop=(100, 1200, 2800, 5000)),
    },
}
FILES = {
    ('HT', 'LXXX'): 'pst_000067405572-seq_321.png',
    ('HT', 'LXXXI'): 'pst_000067405572-seq_323.png',
    ('KA', 'LXXX'): 'Tait__s_table_of_10_crossing_knots_-_1.png',
    ('KA', 'LXXXI'): 'Tait__s_table_of_10_crossing_knots_-_2.png',
    ('IA', 'LXXX'): 'transactionsofro321887roy_orig_0695.jp2',
    ('IA', 'LXXXI'): 'transactionsofro321887roy_orig_0697.jp2',
    ('PDF', 'XLIV'): 's0080456800026806.pdf',
    ('HT', 'XLIV'): 'pst_000067405565-seq_443.png',
    ('KA', 'XLIV'): 'Tait__s_table_of_knots_to_7_crossings.png',
    ('IA', 'XLIV'): 'transactionsofro321887roy_orig_0449.jp2',
}
PRIORITY = ['HT', 'KA', 'IA']   # first source whose trace validates is used
PLATE_PRIORITY = {'XLIV': ['PDF', 'HT', 'KA', 'IA']}
# accepted knot boxes: (min, max) width as fractions of the knot height (XLIV has some wide knots: 9 Bl, 9 Gz)
BOX_W = {'XLIV': (0.4, 2.0)}

def config(src, plate=None):
    """settings of a source for a plate (default: the tenfold plates)"""
    return PLATE_SOURCES.get(plate, {}).get(src) or SOURCES[src]

def priority(plate=None):
    return PLATE_PRIORITY.get(plate, PRIORITY)

def source_path(src, plate):
    return PLATES[plate].sources / FILES[(src, plate)]

def load_gray(src, plate):
    cfg = config(src, plate)
    if cfg.get('pdf_page'):                          # the plate as the image embedded in a PDF page
        from pypdf import PdfReader
        im = PdfReader(source_path(src, plate)).pages[cfg['pdf_page'] - 1].images[0].image.convert('L')
    else:
        im = Image.open(source_path(src, plate)).convert('L')
    if cfg.get('rotate'): im = im.rotate(cfg['rotate'], expand=True)
    g = np.array(im).astype(float)
    if cfg.get('crop'):
        x0, y0, x1, y1 = cfg['crop']; g = g[y0:y1, x0:x1]
    return g

def ink_mask(g, mode):
    if mode == 'fixed':
        return g < 128
    bg = ndimage.uniform_filter(g, 61)
    return g < bg - 35

def find_knots(src, plate):
    """-> (grayscale page, rows) where rows is a list of rows, each a list of knot boxes
    (y0, y1, x0, x1) sorted left to right; rows sorted top to bottom."""
    cfg = config(src, plate); kh = cfg['knot_h']
    g = load_gray(src, plate); ink = ink_mask(g, cfg['threshold'])
    ink[int(0.95 * g.shape[0]):] = False                     # footer / scanner watermark
    # knot bodies from large ink pieces only, so labels can't glue neighbouring knots together
    lab0, n0 = ndimage.label(ink, structure=np.ones((3, 3)))
    big = np.zeros(n0 + 1, bool)
    for i, s0 in enumerate(ndimage.find_objects(lab0)):
        if max(s0[0].stop - s0[0].start, s0[1].stop - s0[1].start) > 0.3 * kh: big[i + 1] = True
    grp = ndimage.binary_dilation(big[lab0], iterations=max(2, int(0.03 * kh)))
    lab, _ = ndimage.label(grp)
    boxes = []
    for s in ndimage.find_objects(lab):
        h = s[0].stop - s[0].start; w = s[1].stop - s[1].start
        wmin, wmax = BOX_W.get(plate, (0.4, 1.15))
        if 0.75 * kh < h < 1.45 * kh and wmin * kh < w < wmax * kh:
            boxes.append((s[0].start, s[0].stop, s[1].start, s[1].stop))
    boxes.sort(key=lambda b: (b[0] + b[1]) / 2)
    rows, cur = [], []
    for b in boxes:
        if cur and (b[0] + b[1]) / 2 - (cur[-1][0] + cur[-1][1]) / 2 > 0.5 * kh:
            rows.append(cur); cur = []
        cur.append(b)
    rows.append(cur)
    rows = [sorted(r, key=lambda b: b[2]) for r in rows if len(r) >= 6]
    return g, rows

def knot_crop(src, g, box, margin=0.08, plate=None):
    """grayscale crop around a knot, rescaled to the working scale, plus its ink mask"""
    cfg = config(src, plate); kh = cfg['knot_h']
    y0, y1, x0, x1 = box; m = int(margin * kh)
    y0, x0 = max(0, y0 - m), max(0, x0 - m); y1, x1 = min(g.shape[0], y1 + m), min(g.shape[1], x1 + m)
    sub = g[y0:y1, x0:x1]; f = S / kh
    im = Image.fromarray(sub.clip(0, 255).astype('uint8')).resize(
        (int(sub.shape[1] * f), int(sub.shape[0] * f)), Image.BICUBIC)
    gg = np.array(im).astype(float)
    if cfg['threshold'] == 'fixed':
        mask = ndimage.gaussian_filter((gg < 128).astype(float), 1.2) > 0.5
    else:
        bg = ndimage.uniform_filter(gg, int(61 * f) | 1)
        mask = ndimage.gaussian_filter((gg < bg - 30).astype(float), 1.2) > 0.5
    return gg, mask, (x0, y0, f)

def cells(rows, kh):
    """the area belonging to each knot, including its labels: halfway to the neighbouring knots
    in its row and halfway to the adjacent rows. Same structure as rows; boxes (y0, y1, x0, x1)."""
    tops = [np.median([b[0] for b in r]) for r in rows]
    bots = [np.median([b[1] for b in r]) for r in rows]
    out = []
    for i, r in enumerate(rows):
        ytop = (bots[i - 1] + tops[i]) / 2 if i > 0 else tops[i] - 0.35 * kh
        ybot = (bots[i] + tops[i + 1]) / 2 if i + 1 < len(rows) else bots[i] + 0.35 * kh
        row = []
        for j, b in enumerate(r):
            xl = (r[j - 1][3] + b[2]) / 2 if j > 0 else b[2] - 0.35 * kh
            xr = (b[3] + r[j + 1][2]) / 2 if j + 1 < len(r) else b[3] + 0.35 * kh
            row.append((int(ytop), int(ybot), int(xl), int(xr)))
        out.append(row)
    return out

def box_centre(b):
    return np.array([(b[2] + b[3]) / 2, (b[0] + b[1]) / 2])

def align(rows_src, rows_ref, kh_ref):
    """Affine map from one source's page to the reference page, fitted on knots both contain.

    Returns (A, matches): A is a 2x3 matrix with ref_xy = A @ [x, y, 1]; matches maps
    (ref_row, ref_col) -> the source's box for that knot (missing where the source has no counterpart).
    Initial pairs come from rows where both found the same number of knots; the fit is then refined
    on all matched knots."""
    P, Q = [], []
    for r in range(min(len(rows_src), len(rows_ref))):
        if len(rows_src[r]) == len(rows_ref[r]):
            P += [box_centre(b) for b in rows_src[r]]; Q += [box_centre(b) for b in rows_ref[r]]
    if len(P) < 10: return None, {}
    def fit(P, Q):
        P = np.asarray(P); Q = np.asarray(Q)
        M = np.hstack([P, np.ones((len(P), 1))])
        return np.linalg.lstsq(M, Q, rcond=None)[0].T          # 2x3
    A = fit(P, Q)
    src = [b for row in rows_src for b in row]
    mapped = np.array([A @ [*box_centre(b), 1] for b in src])
    matches, P2, Q2 = {}, [], []
    for r, row in enumerate(rows_ref):
        for j, b in enumerate(row):
            d = np.hypot(*(mapped - box_centre(b)).T); i = int(np.argmin(d))
            if d[i] < 0.35 * kh_ref:
                matches[(r, j)] = src[i]; P2.append(box_centre(src[i])); Q2.append(box_centre(b))
    return fit(P2, Q2), matches

