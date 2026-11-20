#!/usr/bin/env python3
"""news-image-20261120: 'The World in One Day' - Friday 20 November 2026.

A one-page newspaper front sheet summing up one day of world news.
Everything is drawn as flat vector geometry in code: filled polygons,
circles and thick strokes for the illustrations, and a Hershey-style
stroke typeface (coordinate polylines + explicit advance widths, one
uniform design grid) for every letter. A heavier serif display cut of
the same grid carries the masthead. The scene is rendered on a
4096x4096 canvas and box-downscaled to 1024x1024 so edges are smooth.
Python standard library only. Fully deterministic.
"""

import math
import os
import struct
import zlib

# ------------------------------------------------------------------ canvas
SS = 4                      # supersampling factor
W = 1024                    # final width / height
W4 = W * SS                 # render width / height

PAPER = (246, 240, 226)     # warm cream paper
PANEL = (253, 250, 242)     # panel card
TINT = (241, 234, 217)      # pale art tint
INK = (26, 24, 20)          # near-black ink
GREY = (105, 98, 88)        # secondary ink
RULE = (199, 189, 167)      # hairlines
RED = (178, 32, 26)         # the one accent
BLUE = (46, 78, 120)
TEAL = (38, 102, 96)
GREEN = (66, 110, 60)
GOLD = (176, 128, 32)
BROWN = (128, 88, 54)
NAVY = (22, 30, 54)
SKY = (198, 218, 232)
SEA = (92, 138, 170)
SAND = (219, 196, 150)
WHITE = (255, 255, 255)

FB = bytearray(bytes(PAPER) * (W4 * W4))


def _span(y, x0, x1, c):
    if y < 0 or y >= W4:
        return
    if x0 < 0:
        x0 = 0
    if x1 > W4 - 1:
        x1 = W4 - 1
    if x1 < x0:
        return
    off = y * W4 * 3 + x0 * 3
    FB[off:off + (x1 - x0 + 1) * 3] = bytes(c) * (x1 - x0 + 1)


def fill_rect(x, y, w, h, c):
    x0 = int(round(x * SS))
    y0 = int(round(y * SS))
    x1 = int(round((x + w) * SS)) - 1
    y1 = int(round((y + h) * SS)) - 1
    if x1 < x0 or y1 < y0:
        return
    row = bytes(c) * (x1 - x0 + 1)
    n = len(row)
    for yy in range(y0, y1 + 1):
        off = yy * W4 * 3 + x0 * 3
        FB[off:off + n] = row


def fill_circle(cx, cy, r, c):
    cx *= SS
    cy *= SS
    r *= SS
    y0 = int(cy - r)
    y1 = int(cy + r)
    r2 = r * r
    for yy in range(y0, y1 + 1):
        dy = yy - cy
        d2 = r2 - dy * dy
        if d2 < 0:
            continue
        dx = int(math.sqrt(d2))
        _span(yy, int(cx - dx), int(cx + dx), c)


def fill_ellipse(cx, cy, rx, ry, c):
    cx *= SS
    cy *= SS
    rx *= SS
    ry *= SS
    y0 = int(cy - ry)
    y1 = int(cy + ry)
    for yy in range(y0, y1 + 1):
        dy = (yy - cy) / ry
        d2 = 1.0 - dy * dy
        if d2 < 0:
            continue
        dx = int(rx * math.sqrt(d2))
        _span(yy, int(cx - dx), int(cx + dx), c)


def fill_poly(pts, c):
    """Scanline fill of a polygon given in final-image coordinates."""
    p = [(x * SS, y * SS) for (x, y) in pts]
    ys = [q[1] for q in p]
    y0 = max(0, int(min(ys)))
    y1 = min(W4 - 1, int(max(ys)))
    n = len(p)
    for yy in range(y0, y1 + 1):
        yc = yy + 0.5
        xs = []
        for i in range(n):
            xa, ya = p[i]
            xb, yb = p[(i + 1) % n]
            if (ya <= yc < yb) or (yb <= yc < ya):
                xs.append(xa + (yc - ya) * (xb - xa) / (yb - ya))
        if len(xs) < 2:
            continue
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            _span(yy, int(xs[i]), int(xs[i + 1]), c)


def thick_line(x0, y0, x1, y1, w, c):
    """A line drawn as stamped discs: round caps, even weight."""
    r = w * SS / 2.0
    dx = (x1 - x0) * SS
    dy = (y1 - y0) * SS
    dist = math.hypot(dx, dy)
    steps = max(1, int(dist / max(1.0, r * 0.55)))
    r2 = r * r
    ri = int(r)
    for i in range(steps + 1):
        t = i / steps
        cx = (x0 * SS) + dx * t
        cy = (y0 * SS) + dy * t
        for yy in range(int(cy) - ri, int(cy) + ri + 1):
            ddy = yy - cy
            d2 = r2 - ddy * ddy
            if d2 < 0:
                continue
            ddx = int(math.sqrt(d2))
            _span(yy, int(cx - ddx), int(cx + ddx), c)


def polyline(pts, w, c, close=False):
    pp = list(pts)
    if close and pp:
        pp.append(pp[0])
    for i in range(len(pp) - 1):
        thick_line(pp[i][0], pp[i][1], pp[i + 1][0], pp[i + 1][1], w, c)


def outline_rect(x, y, w, h, lw, c):
    fill_rect(x, y, w, lw, c)
    fill_rect(x, y + h - lw, w, lw, c)
    fill_rect(x, y, lw, h, c)
    fill_rect(x + w - lw, y, lw, h, c)


def arc_pts(cx, cy, rx, ry, a0, a1, n=14):
    """Points along an ellipse arc; angles in degrees, 0 = east,
    positive angles go DOWN the page (screen coordinates)."""
    out = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        out.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return out

# ------------------------------------------------------------------- font
# Hershey-style stroke font on ONE design grid: baseline y=0, cap height
# 12, x-height 8, descender -3 (font units, y up). Every glyph carries an
# explicit advance width plus its strokes. A stroke is either a polyline
# (list of (x, y) points) or an arc tuple ('A', cx, cy, rx, ry, a0, a1)
# with angles in degrees, counter-clockwise in font space. All letterforms
# are built from the same stems, bowls and arcs, so spacing and weight are
# even across the whole alphabet - no hand-wobble, no hairline stems.

def _arc(cx, cy, rx, ry, a0, a1):
    return ('A', cx, cy, rx, ry, a0, a1)


