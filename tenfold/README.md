# Tenfold Knottiness

A faithful vector reconstruction of the two plates **"Tenfold Knottiness"** (Plates LXXX and LXXXI)
from P. G. Tait, *On Knots. Part III*, Transactions of the Royal Society of Edinburgh **32** (1885).
The goal is a poster-quality SVG/PDF in which every knot closely follows Tait's original drawing,
but is rendered with proper over/under crossings, together with all of Tait's annotations.

## Background

In 1885 Tait, working from polyhedral data supplied by T. P. Kirkman, enumerated the alternating
knots with ten crossings: **123 types** (exactly the 123 alternating 10-crossing knots known today),
drawn in **364 forms** (different diagrams of the same knot). Each figure on the plates carries:

- **top left**: the type number (1–123) on the first form of each type, `-` on the others;
  vertical bars separate types;
- **top right**: the knot's designation in Kirkman's list (e.g. `B²⁸` = entry 28 of his list 10B).
  Kirkman sorts the knots into lists by their *flaps* (chains of two-sided regions, i.e. twists):
  10A has one single flap, 10C three, 10H one double and two single, …;
- **bottom**: two letters encoding the diagram's regions — each letter stands for a partition of 20,
  the corner counts of one class of meshes in the checkerboard colouring (table in §18 of the paper).
  A single barred letter (C̄) marks an amphicheiral form.

Tait drew the diagrams without over/under information: since all the knots are alternating, the
crossings are determined by the curve alone (up to mirror image). This project computes them.

## How it works

```
sources/ (scans)                 data/census_p503.txt (Tait's list, transcribed)
      │                                   │  scripts/build_census.py
      │                                   ▼
      │                          data/census.csv (364 forms: type, form, code, plate, …)
      ▼                                   │
segment plate into knots ────────────────┤  census numbers by reading order
      │                                   │
per knot, per source:                     │
  ink mask → skeleton → graph             │
  prune spurs, merge split junctions, bridge gaps,
  remove artefact loops (labels touching the knot, ink blots)
  → 4-valent graph with 10 crossings      │
  → pair strands at each crossing         │
  → validate ◄────────────────────────────┘  one strand · 10 crossings · region code
      │                                       · outer region in class of 2nd letter
      ▼
knots matched across sources by position on the page
first validating source (HathiTrust → Knot Atlas → Internet Archive)
      │  smoothing spline (C²-continuous, ~1–2 px from Tait's line)
      ▼
traced/<seq>.json  (curve, crossings, provenance)  ──►  render (style)  ──►  poster
```

