# The first seven orders of knottiness

A faithful vector reconstruction of Plate XLIV, **"The First Seven Orders of Knottiness"**, from
P. G. Tait, *On Knots. Part II*, Transactions of the Royal Society of Edinburgh **32** (1884), the
companion of [Tenfold Knottiness](../tenfold/README.md) in the same volume. It reuses that project's
tracing, rendering, fonts and page design (see the [repository README](../README.md) for the layout).

## Background

The plate shows all alternating knots of 3 to 9 crossings (the seven "orders" of knottiness
3, 4, …, 9), without composites: 1, 1, 2, 3, 7, 18 and 41 knots, drawn in **144 forms** (73 types).
Tait based the 8- and 9-folds on Kirkman's enumeration and grouped Kirkman's diagrams into types
(§§1–5). Each figure carries its order (crossing number) and Kirkman's designation: `8 Bq` = order 8, figure
Bq among Kirkman's drawings of 8-crossing diagrams (his letters A, B, …, Z, Aa, Ab, …; the gaps are presumably
his composites and other excluded figures). The 6- and 7-folds also carry the designation of the same knot
in Tait's first paper (Trans. RSE 28, 1876–7), whose figures numbered all knots of an order, composites
included: Greek letters for the 6-folds (β γ δ; α missing, presumably the composite 6-fold not figured here, §4), Roman
numerals for the 7-folds (II–XI; I missing, presumably the composite 7-fold). Two forms of one knot can carry two numbers there (type I of the 7-folds: II, 7C and IV, 7D). The group headers give this
paper's numbering of the knots within each order (I, II, …), the number of forms drawn, and whether
the knot is amphicheiral. Each
group of forms of one knot has a header ("XII Four forms", "VII Un. Amph."), and double bars separate
the orders. The text (§6) gives each figure's pair of partitions of 2n: the corner counts of the
regions in the two classes of the checkerboard colouring, which every trace is checked against.

## Status

- **All 144 forms are traced and validated** (`traced/001.json` … `traced/144.json`): one closed
  strand, the figure's number of crossings, and exactly Tait's partition pair. Each validates in the
  Cambridge PDF, which supplies all traces (see `sources/README.md`).
- **Census** transcribed and checked (`data/`, see `data/README.md`). No errors found in the plate or
  the partition list.
- **Poster** (`scripts/build_poster.py` → `output/seven_orders_knottiness[_white]`): A3
  portrait, the same page, margins, header and footer as the tenfold poster's single-plate pages
  (side margins 14.3 mm, the plate's width 268.5 mm; header and footer text at identical positions).
  The title has the tenfold title's size; the long title fits (16 mm clear of the side texts) with the
  spacing measured on Plate XLIV itself, which sets it tighter than Plate LXXX (gaps between the
  letters 0.46 capital heights instead of 0.70, between the words 1.23 instead of 2.10).
  One scale for the whole plate: the knots keep their relative sizes. Every row but the last is
  justified (first and last knots at the margins, the gaps between the knots all widened by one factor
  per row, 1.03–1.17, so Tait's spacing of figures and groups keeps its rhythm; the double bars between
  the orders keep their places in their gaps); the shorter last row keeps the plate's spacing and is centred, with
  extra room only between 9 Ip and 9 Ir (1.4 label sizes), whose headers would nearly touch. The rows are spread over the page: the
  first row as far below the header band as on the tenfold poster (1.19 mm), the last as far above the
  footer band (0.03 mm), equally spaced in between (row pitch 30.0 mm). Group headers and figure labels
  on common lines per row; long headers are set narrower to fit (as on the plate). Spacing check: no
  text closer than 0.3 label sizes to another text, a bar or another figure (to its own figure: 0.15).

## Lettering and page details

The labels under the figures are set entirely in the tenfold poster's traced glyphs
(digits, capitals, also for the 7-folds' Roman numerals, upright lowercase, Greek β γ δ). What the
tenfold plates never print, upright i j m n v w x y z and the comma of the 7-fold labels ("II, 7C"),
is traced from this plate's own labels (`scripts/trace_glyphs.py` → `traced/glyphs.json`, decisions
in `data/glyphs.yaml`) with the tenfold method (instances from the Internet Archive photo,
super-resolved and averaged, corners rebuilt), and fitted to the tenfold set: the letters scaled to
its upright x-height (each letter's body, about its baseline: the plate's hand lettering varies by
letter) and offset to its stroke width; the comma at the common scale. Hand edit: i has j's dot (its
own was small and faint). Specimen: `output/glyphs/glyph_sheet.svg/.png` (the additions only, with the tenfold guide lines). The group headers stay in
Roboto Serif, at weight 400 (wdth 55), whose stroke matches the traced glyphs' (0.097 capital heights). The labels of a row share one baseline; the 6- and 7-fold labels span their figure as on
the plate (designation at its left, order and Kirkman's letter at its right; measured on the scan).

**Credit line.** The plate prints "P. G. Tait del." and "F. Huth, Lithʳ Edinʳ" without a year; the
poster's credit uses MDCCCLXXXIV, the year of the paper (Part II of vol. 32, read 2 June 1884).

**Header.** "Trans. Roy. Soc. Edinʳ" and "Vol. XXXII, Pl. XLIV.", set as on the tenfold poster; the plate
itself prints "Trans. Roy. Soc Edinʳ".

**Line weight.** 6.5 working px as on the tenfold poster (2.1 % of the knot height; the plate's lines
are about 1.7 %). The gaps are as on the tenfold poster: 1.1 stroke widths, 2.0 in the `_white` file.

**Chirality.** As on the tenfold poster: the plate carries no over/under information, and the poster
does not fix one mirror image for all knots (the alternation of each knot starts at the first crossing
passage of its stored curve).

## Usage

From inside `seven-orders/` (after `uv sync` at the repository root). This poster needs the tenfold
glyph set, `../tenfold/traced/glyphs.json` (committed): `scripts/trace_glyphs.py` fits its additional
letters to it and `scripts/build_poster.py` sets the labels in it. To reproduce everything from
scratch, run `tenfold/` first (through its `scripts/trace_glyphs.py`; see the
[repository README](../README.md#reproducibility)).

```bash
uv run scripts/build_census.py                               # data/*.txt -> data/census.csv, checked
uv run ../scripts/trace_rows.py --plate XLIV --rows all      # ~5 min; or 1-4, 5-8, 9-12
uv run ../scripts/render_knots.py                            # output/knots/*.svg, ~2 s per knot
uv run scripts/trace_glyphs.py                               # traced/glyphs.json: i j m n v w x y z , (needs the scans)
uv run scripts/build_poster.py                               # output/seven_orders_knottiness[_white].*
                                                             #    (--white-gap 2.0: wider gaps in the _white file)
uv run ../scripts/review_sheets.py --plate XLIV              # after editing data/census.csv
```

Review sheets (`output/review/XLIV_rowNN.png`, gitignored): each figure's cell from every scan with
its trace, and the accepted trace rendered with the census annotations and the partition pair.
`trace_rows.py` writes the knots in the poster's style (line width 6.5); `render_knots.py` is only needed after changing the rendering.

## References

- P. G. Tait, *On Knots. Part II*, Trans. Roy. Soc. Edinburgh 32 (1884), 327–342, Plate XLIV.
  [doi:10.1017/S0080456800026806](https://doi.org/10.1017/S0080456800026806)
- P. G. Tait, *On Knots*, Trans. Roy. Soc. Edinburgh 28 (1876–7) (the "former paper").