GLYPHS = {
    ' ': (4.0, []),
    'A': (8.6, [[(0, 0), (4.3, 12), (8.6, 0)], [(2.0, 4.6), (6.6, 4.6)]]),
    'B': (8.2, [[(1, 0), (1, 12)],
                [(1, 12), (4.4, 12), (6.6, 10.6), (6.6, 8.0), (4.4, 6.6), (1, 6.6)],
                [(1, 6.6), (4.8, 6.6), (7.0, 5.0), (7.0, 1.6), (4.8, 0), (1, 0)]]),
    'C': (8.4, [_arc(4.6, 6, 3.9, 6, 55, 305)]),
    'D': (8.8, [[(1, 0), (1, 12)], [(1, 12), (4.2, 12)],
                _arc(4.2, 6, 3.6, 6, 90, -90), [(7.8, 0), (1, 0)]]),
    'E': (7.6, [[(7, 12), (1, 12), (1, 0), (7.2, 0)], [(1, 6.4), (5.8, 6.4)]]),
    'F': (7.2, [[(1, 0), (1, 12), (7, 12)], [(1, 6.4), (5.4, 6.4)]]),
    'G': (9.0, [_arc(4.7, 6, 4.0, 6, 55, 305)],
          ),
    'H': (9.0, [[(1, 0), (1, 12)], [(8, 0), (8, 12)], [(1, 6.2), (8, 6.2)]]),
    'I': (3.4, [[(1.7, 0), (1.7, 12)]]),
    'J': (6.4, [[(5.6, 12), (5.6, 2.2)], _arc(3.4, 2.2, 2.2, 2.2, 0, 225)]),
    'K': (8.6, [[(1, 0), (1, 12)], [(7.8, 12), (1.2, 5.6)], [(2.6, 7.2), (8.2, 0)]]),
    'L': (7.4, [[(1, 12), (1, 0), (7.2, 0)]]),
    'M': (10.6, [[(1, 0), (1, 12), (5.3, 5.6), (9.6, 12), (9.6, 0)]]),
    'N': (9.2, [[(1, 0), (1, 12), (8.2, 0), (8.2, 12)]]),
    'O': (9.2, [_arc(4.6, 6, 4.1, 6, 0, 360)]),
    'P': (8.0, [[(1, 0), (1, 12)], [(1, 12), (4.6, 12)],
                _arc(4.6, 9, 2.9, 3, 90, -90), [(7.5, 6), (1, 6)]]),
    'Q': (9.2, [_arc(4.6, 6, 4.1, 6, 0, 360)], ),
    'R': (8.4, [[(1, 0), (1, 12)], [(1, 12), (4.6, 12)],
                _arc(4.6, 9, 2.9, 3, 90, -90), [(7.5, 6), (1, 6)],
                [(4.6, 6.2), (8.2, 0)]]),
    'S': (8.0, [[(7.2, 10.6), (5.6, 11.9), (2.8, 11.9), (1.2, 10.2), (1.4, 8.2),
                 (3.0, 6.9), (5.6, 5.6), (6.9, 4.2), (6.7, 1.9), (5.2, 0.3),
                 (2.6, 0.1), (1.0, 1.2)]]),
    'T': (8.2, [[(0.6, 12), (7.6, 12)], [(4.1, 12), (4.1, 0)]]),
    'U': (9.0, [[(1, 12), (1, 3.4)], _arc(4.5, 3.4, 3.5, 3.4, 180, 360),
                [(8, 3.4), (8, 12)]]),
    'V': (8.6, [[(0.4, 12), (4.3, 0), (8.2, 12)]]),
    'W': (11.2, [[(0.4, 12), (2.6, 0), (5.3, 8.6), (8.0, 0), (10.8, 12)]]),
    'X': (8.4, [[(0.8, 12), (7.6, 0)], [(0.8, 0), (7.6, 12)]]),
    'Y': (8.6, [[(0.4, 12), (4.3, 5.8), (8.2, 12)], [(4.3, 5.8), (4.3, 0)]]),
    'Z': (8.2, [[(0.8, 12), (7.4, 12), (0.8, 0), (7.6, 0)]]),
    'a': (7.2, [_arc(3.3, 4, 3.0, 4, 0, 360), [(6.3, 8), (6.3, 0)]]),
    'b': (7.6, [[(1.2, 0), (1.2, 12)], _arc(4.4, 4, 3.0, 4, 0, 360)]),
    'c': (6.8, [_arc(3.6, 4, 3.1, 4, 50, 310)]),
    'd': (7.6, [_arc(3.3, 4, 3.0, 4, 0, 360), [(6.3, 0), (6.3, 12)]]),
    'e': (7.0, [[(0.6, 4.6), (6.6, 4.6)], _arc(3.5, 4, 3.1, 4, 15, 330)]),
    'f': (4.6, [[(4.4, 11.4), (3.0, 12), (1.9, 10.6), (1.9, 0)],
                [(0.6, 8), (3.6, 8)]]),
    'g': (7.4, [_arc(3.3, 4.4, 3.0, 3.9, 0, 360), [(6.3, 8.3), (6.3, -0.6)],
                _arc(3.9, -0.6, 2.4, 2.4, 0, 200)]),
    'h': (7.6, [[(1.2, 0), (1.2, 12)],
                [(1.2, 4.8), (2.4, 7.4), (4.4, 8.0), (6.2, 6.6), (6.2, 0)]]),
    'i': (3.2, [[(1.6, 0), (1.6, 8)], [(1.6, 10.4), (1.6, 11.3)]]),
    'j': (3.6, [[(2.6, 8), (2.6, 0.2), (1.8, -1.6), (0.4, -2.2)],
                [(2.6, 10.4), (2.6, 11.3)]]),
    'k': (7.0, [[(1.2, 0), (1.2, 12)], [(6.2, 8), (1.4, 3.4)],
                [(3.0, 5.0), (6.6, 0)]]),
    'l': (3.2, [[(1.6, 0), (1.6, 12)]]),
    'm': (11.4, [[(1.2, 0), (1.2, 8)],
                 [(1.2, 5.0), (2.2, 7.6), (4.2, 8.0), (5.6, 6.4), (5.6, 0)],
                 [(5.6, 5.0), (6.6, 7.6), (8.6, 8.0), (10.0, 6.4), (10.0, 0)]]),
    'n': (7.6, [[(1.2, 0), (1.2, 8)],
                [(1.2, 5.0), (2.4, 7.6), (4.4, 8.0), (6.2, 6.6), (6.2, 0)]]),
    'o': (7.4, [_arc(3.7, 4, 3.3, 4, 0, 360)]),
    'p': (7.6, [[(1.2, -3), (1.2, 8)], _arc(4.4, 4, 3.0, 4, 0, 360)]),
    'q': (7.6, [_arc(3.3, 4, 3.0, 4, 0, 360), [(6.3, -3), (6.3, 8)]]),
    'r': (5.2, [[(1.2, 0), (1.2, 8)],
                [(1.2, 5.4), (2.4, 7.8), (4.4, 8.0), (5.0, 6.8)]]),
    's': (6.6, [[(5.8, 6.9), (4.6, 8.1), (2.4, 8.1), (1.2, 6.9), (1.4, 5.4),
                 (2.6, 4.5), (4.8, 3.4), (5.6, 2.2), (5.2, 0.7), (3.8, 0.0),
                 (1.8, 0.1), (0.8, 0.9)]]),
    't': (5.0, [[(2.4, 11), (2.4, 1.6), (3.2, 0.2), (4.6, 0.2)],
                [(0.8, 8), (4.4, 8)]]),
    'u': (7.6, [[(1.2, 8), (1.2, 2.8)], _arc(3.9, 2.6, 2.7, 2.6, 180, 360),
                [(6.6, 2.8), (6.6, 0)]]),
    'v': (7.0, [[(0.4, 8), (3.5, 0), (6.6, 8)]]),
    'w': (9.6, [[(0.4, 8), (2.2, 0), (4.4, 6.0), (6.6, 0), (8.8, 8)]]),
    'x': (6.8, [[(0.6, 8), (6.2, 0)], [(0.6, 0), (6.2, 8)]]),
    'y': (7.0, [[(0.4, 8), (3.5, 2.6), (6.6, 8)],
                [(3.5, 2.6), (2.6, -1.2), (1.2, -2.8)]]),
    'z': (6.8, [[(0.8, 8), (6.0, 8), (0.8, 0), (6.2, 0)]]),
    '0': (8.0, [_arc(4, 6, 3.4, 6, 0, 360)]),
    '1': (5.6, [[(2.2, 9.6), (4.0, 12), (4.0, 0)], [(2.2, 0), (5.6, 0)]]),
    '2': (7.6, [[(0.9, 10.2), (2.2, 11.8), (4.8, 11.9), (6.6, 10.4),
                 (6.4, 8.2), (0.9, 0), (7.0, 0)]]),
    '3': (7.6, [[(1.2, 10.6), (3.0, 12), (5.4, 11.4), (6.2, 9.6), (5.2, 7.6),
                 (3.4, 6.6), (5.4, 5.6), (6.4, 3.4), (5.6, 1.2), (3.2, 0.1),
                 (1.0, 0.8)]]),
    '4': (8.2, [[(5.6, 0), (5.6, 12), (1.0, 4.2), (7.8, 4.2)]]),
    '5': (7.4, [[(6.6, 12), (1.6, 12), (1.4, 7.2), (4.0, 7.8), (6.2, 6.2),
                 (6.4, 2.6), (4.8, 0.4), (2.2, 0.1), (0.9, 1.0)]]),
    '6': (7.8, [[(6.4, 10.8), (4.2, 11.9), (2.0, 9.8), (1.0, 6.4), (1.2, 3.0),
                 (2.8, 0.6), (5.0, 0.2), (6.6, 1.6), (6.6, 4.2), (5.2, 6.0),
                 (3.0, 6.2), (1.4, 5.0)]]),
    '7': (7.4, [[(0.8, 12), (6.8, 12), (3.6, 0)]]),
    '8': (7.8, [_arc(3.9, 9.2, 2.6, 2.8, 0, 360),
                _arc(3.9, 3.2, 3.2, 3.2, 0, 360)]),
    '9': (7.8, [[(1.0, 1.4), (3.2, 0.2), (5.4, 2.2), (6.4, 5.6), (6.2, 9.0),
                 (4.8, 11.4), (2.6, 11.9), (1.0, 10.4), (1.0, 7.8), (2.4, 6.0),
                 (4.6, 5.8), (6.2, 7.2)]]),
    '.': (3.4, [[(1.7, 0.1), (1.7, 0.9)]]),
    ',': (3.4, [[(1.9, 0.9), (1.5, -1.4)]]),
    ';': (3.4, [[(1.7, 5.2), (1.7, 6.0)], [(1.9, 0.9), (1.5, -1.4)]]),
    ':': (3.4, [[(1.7, 0.2), (1.7, 1.0)], [(1.7, 5.2), (1.7, 6.0)]]),
    "'": (2.8, [[(1.4, 12), (1.4, 9.8)]]),
    '-': (5.0, [[(0.8, 4.4), (4.2, 4.4)]]),
    '–': (5.0, [[(0.8, 4.4), (4.2, 4.4)]]),
    '—': (8.0, [[(0.6, 4.4), (7.4, 4.4)]]),
    '·': (3.0, [[(1.5, 4.2), (1.5, 5.0)]]),
    '•': (4.0, [[(2.0, 4.0), (2.0, 5.0)]]),
    '$': (7.6, [[(6.0, 10.4), (4.4, 11.8), (2.2, 11.6), (1.2, 10.0), (2.0, 8.0),
                 (5.2, 6.4), (6.2, 4.6), (5.4, 1.8), (3.4, 0.4), (1.4, 1.2)],
                [(3.8, -1), (3.8, 13)]]),
    '%': (11.0, [_arc(2.6, 9.4, 1.9, 1.9, 0, 360), [(9.6, 12), (1.4, 0)],
                 _arc(8.4, 2.6, 1.9, 1.9, 0, 360)]),
    '+': (7.6, [[(3.8, 1.6), (3.8, 9.6)], [(0.8, 5.6), (6.8, 5.6)]]),
    '/': (5.4, [[(4.8, 12.4), (0.6, -0.4)]]),
    '(': (4.6, [_arc(4.4, 6, 3.4, 6.4, 110, 250)]),
    ')': (4.6, [_arc(0.2, 6, 3.4, 6.4, 70, -70)]),
    '!': (3.4, [[(1.7, 12), (1.7, 4.6)], [(1.7, 0.1), (1.7, 0.9)]]),
    '?': (7.2, [[(1.0, 10.4), (2.4, 11.9), (5.0, 11.7), (6.2, 10.0),
                 (5.6, 7.8), (3.8, 6.2), (3.8, 4.4)],
                [(3.8, 0.1), (3.8, 0.9)]]),
    '&': (9.0, [[(8.2, 0.4), (5.0, 4.6), (3.0, 6.8), (1.6, 9.0), (2.2, 11.2),
                 (4.2, 11.6), (5.4, 10.2), (4.6, 8.0), (2.6, 5.6), (1.2, 3.0),
                 (2.0, 0.6), (4.4, 0.2), (6.8, 2.0), (8.4, 4.4)]]),
    '*': (6.0, [[(3, 11.2), (3, 5.6)], [(0.6, 9.8), (5.4, 7.0)],
                [(5.4, 9.8), (0.6, 7.0)]]),
    '=': (7.6, [[(0.8, 7.6), (6.8, 7.6)], [(0.8, 3.8), (6.8, 3.8)]]),
    '>': (7.6, [[(1.2, 9.8), (6.2, 6.0), (1.2, 2.2)]]),
    '<': (7.6, [[(6.4, 9.8), (1.4, 6.0), (6.4, 2.2)]]),
    '°': (4.6, [_arc(2.3, 9.6, 1.7, 1.7, 0, 360)]),
    '"': (5.4, [[(1.6, 12), (1.6, 9.8)], [(4.0, 12), (4.0, 9.8)]]),
    '#': (8.6, [[(3.0, -0.4), (3.8, 12.4)], [(6.0, -0.4), (6.8, 12.4)],
                [(0.8, 4.2), (8.2, 4.2)], [(0.8, 7.8), (8.2, 7.8)]]),
}

