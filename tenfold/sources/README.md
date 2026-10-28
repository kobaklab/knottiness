# sources/

Original scans and texts, as downloaded except for the two HathiTrust pages (see below). All are of works published in 1885 or 1898
(public domain); see each provider for their own usage terms for the digital copies.

## The plates (Trans. Roy. Soc. Edinburgh 32, 1885: Pl. LXXX, LXXXI)

Plate LXXX holds forms 1–182 of Tait's list, Plate LXXXI forms 183–364.

| File | Plate | Source | Notes |
|---|---|---|---|
| `pst_000067405572-seq_321.png` | LXXX | HathiTrust, Penn State copy, Google scan: <https://babel.hathitrust.org/cgi/pt?id=pst.000067405572> (page seq 321) · catalogue <https://catalog.hathitrust.org/Record/002727598> | Bitonal (recompressed, see below), 4712×6490 px, knots ~240×320 px. Left edge cropped (first column partly missing). Some thin lines broken into dots. **Primary source.** |
| `pst_000067405572-seq_323.png` | LXXXI | same, page seq 323 | Complete. 4760×6486 px. |
| `Tait__s_table_of_10_crossing_knots_-_1.png` | LXXX | Knot Atlas, uploaded 6 Sep 2005: <https://katlas.org/wiki/Special:ListFiles/Scott> | Bitonal, 2550×4200 px, knots ~115×150 px. Complete, including the first column. **Second source.** |
| `Tait__s_table_of_10_crossing_knots_-_2.png` | LXXXI | same | Complete. |
| `transactionsofro321887roy_orig_0695.jp2` | LXXX | Internet Archive (Natural History Museum, London copy): <https://archive.org/details/transactionsofro321887roy>, leaf 695 from the "single page original JP2" tar | Colour camera photo, 350 ppi, knots ~140×185 px, page rotated 90°. Sharpest greyscale source, but the first column is hidden in the binding gutter. **Third source.** |
| `transactionsofro321887roy_orig_0697.jp2` | LXXXI | same, leaf 697 | as above |
| `Fo8qyU7XEBsKqqe.jpeg` | LXXX + LXXXI | Found online (Twitter/X image; also circulated e.g. via <https://kottke.org/26/04/tenfold-knottiness>). Original source unknown. | Low-res (1200×798), tinted bitonal scan of the 1885 plates side by side. The image that started the project; reference only. |

### The HathiTrust pages are recompressed

The downloaded pages are 6 MB JPEGs of what is a black-and-white image (Google's bitonal processing;
99.9 % of the pixels are within 40 grey levels of 0 or 255). To keep the repository small they are
stored as lossless 1-bit PNGs (about 0.5 MB each), made by thresholding the JPEG at 128:

```python
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
g = Image.open('pst_000067405572-seq_321.jpg').convert('L')
g.point(lambda v: 255 if v >= 128 else 0).convert('1').save('pst_000067405572-seq_321.png', optimize=True)
```

Everything derived from these pages (`traced/*.json`, `traced/glyphs.json`) was produced from the PNGs.
Tracing the knots from the PNGs and from the original JPEGs gives identical results for all 364.

The SHA-256 of the
originals as downloaded, to check against a fresh download:

```
dcc6fb7a9b51dafc5fb8680f2530ac5f63457871247fa2ee637f4381b37fc4cb  pst_000067405572-seq_321.jpg
568434856eaec61b291c919202d2b329ea695a1a01b5e7d0b339dbbde7f89fc0  pst_000067405572-seq_323.jpg
```

## The text

| File | What | Source |
|---|---|---|
| `s0080456800025242.pdf` | P. G. Tait, *On Knots. Part III*, Trans. Roy. Soc. Edinburgh **32** (1885/86), pp. 493–506 — the original printing, text only (plates not included) | Cambridge Core, DOI [10.1017/S0080456800025242](https://doi.org/10.1017/S0080456800025242) |
| `s0080456800025230.pdf` | T. P. Kirkman, *The 364 Unifilar Knots of Ten Crossings, Enumerated and Described*, Trans. Roy. Soc. Edinburgh **32** (1885/86), pp. 483–491 — the lists (10A, 10B, …, 10Φ) whose entries are the top-right labels on the plates | Cambridge Core, DOI [10.1017/S0080456800025230](https://doi.org/10.1017/S0080456800025230) |
| `knotsiii.pdf` | The same paper as reprinted in Tait's *Scientific Papers*, vol. 1 (1898), pp. 335–347, with the plates renumbered VII–IX. **Not used**: the plates were re-transferred for the reprint and their headers and footers modified | A. Ranicki's knot theory history pages: <https://webhomes.maths.ed.ac.uk/~v1ranick/papers/knotsiii.pdf> (Internet Archive scan) |

Key pages of the 1885 text: p. 501 (§18, the letter → partition table), p. 503 (§21, the list of
all 364 forms, transcribed in `data/census_p503.txt`), pp. 505–506 (the correction merging the two
forms of type 109).
