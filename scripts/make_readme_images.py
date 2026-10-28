"""Images of the repository README, made from the finished posters (run both build_poster.py scripts first;
they read the paper-tone SVGs in <poster>/output/):

  uv run scripts/make_readme_images.py

Writes docs/cover.png: the header and the first two rows of knots of Tenfold Knottiness (page 1), 1500 px wide;
and docs/posters.png: The First Seven Orders of Knottiness and the Tenfold sheet side by side, at the same height."""
import io
import numpy as np
import cairosvg
from PIL import Image, ImageDraw
from tait import ROOT, TENFOLD, SEVEN_ORDERS

DOCS = ROOT / 'docs'; DOCS.mkdir(exist_ok=True)
WIDTH = 1500

def render(svg, **size):
    return Image.open(io.BytesIO(cairosvg.svg2png(url=str(svg), **size))).convert('RGB')

def save(im, name):
    im.quantize(colors=48, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(DOCS / name, optimize=True)
    print('wrote', (DOCS / name).relative_to(ROOT), im.size)

# ---- cover: page 1 of the tenfold poster, from just above the header to the end of the second row of knots
PAGE_H_MM, PAGE_W_MM = 420.0, 297.0
page = render(TENFOLD.output / 'tenfold_knottiness_page1.svg', output_width=WIDTH)
mm = page.width / PAGE_W_MM                                     # pixels per mm
# the grid starts below the header band; its rows are (page - margins - header - footer) / 14 high (build_poster.py)
y_grid = 16.8 - 4.28 + 16.8; row_h = (PAGE_H_MM - 2 * 16.8 - 16.8 - 10.08) / 14
guess = (y_grid + 2 * row_h) * mm
ink = (np.array(page.convert('L')) < 128).sum(1)              # dark pixels per row of the image
lo, hi = int(guess - 3 * mm), int(guess + 3 * mm)
blank = np.flatnonzero(ink[lo:hi] == 0) + lo                    # empty lines between the labels of row 2 and row 3
end = int(blank[0]) if len(blank) else lo + int(np.argmin(ink[lo:hi]))          # the last line of ink of row 2's labels
top = int(10.5 * mm)
margin = int(np.flatnonzero(ink[top:] > 0)[0])                   # the white space above the header's ink
paper = page.getpixel((0, 0))
cover = Image.new('RGB', (page.width, (end - top) + margin), paper)             # the same white space below the labels
cover.paste(page.crop((0, top, page.width, end)), (0, 0))
save(cover, 'cover.png')

# ---- both posters side by side: same height, a small gap, each on its paper with a thin edge
GAP = 30
seven_w, ten_w = 297.0, 594.0                                    # mm, both 420 mm high
h = round((WIDTH - GAP) / (seven_w + ten_w) * 420)
seven = render(SEVEN_ORDERS.output / 'seven_orders_knottiness.svg', output_height=h)
ten = render(TENFOLD.output / 'tenfold_knottiness.svg', output_height=h)
canvas = Image.new('RGB', (seven.width + GAP + ten.width, h), 'white')
canvas.paste(seven, (0, 0)); canvas.paste(ten, (seven.width + GAP, 0))
d = ImageDraw.Draw(canvas)
for x0, im in ((0, seven), (seven.width + GAP, ten)):
    d.rectangle([x0, 0, x0 + im.width - 1, h - 1], outline=(200, 192, 168))
save(canvas, 'posters.png')