# Fix-ups: G spur and Q tail need a second stroke list entry each.
GLYPHS['G'] = (9.0, [_arc(4.7, 6, 4.0, 6, 55, 305),
                     [(8.6, 4.2), (5.2, 4.2)], [(8.6, 4.2), (8.6, 1.0)]])
GLYPHS['Q'] = (9.2, [_arc(4.6, 6, 4.1, 6, 0, 360),
                     [(5.8, 2.2), (9.0, -0.6)]])

# Typographic aliases fold onto the base glyphs.
_ALIASES = {'’': "'", '‘': "'", '“': '"', '”': '"', '−': '-'}
for _a, _b in _ALIASES.items():
    GLYPHS[_a] = GLYPHS[_b]

# Serif display cut of the same grid, used only for the masthead line.
# Same advances family and stroke logic, but stems carry small horizontal
# feet at the baseline and at cap / x-height, and arms carry end ticks,
# so the line reads as a clean serif display face.
SERIF = {
    ' ': (4.2, []),
    'F': (8.0, [[(1.2, 0), (1.2, 12)], [(0.2, 0), (2.4, 0)],
                [(1.2, 12), (7.2, 12)], [(7.2, 12), (7.2, 11.0)],
                [(1.2, 6.6), (5.6, 6.6)], [(5.6, 6.6), (5.6, 5.7)]]),
    'r': (5.4, [[(1.2, 0), (1.2, 8)], [(0.3, 0), (2.3, 0)],
                [(1.2, 5.2), (2.4, 7.6), (4.2, 8.1), (5.2, 7.0)]]),
    'i': (3.4, [[(1.7, 0), (1.7, 8)], [(0.6, 0), (2.8, 0)],
                [(0.6, 8), (2.8, 8)], [(1.7, 10.5), (1.7, 11.4)]]),
    'd': (8.2, [_arc(3.4, 4, 3.1, 4, 0, 360), [(6.5, 0), (6.5, 12)],
                [(5.5, 0), (7.5, 0)], [(5.5, 12), (7.5, 12)]]),
    'a': (7.6, [_arc(3.4, 4, 3.1, 4, 0, 360), [(6.5, 0), (6.5, 8)],
                [(5.5, 0), (7.5, 0)], [(5.5, 8), (7.5, 8)]]),
    'y': (7.4, [[(0.4, 8), (3.7, 2.6), (7.0, 8)],
                [(3.7, 2.6), (2.8, -1.2), (1.4, -2.8)]]),
    'N': (9.6, [[(1.2, 0), (1.2, 12)], [(8.4, 0), (8.4, 12)],
                [(1.2, 12), (8.4, 0)], [(0.2, 0), (2.2, 0)],
                [(0.2, 12), (2.2, 12)], [(7.4, 0), (9.4, 0)],
                [(7.4, 12), (9.4, 12)]]),
    'o': (7.8, [_arc(3.9, 4, 3.5, 4, 0, 360)]),
    'v': (7.4, [[(0.4, 8), (3.7, 0), (7.0, 8)]]),
    'e': (7.4, [[(0.6, 4.6), (6.8, 4.6)], _arc(3.6, 4, 3.2, 4, 15, 330)]),
    'm': (11.8, [[(1.2, 0), (1.2, 8)], [(0.3, 0), (2.3, 0)],
                 [(1.2, 5.0), (2.2, 7.6), (4.2, 8.0), (5.8, 6.4), (5.8, 0)],
                 [(4.9, 0), (6.7, 0)],
                 [(5.8, 5.0), (6.8, 7.6), (8.8, 8.0), (10.4, 6.4), (10.4, 0)],
                 [(9.5, 0), (11.3, 0)]]),
    'b': (8.2, [[(1.2, 0), (1.2, 12)], [(0.2, 0), (2.2, 0)],
                [(0.2, 12), (2.2, 12)], _arc(4.6, 4, 3.1, 4, 0, 360)]),
    '2': (8.0, [[(1.0, 10.2), (2.4, 11.8), (5.0, 11.9), (6.8, 10.4),
                 (6.6, 8.2), (1.4, 0)], [(0.4, 0), (7.6, 0)]]),
    '0': (8.4, [_arc(4.2, 6, 3.6, 6, 0, 360)]),
    '6': (8.0, [[(6.4, 10.8), (4.2, 11.9), (2.0, 9.8), (1.0, 6.4), (1.2, 3.0),
                 (2.8, 0.6), (5.0, 0.2), (6.6, 1.6), (6.6, 4.2), (5.2, 6.0),
                 (3.0, 6.2), (1.4, 5.0)]]),
}


