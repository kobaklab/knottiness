"""Contact sheets of Kirkman's designations (top-right labels) for checking census.csv by eye.

  uv run scripts/extract_kirkman.py            # sheets + OCR draft for any EMPTY 'kirkman' cells

output/labels/kirkman_NN.png shows every label as cropped from each scan (HathiTrust | Knot Atlas |
Internet Archive) next to the value in data/census.csv. The values in census.csv were transcribed
by Claude from these sheets (not reproducible by script); OCR (tesseract) of the small
superscripts is too unreliable to use directly. Use the sheets to check the transcription by eye.
Requires the 'tesseract' binary only when there are empty cells to draft."""
import csv, json, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from tait import TENFOLD
from tait.review import font
DATA_DIR, TRACED_DIR, OUTPUT_DIR = TENFOLD.data, TENFOLD.traced, TENFOLD.output
from tait.sources import load_gray, ink_mask, SOURCES

rows = list(csv.DictReader(open(DATA_DIR / 'census.csv', encoding='utf-8')))
grays = {}

def label_crop(rec):
    """top-right label area of a knot in one scan (grayscale), with the knot's own ink removed"""
    s = rec['source']; key = (s, rec['plate'])
    if key not in grays: grays[key] = load_gray(s, rec['plate'])
    g = grays[key]; kh = SOURCES[s]['knot_h']
    cy0, cy1, cx0, cx1 = rec['cell']; by0, by1, bx0, bx1 = rec['box']
    y0, y1 = max(0, cy0, by0 - int(0.22 * kh)), min(g.shape[0], by0 + int(0.14 * kh))
    x0, x1 = max(0, (bx0 + 2 * bx1) // 3), min(g.shape[1], cx1 + int(0.12 * kh))
    sub = g[y0:y1, x0:x1].copy()
    if sub.size == 0: return None
    ink = ink_mask(sub, SOURCES[s]['threshold'])
    lab, n = ndimage.label(ink, structure=np.ones((3, 3)))
    for i, sll in enumerate(ndimage.find_objects(lab)):     # drop knot strands (anything big)
        h, w = sll[0].stop - sll[0].start, sll[1].stop - sll[1].start
        if max(h, w) > 0.22 * kh: sub[lab == i + 1] = 255
    return sub

def ocr(img):
    big = Image.fromarray(img.clip(0, 255).astype('uint8')).resize((img.shape[1] * 3, img.shape[0] * 3), Image.LANCZOS)
    with tempfile.NamedTemporaryFile(suffix='.png') as t:
        big.save(t.name)
        out = subprocess.run(['tesseract', t.name, '-', '--psm', '7', '-c',
                              'tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'],
                             capture_output=True, text=True).stdout
    return ''.join(ch for ch in out if ch.isalnum())

crops = {}                       # seq -> {source: crop}
for row in rows:
    seq = int(row['seq']); acc = TRACED_DIR / f'{seq:03d}.json'
    if not acc.exists(): continue
    crops[seq] = {}
    for src in ('HT', 'KA', 'IA'):
        p = TRACED_DIR / 'candidates' / f'{seq:03d}_{src}.json'
        if p.exists():
            c = label_crop(json.load(open(p)))
            if c is not None and c.size: crops[seq][src] = c
    if not row['kirkman'] and 'no Kirkman label' not in row['notes']:   # #133 has none printed
        best = crops[seq].get('KA' if row['plate'] == 'LXXX' and row['col'] == '1' else 'HT')
        row['kirkman'] = ocr(best) if best is not None else ''
with open(DATA_DIR / 'census.csv', 'w', encoding='utf-8', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator='\n'); w.writeheader(); w.writerows(rows)

# contact sheets: each label from every source (HT | KA | IA) with its current value in census.csv
font = font('roman', 22)
(OUTPUT_DIR / 'labels').mkdir(parents=True, exist_ok=True)
for f in (OUTPUT_DIR / 'labels').glob('*.png'): f.unlink()
seqs = sorted(crops); per_row, n_rows, ch = 3, 14, 96
values = {int(r['seq']): r['kirkman'] for r in rows}
for k in range(0, len(seqs), per_row * n_rows):
    chunk = seqs[k:k + per_row * n_rows]
    sheet = Image.new('RGB', (per_row * 560, n_rows * (ch + 30)), 'white'); d = ImageDraw.Draw(sheet)
    for i, seq in enumerate(chunk):
        x, y = (i % per_row) * 560, (i // per_row) * (ch + 30)
        d.text((x + 6, y + 2), f'#{seq}   census: {values[seq] or "—"}', fill=(200, 0, 0), font=font)
        xx = x + 6
        for src in ('HT', 'KA', 'IA'):
            c = crops[seq].get(src)
            if c is None: xx += 170; continue
            im = Image.fromarray(c.clip(0, 255).astype('uint8'))
            sc = ch / im.height; im = im.resize((max(1, int(im.width * sc)), ch), Image.LANCZOS)
            im = im.crop((0, 0, min(im.width, 175), ch))
            sheet.paste(im.convert('RGB'), (xx, y + 28)); xx += 180
        d.rectangle([x, y, x + 559, y + ch + 29], outline=(190, 190, 190))
    sheet.save(OUTPUT_DIR / 'labels' / f'kirkman_{seqs.index(chunk[0]) // (per_row * n_rows) + 1:02d}.png')
print('kirkman column filled:', sum(1 for r in rows if r['kirkman']), '/', len(rows))
