# sources/

The paper and its plate were published in 1884 (public domain); see each provider for their own usage
terms for the digital copies.

## Used

| File | Source | Used for |
|---|---|---|
| `s0080456800026806.pdf` | Cambridge Core, P. G. Tait, *On Knots. Part II*, Trans. Roy. Soc. Edinburgh 32 (1884), 327–342, DOI [10.1017/S0080456800026806](https://doi.org/10.1017/S0080456800026806) | **Everything except the added glyphs.** The paper with the plate as its last page (p. 17): one embedded bitonal image, 2584×3534 px at 300 ppi, knots ~170 px tall, clean continuous lines, read directly from the PDF (`tait/sources.py`, `pdf_page`). All 144 knots are traced from it, and it is the reference for the layout (positions, double bars, the 6- and 7-fold labels). The text supplies the partitions of §6 (`../data/partitions_p332.txt`). |
| `transactionsofro321887roy_orig_0449.jp2` | Internet Archive (Natural History Museum, London copy): <https://archive.org/details/transactionsofro321887roy>, leaf 449 of the "single page original JP2" tar | **Only the glyphs the tenfold set lacks** (upright i j m n v w x y z and the comma, `../scripts/trace_glyphs.py`): a colour camera photo, the only greyscale scan, which the super-resolution of the glyph tracing needs (as for the tenfold glyphs). Page rotated 90°; the plate's first column is hidden in the binding gutter. |

The PDF alone is sufficient for the knots: its trace validated for every figure.

## Not used

Other scans of the plate, not used for any result. They are kept so that the folder is complete.

| File | Source | Notes |
|---|---|---|
| `pst_000067405565-seq_443.png` | HathiTrust, Penn State copy, Google scan: <https://babel.hathitrust.org/cgi/pt?id=pst.000067405565> (page seq 443) | Bitonal, 4992×6502 px, heavy lines. Recompressed, see below. |
| `Tait__s_table_of_knots_to_7_crossings.png` | Knot Atlas (uploaded by Scott, as the tenfold plates): <https://katlas.org/wiki/Special:ListFiles/Scott> | Bitonal, thin and partly broken lines. |

The HathiTrust page is stored as a lossless 1-bit PNG, made from the downloaded JPEG (6.3 MB) by
thresholding at 128, as for the tenfold pages (see `../../tenfold/sources/README.md`). SHA-256 of the
original download:

```
b0226592842f16c237de26f4ad6972403678ee7a1947f7c3593948bf7d4a24e1  pst_000067405565-seq_443.jpg
```