def _font_pts(stroke):
    """Expand one font stroke (polyline or arc tuple) to font-space points."""
    if isinstance(stroke, tuple):
        _, cx, cy, rx, ry, a0, a1 = stroke
        n = max(5, int(abs(a1 - a0) / 12))
        pts = []
        for i in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * i / n)
            pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
        return pts
    return stroke


def text_width(s, size, tracking=0.0, font=None):
    font = GLYPHS if font is None else font
    scale = size / 12.0
    w = 0.0
    for ch in s:
        g = font.get(ch) or GLYPHS.get(ch) or GLYPHS[' ']
        w += g[0] * scale
    if len(s) > 1:
        w += tracking * (len(s) - 1)
    return w


def draw_text(x, y, s, size, color, weight, tracking=0.0, font=None,
              align='l', shear=0.0):
    """Draw one line of stroke text; (x, y) is the baseline start.
    size = cap height in final px; weight = stroke width in final px."""
    font = GLYPHS if font is None else font
    scale = size / 12.0
    w = text_width(s, size, tracking, font)
    if align == 'c':
        x -= w / 2.0
    elif align == 'r':
        x -= w
    cx = x
    for ch in s:
        g = font.get(ch) or GLYPHS.get(ch) or GLYPHS[' ']
        adv, strokes = g
        for stroke in strokes:
            pts = _font_pts(stroke)
            sp = [(cx + (px + shear * py) * scale, y - py * scale)
                  for (px, py) in pts]
            if len(sp) == 1:
                fill_circle(sp[0][0], sp[0][1], weight / 2.0, color)
            else:
                polyline(sp, weight, color)
        cx += adv * scale + tracking
    return cx


def wrap_text(s, size, maxw, tracking=0.0, font=None):
    """Greedy word wrap on the font's own advances."""
    words = s.split(' ')
    lines = []
    cur = ''
    for wd in words:
        trial = wd if not cur else cur + ' ' + wd
        if text_width(trial, size, tracking, font) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(x, y, s, size, color, weight, maxw, lh, tracking=0.0,
                 font=None, max_lines=None):
    """Draw wrapped text starting with baseline y; returns last baseline."""
    lines = wrap_text(s, size, maxw, tracking, font)
    if max_lines is not None:
        lines = lines[:max_lines]
    yy = y
    for ln in lines:
        draw_text(x, yy, ln, size, color, weight, tracking, font)
        yy += lh
    return yy - lh


def wgt(size, ratio, minpx):
    """Stroke weight for a text block: never below the minimum pixel rule."""
    return max(minpx, size * ratio)

# ------------------------------------------------------------------ output
def downscale():
    """Box-downscale the 4096 canvas to 1024 with SWAR big-int sums:
    each byte is spread into a 16-bit lane, rows and neighbours are added
    in parallel, then shifted back - exact 4x4 means, C speed."""
    out = bytearray(W * W * 3)
    stride4 = W4 * 3
    for oy in range(W):
        ints = []
        for dy in range(SS):
            row = bytes(FB[(oy * SS + dy) * stride4:
                           (oy * SS + dy) * stride4 + stride4])
            ba = bytearray(len(row) * 2)
            ba[0::2] = row
            ints.append(int.from_bytes(ba, 'little'))
        v = ints[0] + ints[1] + ints[2] + ints[3]
        h = v + (v >> 48) + (v >> 96) + (v >> 144)
        res = (h >> 4).to_bytes(len(row) * 2, 'little')
        # Lane 3p+c of the sum holds buffer pixels p..p+3, so output
        # pixel p (buffer pixels 4p..4p+3) sits at lane 12p+c: gather
        # each channel with a 24-byte stride, then interleave.
        orow = bytearray(W * 3)
        orow[0::3] = res[0::24]
        orow[1::3] = res[2::24]
        orow[2::3] = res[4::24]
        out[oy * W * 3:(oy + 1) * W * 3] = orow
    return bytes(out)


def save_png(path):
    raw = downscale()
    stride = W * 3
    scan = bytearray()
    for yy in range(W):
        scan.append(0)
        scan += raw[yy * stride:(yy + 1) * stride]
    comp = zlib.compress(bytes(scan), 6)

    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data +
                struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', W, W, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', comp)
    png += chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)


# ------------------------------------------------------------------- page
M = 22                      # page margin
CW = W - 2 * M              # content width = 980

# Top line
fill_rect(M, 13, 9, 9, RED)
draw_text(M + 15, 22, "THE WORLD IN ONE DAY", 10.5, INK,
          wgt(10.5, 0.17, 1.6), tracking=0.8)
draw_text(W - M, 22, "40 STORIES · 7 REGIONS · EVERY ONE DATED "
          "FRIDAY 20 NOVEMBER 2026", 8.8, GREY, wgt(8.8, 0.18, 1.5),
          tracking=0.3, align='r')
fill_rect(M, 28, CW, 1.6, INK)

# Masthead: red calendar box + serif display line
fill_rect(M, 38, 94, 76, RED)
draw_text(M + 47, 56, "NOV", 12, WHITE, 2.0, tracking=2.0, align='c')
draw_text(M + 47, 93, "20", 38, WHITE, 5.4, tracking=1.0, align='c')
draw_text(M + 47, 108, "FRI · 2026", 8.5, WHITE, 1.5, tracking=0.6,
          align='c')
draw_text(132, 100, "Friday 20 November 2026", 57, INK, 6.4,
          tracking=0.6, font=SERIF)
fill_rect(M, 121, CW, 1.4, INK)

# Red italic sub-headline naming the four lead stories
draw_text(M, 140, "Russian missiles hit Kyiv's bridges · Cyclone Akvan "
          "strikes India · An AI sell-off sinks world markets · "
          "Bitcoin breaks $60,000", 12.3, RED, wgt(12.3, 0.17, 2.1),
          tracking=0.1, shear=0.16)
fill_rect(M, 148, CW, 1.0, INK)

# The day in figures: six big numbers, red dividers
draw_text(M, 162, "THE DAY IN FIGURES", 8.5, GREY, 1.5, tracking=1.2)
FIGS = [
    ("3", "bridges hit", "in Kyiv"),
    ("370,000", "evacuated for", "Cyclone Akvan"),
    ("-5.28%", "Nasdaq, Friday's", "close in New York"),
    ("$58,678", "Bitcoin's low", "on Friday"),
    ("144>80", "COP31 draft cut,", "pages, in Antalya"),
    ("5.1bn", "pounds a year,", "UK-EU food deal"),
]
_colw = CW / 6.0
for _i, (_num, _c1, _c2) in enumerate(FIGS):
    _x = M + _i * _colw
    if _i:
        fill_rect(_x - 9, 156, 1.6, 50, RED)
    draw_text(_x, 190, _num, 24, INK, wgt(24, 0.15, 3.4), tracking=0.2)
    draw_text(_x, 202, _c1, 7.8, GREY, wgt(7.8, 0.19, 1.5))
    draw_text(_x, 213, _c2, 7.8, GREY, wgt(7.8, 0.19, 1.5))

