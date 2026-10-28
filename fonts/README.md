# fonts/

Free fonts for the poster headers and footers (SIL Open Font License; the licences are in this directory).

| File | Font | Used for |
|---|---|---|
| `BarlowSemiCondensed-Medium.ttf` | Barlow Semi Condensed Medium, as downloaded | the spaced title capitals |
| `RobotoSerif-Latin[GRAD,opsz,wdth,wght].ttf` | Roboto Serif (variable), subset | side texts, credits, group headers of Plate XLIV |

The Roboto Serif file is the upstream variable font (https://github.com/googlefonts/RobotoSerif) reduced to the
characters the posters can use (Basic Latin, no-break space, middle dot, en and em dash, curly quotes), with
all four axes kept, which brings it from 3.9 MB to 0.4 MB. The Font Software has no Reserved Font Name. Made with

```bash
pyftsubset "RobotoSerif[GRAD,opsz,wdth,wght].ttf" \
  --unicodes="U+0020-007E,U+00A0,U+00B7,U+2013,U+2014,U+2018,U+2019,U+201C,U+201D" \
  --layout-features= --no-hinting --glyph-names --notdef-outline --drop-tables+=GPOS,GSUB,GDEF,gasp \
  --output-file="RobotoSerif-Latin[GRAD,opsz,wdth,wght].ttf"
```

The posters only read outlines and advance widths (`tait/poster.py`, `OutlineFont`), so the rebuilt posters are
identical to those made with the full font. A text with other characters needs a wider subset.