Rendering (`tait/render.py`): each knot is drawn as one filled outline; at every crossing the
under-strand is cut where it passes through the over-strand's band (its width plus a margin of 1.1
stroke widths on each side), so gap edges are parallel to the over-strand at any crossing angle.
A cut never extends past the midpoint to the next crossing along the same strand, which keeps tight
loops intact even with heavy lines. The outline is written as cubic Bézier curves, fitted within
0.1 px of the exact shape. Default line width: 6.5 working px (`DEFAULT_STROKE` in `tait/render.py`; 2.1% of the median knot
height, close to Tait's lines).

Tracing and styling are independent: `traced/*.json` holds geometry only, so the drawing style
(line weight, colours) can change without re-tracing.

## Directory layout

This poster's directory in the [knottiness](../README.md) repository. Paths below are relative to
`tenfold/`; the Python package `tait/`, the shared scripts in `scripts/` and the fonts in `fonts/` are
at the repository root (`../tait/`, `../scripts/`, `../fonts/`).

```
sources/    original scans and PDFs, as downloaded except the two HathiTrust pages, stored as 1-bit PNGs
            (see sources/README.md for provenance)
data/       data transcribed by Claude from the 1885 sources: census_p503.txt, census.csv;
            glyphs.yaml: hand-made decisions for tracing the annotation glyphs, and hand edits of
            the finished outlines (`edit:` lists)
scripts/    the scripts specific to this poster
  build_census.py   census_p503.txt → census.csv, checked against Tait's totals
  build_poster.py   census + traced knots + output/knots/*.svg + traced/glyphs.json
                    -> output/tenfold_knottiness*.svg/.pdf/.png
                    (A2 landscape sheet, or --plates separate: one A3 portrait page per plate;
                    the layout is proportional, so other sizes are scaled prints)
  extract_kirkman.py  contact sheets of all Kirkman labels for checking census.csv by eye
  check_kirkman.py  check each Kirkman label's letter against the traced knot's flaps
  trace_glyphs.py   trace the 84 annotation glyphs -> traced/glyphs.json + review sheets
traced/     accepted traces, one JSON per form (candidates/ with every attempt is gitignored);
            glyphs.json: the annotation glyphs (edited ones keep their untouched trace under 'traced')
output/     generated
  knots/       one SVG per form in the current default style (committed)
  review/      one sheet per plate row: each knot's full cell (knot + labels) from every scan with
               its trace, and the accepted trace rendered with the annotations from census.csv
               (gitignored; regenerate with the scripts)
  labels/      every Kirkman label as cropped from each scan, next to its census value (gitignored)
  glyphs/      review sheets of the traced annotation glyphs, and glyph_sheet.svg/.png: the specimen
               of all glyphs between guide lines (gitignored)
  tenfold_knottiness.pdf                    the poster: both plates on one A2 sheet, paper tone
  tenfold_knottiness_page1/2.pdf            each plate on its own A3 page, paper tone
  tenfold_knottiness*.png, *_white.*, *.svg the same as PNG, on white, and as SVG (gitignored; rebuilt;
                                            only the three PDFs above are committed)
```

Shared, at the repository root:

```
tait/       Python package
  __init__.py  ROOT, FONTS_DIR, and Poster: the directories of one poster (TENFOLD, SEVEN_ORDERS)
  sources.py   source files per plate, ink detection, knot segmentation
  graph.py     skeleton → planar graph → strands, faces, checkerboard classes
  trace.py     one knot: clean-up, validation, smoothing spline
  codes.py     Tait's letter → partition tables (§18)
  diagram.py   faces and Kirkman's flap signature of a traced curve; Kirkman's list definitions
  glyphs.py    tracing Tait's hand-lettered annotation glyphs from the scans; hand edits of the
               traced outlines (edit_glyph, apply_edits)
  census.py    reading the census
  render.py    crossings, over/under alternation, SVG output
  review.py    review sheets
  layout.py    the page layout (A2 sheet, A3 pages, margins, text sizes), shared by the posters
  poster.py    typesetting (outline fonts, traced glyphs, labels), header and footer, glyph <defs>, SVG/PDF/PNG output
scripts/    shared by the posters: --poster tenfold (the default when run from inside tenfold/), or
            --plate LXXX / LXXXI
  trace_rows.py     trace rows of a plate from all sources, accept the first valid trace,
                    record row/col in census.csv, write SVGs and review sheets
  review_sheets.py  rebuild the review sheets from existing traces (e.g. after editing census.csv);
                    needs traced/candidates/ from a trace_rows.py run (gitignored)
  render_knots.py   re-render output/knots/*.svg from traced/*.json (after changing the rendering;
                    ~2 s per knot)
  edit_glyphs.py    re-apply the hand edits of data/glyphs.yaml to traced/glyphs.json (no re-tracing)
  plot_glyphs.py    specimen of all traced glyphs between guide lines -> output/glyphs/glyph_sheet.svg/.png
fonts/      the fonts of header and footer, with their licences (SIL Open Font License)
```

## Usage

`uv sync` once at the repository root (see the [repository README](../README.md)). The commands
below are run from inside `tenfold/`: uv finds the project from any subdirectory, and the scripts
locate their files themselves; the working directory only selects the default `--poster` of the
shared scripts in `../scripts/`.

The steps depend on each other in the order given: the glyph tracing reads the knot traces and the
census positions; the poster reads the glyphs and the rendered knots.

```bash
cd tenfold
# put the source files in sources/ (filenames as listed in sources/README.md)
uv run scripts/build_census.py
uv run ../scripts/trace_rows.py --plate LXXXI --rows all   # or 1, or 1-3; ~1.5 min per plate
uv run ../scripts/trace_rows.py --plate LXXX --rows all
# inspect output/review/<plate>_row<NN>.png and output/knots/<seq>.svg
uv run scripts/trace_glyphs.py                             # annotation glyphs -> traced/glyphs.json
                                                           #    (uses output/glyphs/collected.pkl if present, and says
                                                           #    if it is older than the traces;
                                                           #    --fresh: re-collect from the scans, ~3 min)
uv run ../scripts/render_knots.py                          # re-render the knots (line width 6.5, --stroke), ~12 min;
                                                           #    only after changing the rendering: trace_rows.py
                                                           #    already writes them in this style
uv run scripts/build_poster.py                             # the sheet, A2 -> output/tenfold_knottiness[_white]
                                                           #    (--white-gap 2.0: wider gaps in the _white files)
                                                           #    .svg/.pdf/.png
uv run scripts/build_poster.py --plates separate           # one page per plate, A3
                                                           #    -> output/tenfold_knottiness_page1/2[_white].*
```

Checks and maintenance:

```bash
uv run scripts/check_kirkman.py                            # each Kirkman letter against the traced knot's flaps
uv run scripts/extract_kirkman.py                          # contact sheets of the labels -> output/labels/
                                                           #    (needs traced/candidates/ from trace_rows.py)
uv run ../scripts/edit_glyphs.py                           # after changing only the edit: lists (no scans needed)
uv run ../scripts/plot_glyphs.py                           # -> output/glyphs/glyph_sheet.svg, .png
uv run ../scripts/review_sheets.py --plate LXXX            # after editing data/census.csv
                                                           #    (needs traced/candidates/ from trace_rows.py)
```

**Run this directory first when reproducing the repository from scratch.** The seven-orders poster
sets its labels in the glyphs traced here: `traced/glyphs.json` is read by
`../seven-orders/scripts/trace_glyphs.py` (to fit its additional letters to this set) and by
`../seven-orders/scripts/build_poster.py`. Everything up to `trace_glyphs.py` is needed for that
(the glyph tracing reads `traced/<seq>.json` and `data/census.csv`); `render_knots.py` and
`build_poster.py` are not. After re-tracing the glyphs (`--fresh`, or changed settings in
`data/glyphs.yaml`), re-run `../seven-orders/scripts/trace_glyphs.py` as well. See the
[repository README](../README.md#reproducibility).

What needs the scans: the knot traces and the glyph tracing read the files in `sources/`, which are
downloaded separately (see `sources/README.md`). Everything after that runs from committed files:
`traced/*.json` (knots), `traced/glyphs.json` (glyphs), `data/` (census, glyph decisions and edits).
So the glyph edits can be changed and re-applied (`edit_glyphs.py`) without the scans, while a fresh
`trace_glyphs.py` run re-traces from the scans and applies the same edits at the end. The edit
coordinates refer to the current traces: if the tracing settings of an edited glyph change, check
it on the glyph sheet and adjust the edits.

`cairosvg` (used for the review sheets and the PDF/PNG output) needs the system Cairo library:
usually present on Linux; on macOS `brew install cairo`. `scripts/extract_kirkman.py` calls
`tesseract` only to draft labels for empty `kirkman` cells (none: #133 has no printed label and is
skipped), so tesseract is optional.

## Status

**All 364 forms are traced and validated** (`traced/001.json` … `traced/364.json`). Every accepted
trace forms one closed strand with exactly 10 crossings, its region corner counts match Tait's
code for that form, and its outer region lies in the class of the code's second letter.

| Plate | accepted | from HathiTrust | from Knot Atlas | from Internet Archive |
|---|---|---|---|---|
| LXXX  | 182/182 | 162 | 19 | 1 |
| LXXXI | 182/182 | 179 |  3 | 0 |

HathiTrust alone succeeds less often on LXXX (cropped first column, thin lines broken into dots by
Google's bitonal processing); Knot Atlas covers almost all of those. Knot #133 (type 38, H̄) is the
only one that only the Internet Archive scan traces.

Per source, the knots that validate on their own: HathiTrust 162 + 179, Knot Atlas 179 + 178,
Internet Archive 168 + 168 (LXXX + LXXXI). The first column of the Internet Archive scan is hidden
in the binding gutter, so its 14 knots per plate cannot be reconstructed from it. Every knot validates in at least one source.

Smoothing: traces stay within Tait's printed stroke for ~96% of their length (mean ~1.2 px from the
line centre, stroke ~6.5 px at working scale); the curves are C²-continuous.

Annotations: all 363 Kirkman labels transcribed by Claude from the scans and checked against Kirkman's paper:
the letter fixed by each traced knot's flaps matches the label for all of them, after correcting the
misprinted #70 (see below).

Errors and inconsistencies found in the 1885 publications along the way are listed in the next
section.

## Errors and inconsistencies in the 1885 publications

Found while tracing and transcribing. Each was confirmed in all three scans of the plates (so it is in
the printing itself, not a scanning artefact). The poster shows the **corrected** version where there
is a correction; `data/census.csv` holds the corrected values and records what was printed in its
`notes` column. "Text" means Tait, *On Knots III* (`sources/s0080456800025242.pdf`); "Kirkman" means
Kirkman's list paper (`sources/s0080456800025230.pdf`).

| Form(s) | Printed | Problem | Evidence | Poster / census |
|---|---|---|---|---|
| #70 | Kirkman label **C⁵²** | The knot has four single flaps, which puts it in Kirkman's list 10D, not 10C. List 10D has 47 entries and D⁴⁷ appears nowhere else on the plates. | `scripts/check_kirkman.py`; with this correction every list has exactly as many knots on the plates as entries in Kirkman's paper. | **D⁴⁷** |
| #26, #32 | Kirkman label **C¹³** on both | C¹³ printed twice, C¹¹ never. | Both are C-list knots by their flaps; neither the flaps nor the 8-crossing bases tell which one is meant (the plates' C numbering does not follow Kirkman's published list, see next row). | #26 **C¹³**, #32 **C¹¹** (by convention: the second occurrence is renamed) |
| #352 (type 111) | Region code **lκ** (text p. 503 and plate) | Tait's convention (p. 502): the second letter is the class containing the outer region. The outer region has 6 corners, so it belongs to class l (κ = 33332222 has no region with more than 3). | The letters themselves match the traced knot; only their order is wrong. | **κl** (`CODE_CORRECTIONS` in `scripts/build_census.py`) |
| #307, #308 (type 79) | εc, βc (plate) | The text (p. 503) lists the two forms in the opposite order: βc, εc. | Both forms trace correctly with the plate's codes. | As on the plate (`PLATE_ORDER` in `scripts/build_census.py`) |
| list C | C¹ … C⁸⁰ | The plates' C numbers run to **C⁸⁰** (#65), without C¹¹ and C⁵², whereas Kirkman's printed list 10C has entries 1–79. Tait worked from an earlier version of Kirkman's list (Kirkman mentions bifilars Tait removed and four knots Tait added), which probably explains the different numbering. | The plates hold 79 C-list knots (by flaps), matching Kirkman's count. | As printed (C⁸⁰ kept): only the duplicate is resolved |

Related points that are *not* errors, but look like ones:

- **#133 (type 38, H̄) has no Kirkman label.** It is Kirkman's one *solid* knot (no flaps), which he
  describes separately rather than in his lists. This also explains why his lists add up to 363
  (119 subsolids + 244 unsolids) although his title says 364.
- **Type 109:** Tait's own late correction (Text, pp. 505–506): the two forms under No. 109 belong to
  one type, reducing his count to 123 types. The plates and the p. 503 list already reflect this.
- **Kirkman's paper** lists its own corrections to his earlier memoir (pp. 483–484); none of them
  affect the ten-crossing lists used here.

## Poster design

**Page.** The sheet is A2 landscape (594 × 420 mm) with both plates side by side
(`--plates together`, the default); `--plates separate` gives one A3 portrait page per plate (half the
sheet, with the complete footer: Tait's credit, the project address, the two credit lines). The
layout is proportional, so prints at other A sizes are scaled copies ("Fit to page": the pages on A4
are at the original's scale). Each plate is a 14 × 13 grid from `row`/`col` in `census.csv`, rows
justified, with a separator wherever the type changes between neighbours. Knots fill 72 % of the row
pitch; labels are 15 % of the knot height. Every output exists on the paper tone (`#f6f0dc`) and on
white, as SVG, PDF and PNG (the sheet 2500 px wide, the pages at the same density):
`output/tenfold_knottiness[_page1|_page2][_white]`.

**Drawing style.** Thin line with gaps (see "How it works"), line width 6.5 working px. The gap on each
side of an over-strand is 1.1 stroke widths; the `_white` files (made for home printing, where ink
bleeding closes narrow gaps) use 2.0 (`--white-gap`, `--gap` for the paper-tone files). Those knots are
rendered on first use (about 2 s per knot) and cached in `output/knots/gap2/` (gitignored). The plates
carry no over/under information, so the poster does not fix one mirror image for all knots:
the alternation of each knot starts at the first crossing passage of its stored curve.

**Header and footer.** As on the plates: "Trans. Roy. Soc. Edinʳ" (left), the title, and
"Vol. XXXII, Pl. LXXX." (right). Footer: "P. G. Tait del." (far left), the project's address,
`github.com/kobaklab/knottiness`, centred below the footer, half-way between the last credit line and the
page's edge, at 30 % opacity (`URL` in `build_poster.py`), and two
credit lines on the right: "F. Huth Lithʳ Edinʳ MDCCCLXXXV" over "D. Kobak Restʳ Ghent MMXXVI"
(`CREDIT`). The fonts are free ones close to the plates' lettering, compared on Plate LXXX's header:
the spaced title capitals in Barlow Semi Condensed Medium (spaced by their ink: 0.7 capital heights
between letters, 2.1 between words, as measured), the side texts and credits in Roboto Serif at
width 55, weight 250 (superscripts at weight 430, so they keep their weight when scaled down). Font
files and licences (SIL OFL) are in `../fonts/`; all text is drawn as outlines, so the SVG and PDF
need no installed fonts.

**Annotations.** Four per knot, at its corners: type number (first form of each type only; Tait's
`–` on the other forms is omitted), Kirkman label with superscript, and the two region letters
(italics as printed, a bar for amphicheirals). Labels stand on common baselines per row; each is
pushed out until it clears its knot, neighbouring labels are de-crowded, and a spacing check
reports any label or footer text closer than 0.35 font sizes to another label, to a knot other than
its own, to a separator or to the footer (a label keeps 0.30 from its own knot, and gives up some of that
where neighbours crowd; currently nothing is reported; `--check-only` runs just the check). All text is positioned from the glyphs' and the fonts' own metrics (renderer-independent).
Tait's long descenders (β γ ζ η f g p q) needed the label baselines 0.1 font sizes closer to their
knots (`--top-rise 0.05`, `--bottom-drop 0.85`). Weights (glyph outlines offset outward):
superscripts keep 0.85 of the full-size stroke width instead of the 0.62 that plain scaling would
give (`--sup-weight`); the type numbers are bold, 1.4 × the normal stroke (`--bold`; 1.0 = as on the
plates, which have no bold).

**Glyphs.** The annotations are set in glyphs traced from the plates (84: digits, capitals incl.
Δ Θ Ξ Σ Φ, italic and upright lowercase, Greek; `tait/glyphs.py`, `data/glyphs.yaml`,
`traced/glyphs.json`). The labels were hand-lettered on the stone (instances of one letter vary
4–8 % in height and visibly in shape), so a font cannot match them. Each glyph is combined from its
closely matching instances in the greyscale scan by super-resolution (instances enlarged 4×,
affine-aligned, averaged) and deconvolution, or taken from one chosen instance; traced as Bézier
outlines (type-like glyphs at 50 % ink with corner rebuilding), set to a common stroke width, with
measured baselines and descenders; Q's tail hangs below the baseline. The capital height is that of
the former placeholder font, so the layout keeps its proportions.

**Hand edits of the glyph outlines**, as `edit:` lists in `data/glyphs.yaml`, applied after tracing
(and by `../scripts/edit_glyphs.py` without re-tracing): change the height by stretching chosen
bands only; copy a part from another glyph (or the glyph itself, mirrored) into a region, morphed
into the old outline at the region's edge (signed-distance blending); thin, smooth, add or cut ink.
Edited: 5, A, M, N, W, Y, Ξ, Σ, Φ, italic u, upright e and r (e.g. W's serifs from X, Φ's foot from
T, u's tail from d, Σ's bottom bar = its top bar upside down).

## References

- P. G. Tait, *On Knots. Part III*, Trans. Roy. Soc. Edinburgh 32 (1885), 493–506, Plates LXXIX–LXXXI.
  [doi:10.1017/S0080456800025242](https://doi.org/10.1017/S0080456800025242)
- T. P. Kirkman, *The 364 unifilar knots of ten crossings, enumerated and described*,
  Trans. Roy. Soc. Edinburgh 32 (1885), 483–491.
  [doi:10.1017/S0080456800025230](https://doi.org/10.1017/S0080456800025230)