# Region bar: honest counts, summing to 40
REGIONS = [
    ("EUROPE 6", 136, BLUE), ("ASIA 11", 250, RED),
    ("AMERICAS 11", 250, TEAL), ("AFRICA 1", 62, GOLD),
    ("MIDDLE EAST 4", 92, BROWN), ("OCEANIA 2", 76, GREEN),
    ("WORLD 5", 114, INK),
]
_rx = M
for _label, _w, _c in REGIONS:
    fill_rect(_rx, 222, _w, 19, _c)
    draw_text(_rx + _w / 2.0, 235.5, _label, 9, WHITE,
              wgt(9, 0.19, 1.7), tracking=0.4, align='c')
    _rx += _w

# ------------------------------------------------------------- hero scenes
def _stars(bx, by, bw, bh, n, col):
    for i in range(n):
        sx = bx + (i * 47.31) % bw
        sy = by + 20 + (i * 29.73) % max(10, bh - 30)
        fill_circle(sx, sy, 0.9, col)


def scene_kyiv(bx, by, bw, bh):
    fill_rect(bx, by, bw, bh, NAVY)
    _stars(bx, by, bw, bh, 34, (198, 208, 228))
    fill_circle(bx + bw - 34, by + 32, 7, (232, 229, 198))
    # city blocks with lit windows
    for i, (ox, hh) in enumerate([(6, 26), (34, 34), (66, 22), (238, 30),
                                  (268, 24), (294, 36)]):
        fill_rect(bx + ox, by + bh - 14 - hh, 24, hh, (9, 11, 24))
        for k in range(4):
            fill_rect(bx + ox + 4 + (k % 2) * 10,
                      by + bh - 20 - hh + (k // 2) * 10 + (i % 3) * 2,
                      4, 5, (238, 196, 92))
    # river and bridge
    fill_rect(bx, by + bh - 14, bw, 14, (38, 66, 98))
    deck = by + bh - 20
    fill_rect(bx + 8, deck, bw - 16, 3.4, (14, 16, 28))
    for tx in (bx + 70, bx + bw - 70):
        fill_rect(tx, deck - 26, 3.4, 26, (14, 16, 28))
    polyline(arc_pts(bx + 70, deck - 40, bw / 2 - 70, 15, 180, 360), 1.3,
             (120, 130, 150))
    for sx in range(0, 5):
        xx = bx + 70 + sx * (bw - 140) / 4.0
        thick_line(xx, deck - 25 + abs(sx - 2) * 3.4, xx, deck, 0.9,
                   (120, 130, 150))
    # missile trails and bursts
    for (cx, cy, rx, ry, a0, a1) in [
            (bx + 60, by - 66, 120, 108, 55, 96),
            (bx + 210, by - 90, 130, 120, 62, 100),
            (bx + 300, by - 40, 90, 84, 120, 168)]:
        polyline(arc_pts(cx, cy, rx, ry, a0, a1), 1.7, (243, 164, 62))
    for (ex, ey) in [(bx + 128, by + 52), (bx + 252, by + 44)]:
        fill_circle(ex, ey, 3.2, (250, 120, 50))
        for a in range(0, 360, 60):
            ar = math.radians(a)
            thick_line(ex, ey, ex + 8 * math.cos(ar), ey + 8 * math.sin(ar),
                       1.2, (250, 150, 60))


def scene_akvan(bx, by, bw, bh):
    fill_rect(bx, by, bw, bh, SKY)
    for (ex, ey, rx, ry) in [(60, 30, 52, 10), (170, 24, 66, 12),
                             (268, 32, 48, 9)]:
        fill_ellipse(bx + ex, by + ey, rx, ry, (148, 158, 168))
    cx, cy = bx + bw * 0.60, by + bh * 0.54
    for r in (7, 13, 19, 25):
        polyline(arc_pts(cx, cy, r, r * 0.76, 25, 305), 2.3, (64, 86, 108))
    fill_rect(bx, by + bh - 22, bw, 22, SEA)
    polyline(arc_pts(bx + 40, by + bh - 16, 60, 7, 180, 360), 1.4, WHITE)
    polyline(arc_pts(bx + 190, by + bh - 12, 70, 8, 180, 360), 1.4, WHITE)
    # bending palms
    for px, lean in [(36, 10), (66, 14)]:
        thick_line(bx + px, by + bh - 18, bx + px + lean, by + 34, 2.6, BROWN)
        for a in (200, 250, 300, 340):
            ar = math.radians(a)
            polyline(arc_pts(bx + px + lean + 10 * math.cos(ar),
                             by + 34 + 6 * math.sin(ar), 11, 6, a - 40, a + 30),
                     1.7, GREEN)
    for i in range(14):
        rx = bx + 190 + (i * 23.7) % 110
        ry = by + 26 + (i * 13.1) % 34
        thick_line(rx, ry, rx - 3, ry + 7, 1.0, (86, 116, 146))


def scene_markets(bx, by, bw, bh):
    fill_rect(bx, by, bw, bh, (30, 34, 46))
    for i in range(4):
        fill_rect(bx + 6, by + 26 + i * 13, bw - 12, 0.8, (62, 68, 84))
    for i, hh in enumerate([16, 24, 13, 30, 20, 26, 15, 22]):
        fill_rect(bx + 12 + i * 38, by + bh - hh, 26, hh, (18, 21, 30))
    pts = [(bx + 14, by + 30), (bx + 62, by + 34), (bx + 104, by + 44),
           (bx + 148, by + 42), (bx + 196, by + 56), (bx + 240, by + 62),
           (bx + 282, by + 74)]
    polyline(pts, 2.8, RED)
    ex, ey = pts[-1]
    fill_poly([(ex, ey), (ex - 11, ey - 3), (ex - 4, ey + 9)], RED)
    # yen coin
    cx, cy = bx + bw - 40, by + 34
    fill_circle(cx, cy, 12, GOLD)
    fill_circle(cx, cy, 9.6, (198, 152, 44))
    thick_line(cx - 4.4, cy - 6.4, cx, cy - 0.6, 1.8, (84, 60, 8))
    thick_line(cx + 4.4, cy - 6.4, cx, cy - 0.6, 1.8, (84, 60, 8))
    thick_line(cx, cy - 0.6, cx, cy + 6.6, 1.8, (84, 60, 8))
    thick_line(cx - 4.2, cy + 0.8, cx + 4.2, cy + 0.8, 1.5, (84, 60, 8))
    thick_line(cx - 4.2, cy + 3.4, cx + 4.2, cy + 3.4, 1.5, (84, 60, 8))


def label_band(bx, by, bw, bh, label, kicker, col, lsize):
    fill_rect(bx, by, bw, bh, col)
    draw_text(bx + 8, by + bh - 4.5, label, lsize, WHITE,
              wgt(lsize, 0.20, 2.2), tracking=0.5)
    if kicker:
        draw_text(bx + bw - 7, by + bh - 5.5, kicker, lsize - 3.4, WHITE,
                  wgt(lsize - 3.4, 0.19, 1.5), tracking=0.3, align='r')


def hero(x, y, w, h, scene, label, kicker, band_col, region, rcol,
         headline, standfirst):
    fill_rect(x, y, w, h, PANEL)
    outline_rect(x, y, w, h, 1.1, RULE)
    bx, by, bw, bh = x + 1, y + 1, w - 2, 76
    scene(bx, by, bw, bh)
    label_band(bx, by, bw, 18, label, kicker, band_col, 11.5)
    draw_text(x + 9, y + 93, region, 8.3, rcol, wgt(8.3, 0.20, 1.65),
              tracking=0.3)
    hend = draw_wrapped(x + 9, y + 117, headline, 16, INK,
                        wgt(16, 0.16, 2.6), w - 18, 19.5)
    draw_wrapped(x + 9, hend + 17, standfirst, 9.2, (52, 48, 42),
                 wgt(9.2, 0.185, 1.7), w - 18, 12.3)


HY = 250
HW = (CW - 20) / 3.0
hero(M, HY, HW, 214, scene_kyiv, "KYIV", "OVERNIGHT", NAVY,
     "1 · EUROPE · WAR — CONFIRMED · REUTERS/BBC", RED,
     "Russia fires 110+ missiles at Kyiv, hits three bridges",
     "Some 400 drones joined the barrage hours after Putin vowed payback "
     "for the Crimea Bridge strikes. Eight people were killed across "
     "Ukraine; power, heat and water were cut in the capital.")
hero(M + HW + 10, HY, HW, 214, scene_akvan, "CYCLONE AKVAN",
     "LANDFALL 07:30 · GOPALPUR", RED,
     "2 · ASIA · WEATHER — CONFIRMED · IMD", TEAL,
     "Cyclone Akvan comes ashore on the Odisha coast",
     "Winds of 70-80 km/h, gusting to 90, crossed near Gopalpur after "
     "370,000 people were moved into 9,341 shelters. No deaths or major "
     "damage were reported in the first hours.")
hero(M + 2 * HW + 20, HY, HW, 214, scene_markets, "AI SELL-OFF",
     "FRIDAY'S CLOSE", NAVY,
     "3 · WORLD · MARKETS — CONFIRMED · AP", BLUE,
     "AI sell-off sinks Asia, then Wall Street",
     "Taipei fell 6.2%, Tokyo 4.8% and Seoul 5.2% as chip stocks slid; "
     "New York's Nasdaq then lost 5.28% and the S&P 500 fell for a "
     "seventh day. Anthropic dropped 9.1% on its second day.")

# ------------------------------------------------------------ panel scenes
def s_btc(bx, by, bw, bh):
    fill_rect(bx, by, bw, bh, (26, 25, 30))
    fill_rect(bx, by + bh - 7, bw, 7, (54, 51, 58))
    polyline([(bx + 120, by + bh - 7), (bx + 132, by + bh - 3),
              (bx + 142, by + bh - 7), (bx + 152, by + bh - 4)], 1.2,
             (150, 60, 50))
    cx, cy = bx + 36, by + bh - 17
    fill_circle(cx, cy, 10.5, GOLD)
    fill_circle(cx, cy, 8.2, (200, 154, 46))
    draw_text(cx, cy + 4.4, "B", 12.5, (84, 60, 8), 2.1, align='c')
    thick_line(cx - 3.2, cy - 9.5, cx - 3.2, cy + 9.5, 1.4, (84, 60, 8))
    pts = [(bx + 74, by + 17), (bx + 108, by + 21), (bx + 138, by + 26),
           (bx + 170, by + 32)]
    polyline(pts, 2.3, RED)
    fill_poly([(pts[-1][0], pts[-1][1]), (pts[-1][0] - 10, pts[-1][1] - 3),
               (pts[-1][0] - 3, pts[-1][1] + 8)], RED)


def s_cop(bx, by, bw, bh):
    fill_rect(bx, by, bw, bh, (206, 224, 232))
    fill_circle(bx + 38, by + 25, 11.5, BLUE)
    for (ox, oy, r) in [(-4, -3, 4.4), (5, 2, 5.2), (-2, 6, 3.6)]:
        fill_circle(bx + 38 + ox, by + 25 + oy, r, GREEN)
    fill_rect(bx + 108, by + 27, 34, 9, (92, 92, 98))
    fill_rect(bx + 114, by + 19, 5, 8, (92, 92, 98))
    fill_circle(bx + 116, by + 15, 3.4, (168, 172, 176))
    fill_circle(bx + 121, by + 12, 4.4, (178, 182, 186))
    tx = bx + 164
    fill_rect(tx, by + 15, 5.5, 17, WHITE)
    fill_rect(tx + 1.4, by + 23, 2.7, 9, RED)
    fill_circle(tx + 2.7, by + 33.5, 3.8, RED)


def s_ukeu(bx, by, bw, bh):
    fill_rect(bx, by, bw, bh, TINT)
    fill_rect(bx + 12, by + 16, 46, 18, BLUE)
    polyline([(bx + 12, by + 16), (bx + 58, by + 34)], 1.6, WHITE)
    polyline([(bx + 12, by + 34), (bx + 58, by + 16)], 1.6, WHITE)
    fill_rect(bx + 31, by + 16, 8, 18, RED)
    fill_rect(bx + 12, by + 22.5, 46, 5, RED)
    fill_rect(bx + 128, by + 16, 46, 18, BLUE)
    for a in range(0, 360, 60):
        ar = math.radians(a)
        fill_circle(bx + 151 + 6.4 * math.cos(ar), by + 25 + 6.4 * math.sin(ar),
                    1.7, GOLD)
    fill_circle(bx + 151, by + 25, 1.7, GOLD)
    fill_rect(bx + 72, by + 25, 36, 11, BROWN)
    thick_line(bx + 72, by + 30.5, bx + 108, by + 30.5, 1.2, (96, 64, 38))
    thick_line(bx + 90, by + 25, bx + 90, by + 36, 1.2, (96, 64, 38))


def s_icj(bx, by, bw, bh):
    fill_rect(bx, by, bw, bh, (233, 227, 211))
    fill_poly([(bx + 18, by + 21), (bx + 94, by + 13), (bx + 170, by + 21)],
              (96, 88, 74))
    for i in range(4):
        fill_rect(bx + 30 + i * 34, by + 22, 9, 11, (216, 208, 190))
    fill_rect(bx + 22, by + 33, 144, 3, (96, 88, 74))


def s_japan(bx, by, bw, bh):
    fill_rect(bx, by, bw, bh, TINT)
    fill_poly([(bx + 20, by + 17), (bx + 56, by + 17), (bx + 69, by + 25.5),
               (bx + 56, by + 34), (bx + 20, by + 34)], RED)
    fill_circle(bx + 27, by + 25.5, 2.7, TINT)
    pts = [(bx + 92, by + 33), (bx + 114, by + 21), (bx + 136, by + 25),
           (bx + 162, by + 15)]
    polyline(pts, 2.7, GREEN)
    fill_poly([(pts[-1][0], pts[-1][1]), (pts[-1][0] - 10, pts[-1][1] + 1),
               (pts[-1][0] - 3, pts[-1][1] + 9)], GREEN)


def s_italy(bx, by, bw, bh):
    fill_rect(bx, by, bw, bh, SKY)
    fill_rect(bx, by + bh - 6, bw, 6, (150, 140, 120))
    for i, (ox, pc) in enumerate([(34, RED), (84, BLUE), (134, TEAL)]):
        cx = bx + ox
        fill_circle(cx, by + 21, 3.5, INK)
        thick_line(cx, by + 24.5, cx, by + 32, 2.1, INK)
        thick_line(cx + 2, by + 27, cx + 7, by + 21, 1.4, INK)
        fill_rect(cx + 6, by + 14, 17, 10.5, pc)
        fill_rect(cx + 9, by + 18.5, 11, 1.6, WHITE)


def s_gold(bx, by, bw, bh):
    fill_rect(bx, by, bw, bh, (35, 33, 29))

    def bar(x, y, w):
        fill_poly([(x, y), (x + w, y), (x + w - 4, y - 6), (x + 4, y - 6)],
                  GOLD)
    bar(bx + 18, by + 24, 34)
    bar(bx + 62, by + 29, 34)
    bar(bx + 106, by + 34, 34)
    pts = [(bx + 120, by + 16), (bx + 146, by + 21), (bx + 172, by + 27)]
    polyline(pts, 2.2, RED)


def s_mercury(bx, by, bw, bh):
    fill_rect(bx, by, bw, bh, NAVY)
    _stars(bx, by, bw, bh, 12, (190, 200, 220))
    fill_circle(bx + 52, by + 24, 12.5, (172, 152, 130))
    for (ox, oy, r) in [(-4, -3, 2.6), (4, 3, 3.2), (1, -6, 1.9)]:
        fill_circle(bx + 52 + ox, by + 24 + oy, r, (146, 126, 104))
    sx, sy = bx + 128, by + 22
    fill_rect(sx, sy - 3, 15, 6.5, WHITE)
    fill_rect(sx - 13, sy - 5, 11, 10, (86, 130, 190))
    fill_rect(sx + 17, sy - 5, 11, 10, (86, 130, 190))
    thick_line(sx + 7, sy + 3, sx + 16, sy + 10, 1.2, WHITE)
    fill_circle(sx + 17, sy + 11, 1.8, GOLD)


def s_sudan(bx, by, bw, bh):
    fill_rect(bx, by, bw, bh, SAND)
    fill_circle(bx + 164, by + 20, 6.5, GOLD)
    fill_poly([(bx + 44, by + 36), (bx + 88, by + 36), (bx + 76, by + 27),
               (bx + 56, by + 27)], (122, 92, 60))
    cx, cy = bx + 128, by + 21
    thick_line(cx - 13, cy - 6, cx + 13, cy + 6, 1.7, INK)
    thick_line(cx - 13, cy + 6, cx + 13, cy - 6, 1.7, INK)
    fill_rect(cx - 6, cy - 2.2, 12, 4.4, INK)
    for (ox, oy) in [(-13, -6), (13, -6), (-13, 6), (13, 6)]:
        fill_circle(cx + ox, cy + oy, 2.5, (88, 82, 76))


def s_cricket(bx, by, bw, bh):
    fill_rect(bx, by, bw, bh, (88, 132, 72))
    fill_rect(bx + 66, by + 15, 52, 21, SAND)
    for i in range(3):
        thick_line(bx + 148 + i * 5, by + 20, bx + 148 + i * 5, by + 33,
                   1.9, (232, 200, 110))
    fill_poly([(bx + 28, by + 34), (bx + 37, by + 34), (bx + 52, by + 16),
               (bx + 45, by + 12.5)], (219, 193, 142))
    fill_circle(bx + 94, by + 25, 4.6, RED)
    polyline(arc_pts(bx + 94, by + 25, 3.4, 4.4, 300, 60), 0.9, WHITE)


def small_panel(x, y, w, h, scene, label, band_col, region, headline, body):
    fill_rect(x, y, w, h, PANEL)
    outline_rect(x, y, w, h, 1.1, RULE)
    bx, by, bw, bh = x + 1, y + 1, w - 2, 36
    scene(bx, by, bw, bh)
    label_band(bx, by, bw, 13, label, "", band_col, 8.3)
    draw_text(x + 7, y + 48, region, 6.6, GREY, wgt(6.6, 0.22, 1.45),
              tracking=0.15)
    hend = draw_wrapped(x + 7, y + 63, headline, 10.3, INK,
                        wgt(10.3, 0.17, 1.75), w - 14, 12.4)
    draw_wrapped(x + 7, hend + 13.5, body, 7.55, (52, 48, 42),
                 wgt(7.55, 0.195, 1.45), w - 14, 9.9)


PY1, PY2, PH = 472, 640, 160
PW = (CW - 32) / 5.0


def _px(i):
    return M + i * (PW + 8)


# Panel 4 is custom: the BlackRock IBIT outflow is a named figure row.
def btc_panel(x, y, w, h):
    fill_rect(x, y, w, h, PANEL)
    outline_rect(x, y, w, h, 1.1, RULE)
    bx, by, bw, bh = x + 1, y + 1, w - 2, 36
    s_btc(bx, by, bw, bh)
    label_band(bx, by, bw, 13, "BITCOIN < $60K", "", RED, 8.3)
    draw_text(x + 7, y + 48, "4 · WORLD · CRYPTO · CONF · REUTERS", 6.6,
              GREY, wgt(6.6, 0.22, 1.45), tracking=0.15)
    draw_wrapped(x + 7, y + 63, "Bitcoin breaks below $60,000", 10.3, INK,
                 wgt(10.3, 0.17, 1.75), w - 14, 12.4)
    draw_wrapped(x + 7, y + 76, "First dip under $60k since July, to a "
                 "$58,678 low. Fear gauge: 11 of 100 - extreme fear.",
                 7.55, (52, 48, 42), wgt(7.55, 0.195, 1.45), w - 14, 9.9)
    draw_text(x + 7, y + 112, "IBIT -$541.1M", 11.5, RED,
              wgt(11.5, 0.18, 2.1))
    draw_wrapped(x + 7, y + 122.5, "BlackRock's biggest one-day outflow "
                 "on record (Thu 19)", 6.9, GREY, wgt(6.9, 0.21, 1.45),
                 w - 14, 8.8)
    draw_wrapped(x + 7, y + 143, "US spot BTC ETFs -$582.3m on 19 Nov; "
                 "about $3.47bn out across November (Farside).", 7.3,
                 (52, 48, 42), wgt(7.3, 0.20, 1.45), w - 14, 9.4)


btc_panel(_px(0), PY1, PW, PH)
small_panel(_px(1), PY1, PW, PH, s_cop, "COP31: NO DEAL", NAVY,
            "5 · WORLD · CLIMATE · CONF · AFP/AP",
            "COP31 ends its last day with no deal",
            "Talks in Antalya ran into overtime after the draft dropped "
            "every mention of fossil fuels and a $120bn adaptation "
            "target. A third draft was promised for Saturday.")
small_panel(_px(2), PY1, PW, PH, s_ukeu, "UK-EU DEAL", BLUE,
            "6 · EUROPE · DIPLOMACY · CONF · REUTERS",
            "UK and EU seal a 'reset' deal",
            "Food checks eased in a deal worth 5.1bn pounds a year from "
            "2028, carbon markets linked, 100,000 youth places a year "
            "each way. University fees stayed unresolved.")
small_panel(_px(3), PY1, PW, PH, s_icj, "WORLD COURT", INK,
            "7 · ASIA · JUSTICE · CONF · REUTERS/UN",
            "Myanmar calls genocide ruling 'unfair'",
            "The World Court's judgment (Thu) first found a state itself "
            "responsible for genocide, over the Rohingya. Myanmar "
            "rejected it Friday; redress and safe return were ordered.")
small_panel(_px(4), PY1, PW, PH, s_japan, "JAPAN: +2.3%", RED,
            "8 · ASIA · ECONOMY · CONF · OFFICIAL",
            "Japan inflation rises to 2.3%",
            "October prices rose 2.3% in a year, core 2.2%, keeping a "
            "December Bank of Japan rate rise to 1.5% in view.")
small_panel(_px(0), PY2, PW, PH, s_italy, "ITALY: STRIKE", RED,
            "9 · EUROPE · LABOUR · CONF · ANSA",
            "General strike across Italy",
            "The CGIL union's 24-hour stoppage over pay and the budget "
            "brought marches to more than 100 cities; rail freight "
            "halted for 23 hours from 9pm.")
small_panel(_px(1), PY2, PW, PH, s_gold, "GOLD < $3,600", INK,
            "10 · WORLD · MARKETS · CONF · KITCO",
            "Gold breaks under $3,600",
            "A 14-month low near $3,532 as investors sold the metal to "
            "cover AI-stock losses; silver slid under $42. Worst week "
            "in eight months.")
small_panel(_px(2), PY2, PW, PH, s_mercury, "MERCURY", NAVY,
            "11 · WORLD · SPACE · CONF · ESA",
            "BepiColombo reaches Mercury",
            "After eight years and 6bn miles the European-Japanese "
            "probe arrived; Saturday's burn should make it only the "
            "second craft ever to orbit Mercury.")
small_panel(_px(3), PY2, PW, PH, s_sudan, "SUDAN: DRONE", BROWN,
            "12 · AFRICA · CONFLICT · REP · DABANGA",
            "Drone strike kills 10 at a Sudan gold mine",
            "The strike hit the Bajoun mining site in South Kordofan, "
            "in the civil war between the army and the RSF.")
small_panel(_px(4), PY2, PW, PH, s_cricket, "PHILLIPS: 118", GREEN,
            "13 · OCEANIA · CRICKET · CONFIRMED",
            "Phillips hits 118 against India",
            "Glenn Phillips' Wellington century made him the first "
            "player with hundreds against India in all three formats "
            "in one year. Nicholls made 175; New Zealand 368.")

# --------------------------------------------------------- bottom section
draw_text(M, 818, "WHERE IT HAPPENED", 9.5, INK, wgt(9.5, 0.18, 1.7),
          tracking=0.6)
draw_text(352, 818, "ALSO ON FRIDAY 20 NOVEMBER — 27 MORE STORIES", 9.5,
          INK, wgt(9.5, 0.18, 1.7), tracking=0.4)
fill_rect(M, 824, CW, 1.0, RULE)

MAPX, MAPY, MAPW, MAPH = M, 830, 308, 128
fill_rect(MAPX, MAPY, MAPW, MAPH, (238, 232, 214))
outline_rect(MAPX, MAPY, MAPW, MAPH, 1.0, RULE)
MAPROWS = [
    "        #####                       ##########        ",
    "     ##########      ##           #################   ",
    "      ########      ####        ##################    ",
    "       ######        ##        ######  ##########     ",
    "        ####                  ##################      ",
    "        #####                  ################       ",
    "         ####                   ### ##########        ",
    "         ###                     ############         ",
    "          ##          ##          ##########          ",
    "          ###        ####          ########           ",
    "           ####     ######          ######            ",
    "           ####      ####           ####     ##       ",
    "            ###      ###            ###     ####      ",
    "            ##       ##                      ###      ",
    "            ##       #                                ",
    "                     #                                ",
    "                                                      ",
]
_cw = MAPW / 52.0
_ch = MAPH / 17.0
for _r, _row in enumerate(MAPROWS):
    for _c, _ch_c in enumerate(_row.ljust(52)[:52]):
        if _ch_c == '#':
            fill_circle(MAPX + (_c + 0.5) * _cw, MAPY + (_r + 0.5) * _ch,
                        1.7, (110, 132, 158))


def _pin(n, lon, lat):
    px = MAPX + (lon + 180) / 360.0 * MAPW
    py = MAPY + (75 - lat) / 135.0 * MAPH
    fill_circle(px, py, 4.6, RED)
    draw_text(px, py + 1.9, str(n), 5.2 if n < 10 else 4.4, WHITE,
              wgt(5.2, 0.22, 1.3), align='c')


_pin(1, 30.5, 50.2)     # Kyiv
_pin(2, 85.1, 19.3)     # Gopalpur
_pin(3, -122.4, 37.8)   # markets: San Francisco / US tech
_pin(4, -74.0, 40.7)    # crypto: New York
_pin(5, 30.7, 36.9)     # Antalya
_pin(6, 4.35, 50.8)     # Brussels
_pin(7, 99.0, 21.9)     # Myanmar
_pin(8, 139.7, 35.7)    # Tokyo
_pin(9, 14.0, 37.5)     # Italy
_pin(10, 8.5, 47.2)     # gold: Zurich
_pin(12, 30.0, 15.0)    # Sudan
_pin(13, 174.8, -41.3)  # Wellington
# 11 is off the map: a star at the top-right corner of the map box.
_sx, _sy = MAPX + MAPW - 12, MAPY + 10
fill_poly([(_sx, _sy - 6), (_sx + 1.8, _sy - 1.8), (_sx + 6, _sy - 1.6),
           (_sx + 2.6, _sy + 1.2), (_sx + 3.8, _sy + 5.6), (_sx, _sy + 2.6),
           (_sx - 3.8, _sy + 5.6), (_sx - 2.6, _sy + 1.2),
           (_sx - 6, _sy - 1.6), (_sx - 1.8, _sy - 1.8)], GOLD)
draw_text(_sx - 8, _sy + 13.5, "11", 5.2, INK, wgt(5.2, 0.22, 1.3),
          align='c')
draw_text(MAPX + 4, MAPY + MAPH - 5, "Pins 1-13 as numbered on the page; "
          "11 = Mercury, off the map.", 6.2, GREY, wgt(6.2, 0.21, 1.35))

ALSO = [
    (14, "New York: Michigan sentiment 51.5 final; inflation hopes 3.7%", "C"),
    (15, "Gaza: Israeli raid past the Yellow Line ends; troops withdraw", "R"),
    (16, "Yongbyon: IAEA says N. Korea expanding uranium enrichment", "R"),
    (17, "Poland: Warsaw says a Russian missile landed on its soil", "R"),
    (18, "Washington: IMF warns world debt will near 100% of GDP", "R"),
    (19, "Washington: Senate passes energy permitting plan 62-33", "R"),
    (20, "Caracas: US and Venezuela sign military cooperation deal", "R"),
    (21, "Port-au-Prince: forces kill 34 gang suspects in raid", "R"),
    (22, "Dhaka: violence flares before Hasina's planned return", "R"),
    (23, "Mato Grosso: Brazil recognises Raoni ancestral land", "R"),
    (24, "New York: race to succeed Guterres stalls after 8 votes", "R"),
    (25, "Al-Dahi: mosque set on fire in northern Israel", "R"),
    (26, "Huntsville: Texas executes Reinaldo Dennes, aged 70", "R"),
    (27, "Jurf al-Nasr: Iraq orders Iran-backed militia to leave", "R"),
    (28, "Washington: Trump pardons baseball great Pete Rose", "R"),
    (29, "Sydney: marathon champion Jepchirchir banned 3 years", "R"),
    (30, "Washington: cyber chief Cairncross out; Davies acting", "R"),
    (31, "New York: Anthropic completes its $83 IPO offering", "R"),
    (32, "Hormuz: Brent holds near $92 as shipping risk lingers", "C"),
    (33, "Hong Kong: Hang Seng falls 1.9% in the Asia rout", "C"),
    (34, "Taipei: TSMC -4.8%; Samsung and SK Hynix fall 6-7%", "C"),
    (35, "Seoul: trading curbs trigger twice on the KOSPI", "C"),
    (36, "Antalya: COP31 draft keeps 35%-by-2035 electrify goal", "C"),
    (37, "Odisha: Akvan cancels 47 trains; schools shut in 15 districts", "C"),
    (38, "Kyiv: Zelenskyy says 79 cruise missiles shot down", "R"),
    (39, "Brussels: UK-EU youth movers start in 2030", "C"),
    (40, "Antalya: 'failure' banner interrupts COP31 president", "C"),
]
for _i, (_n, _txt, _tag) in enumerate(ALSO):
    _colx = 352 if _i < 14 else 684
    _yy = 842 + (_i % 14) * 8.8
    _line = "%d %s (%s)" % (_n, _txt, _tag)
    draw_text(_colx, _yy, _line, 7.3, (52, 48, 42), wgt(7.3, 0.20, 1.45))
    draw_text(_colx, _yy, str(_n), 7.3, RED, wgt(7.3, 0.21, 1.55))

# How sure strip
_hx = draw_text(M, 972, "HOW SURE:", 7.4, INK, wgt(7.4, 0.21, 1.55),
                tracking=0.3)
draw_text(_hx + 4, 972, "CONFIRMED = two or more outlets or official "
          "data · REPORTED = one source or an official claim · Counts "
          "are officials' counts where stated.", 7.4, GREY,
          wgt(7.4, 0.20, 1.45))

# Date check box
outline_rect(M, 978, CW, 34, 1.3, RED)
draw_wrapped(M + 8, 988.5, "DATE CHECK — Left out on purpose, each first "
             "reported before or after Friday: the Trump-Xi-Putin "
             "declaration in Shenzhen (Thu 19) · Anthropic's 17% Nasdaq "
             "debut (Thu 19) · the Houthi strike on Riyadh's PIF Tower "
             "(Thu 19) · Bukele's third-term filing (Thu 19) · Fiji's "
             "disaster and Tonga's emergency declarations (Thu 19) · "
             "Denmark's 109-0 Greenland vote (Thu 19) · Kenya's last "
             "Ebola patient went home (11 Nov). Not yet: BepiColombo's "
             "orbit burn (Sat 21) and any final COP31 text (Sat). The "
             "Hormuz tanker-mine claim could not be verified and is not "
             "shown as fact.", 7.2, (52, 48, 42), wgt(7.2, 0.20, 1.45),
             CW - 16, 9.3)
draw_text(M + 8, 988.5, "DATE CHECK", 7.2, RED, wgt(7.2, 0.21, 1.55))

# Sources line
draw_text(M, 1021, "Sources: Reuters · AP · BBC · AFP · IMD · Al Jazeera "
          "· ANSA · Kitco · Farside · official data. All 40 stories "
          "happened, or were first reported, on Friday 20 November 2026. "
          "Original drawings.", 7.0, GREY, wgt(7.0, 0.20, 1.4))


def main():
    outdir = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output')
    os.makedirs(outdir, exist_ok=True)
    save_png(os.path.join(outdir, 'entry.png'))


if __name__ == '__main__':
    main()
