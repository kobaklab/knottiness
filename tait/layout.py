"""Page layout shared by the posters, in mm, and the sizes of header and footer text.

The layout is made for the Tenfold sheet, A2 landscape (594 x 420 mm) with a plate on each half; a plate's own
page is half of it, A3 portrait (297 x 420), and Plate XLIV's page (seven-orders) is the same page. Everything
is proportional to the sheet, so prints at other A sizes are scaled copies. Used by both build_poster.py scripts
and by the scripts that make the README images from the finished posters."""
SHEET_W, PAGE_H = 594, 420                # the Tenfold sheet, A2 landscape (mm)
PAGE_W = SHEET_W / 2                     # a plate's own page, A3 portrait (297 mm)

MARGIN_X, MARGIN_Y = 0.028 * SHEET_W, 0.040 * PAGE_H      # outer margins of the sheet
# The footer's text hangs down from the top of its band while the header is centred in its band, which left
# 20.9 mm of white above the title and 12.35 mm below the footer (the address aside). The content is moved
# up by half the difference, so that both are 16.6 mm.
CENTRING_SHIFT = 4.28
MARGIN_TOP, MARGIN_BOTTOM = MARGIN_Y - CENTRING_SHIFT, MARGIN_Y + CENTRING_SHIFT
GUTTER = 0.040 * SHEET_W                                  # between the two plates of the sheet
HEADER, FOOTER = 0.040 * PAGE_H, 0.024 * PAGE_H           # bands for the plate headers / footers
PLATE_W = (SHEET_W - 2 * MARGIN_X - GUTTER) / 2           # 268.5 mm: the width of a plate
Y_GRID = MARGIN_TOP + HEADER                              # where the knots start

ROWS = 14                                                 # rows of a tenfold plate (13 knots each)
ROW_H = (PAGE_H - 2 * MARGIN_Y - HEADER - FOOTER) / ROWS  # row pitch of the tenfold plates
KNOT_FILL = 0.72                                          # median knot height as a fraction of the row pitch
LABEL_SIZE = 0.150                                        # label font size as a fraction of the median knot height
FS_TENFOLD = LABEL_SIZE * KNOT_FILL * ROW_H               # the tenfold label font size (mm)

# header and footer text, relative to the tenfold label size (the seven-orders page uses the same sizes)
HEADER_SIZE = 1.45                                        # header text
TITLE_SCALE = 1.45                                        # title, relative to the header text
FOOTER_SCALE = 0.95                                       # footer text, relative to the header text
URL, URL_SCALE, URL_OPACITY = 'github.com/kobaklab/knottiness', 1.0, 0.3   # the project's address, faint
CREDIT_LEADING = 2.1                                      # baseline-to-baseline distance of the credit lines, in capital heights
