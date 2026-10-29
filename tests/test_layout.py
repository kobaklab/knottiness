from tait import layout

def test_page_geometry():
    assert (layout.SHEET_W, layout.PAGE_H, layout.PAGE_W) == (594, 420, 297)
    assert abs(layout.PLATE_W - 268.5) < 0.02                       # the width of a plate
    assert abs((layout.PAGE_W - layout.PLATE_W) / 2 - 14.3) < 0.05  # side margins of a single-plate page
    # the content is centred: white above the header text and below the footer text are equal (16.6 mm)
    assert abs(layout.MARGIN_TOP + layout.CENTRING_SHIFT - layout.MARGIN_Y) < 1e-9
    assert abs(layout.MARGIN_BOTTOM - layout.CENTRING_SHIFT - layout.MARGIN_Y) < 1e-9
