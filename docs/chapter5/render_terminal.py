#!/usr/bin/env python3
"""
Renders a captured terminal output (results/evidence_*/NN_name.txt) as a terminal-style PNG
for the report. The text is the real output, exactly as captured; only long blank runs are
squeezed and lines can be selected.

  python render_terminal.py <in.txt> <out.png> [--lines 3-20] [--width 100]
"""
import argparse

from PIL import Image, ImageDraw, ImageFont

BG, FG, PROMPT, DIM = (24, 26, 33), (222, 226, 230), (120, 200, 140), (130, 140, 150)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def render(lines, out, width=100, size=17):
    font = ImageFont.truetype(FONT, size)
    cw = font.getbbox("M")[2]
    lh = int(size * 1.45)
    lines = [l.rstrip()[:width] for l in lines]
    pad = 22
    W = pad * 2 + cw * min(width, max(len(l) for l in lines))
    H = pad * 2 + 30 + lh * len(lines)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 30], fill=(45, 48, 56))                       # title bar
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([12 + i * 20, 9, 24 + i * 20, 21], fill=c)
    y = 30 + pad
    for l in lines:
        colour = PROMPT if l.startswith("$ ") else DIM if l.startswith("# ") else FG
        d.text((pad, y), l, font=font, fill=colour)
        y += lh
    img.save(out)


def compact(lines, width=100):
    """Shorten runs of 3+ columns that are blank on every OUTPUT line to 2 columns, so wide
    switch tables fit the page. Underline rows (only dashes and spaces) are shortened along
    with the columns they underline; the "$ command" and "# time" lines are kept as typed
    (wrapped if long). No other character is changed and tables stay aligned."""
    import textwrap
    head = lambda l: l.startswith("$ ") or l.startswith("# ")
    rule = lambda l: l.strip() and set(l.strip()) <= {"-", " "}
    body = [l for l in lines if not head(l) and not rule(l)]
    n = max([len(l) for l in lines if not head(l)] + [1])
    blank = [all(c >= len(l) or l[c] == " " for l in body) for c in range(n)]
    keep, run = [], 0
    for c in range(n):
        run = run + 1 if blank[c] else 0
        keep.append(not (blank[c] and run > 2))
    out = []
    for l in lines:
        if head(l):
            out += textwrap.wrap(l, width, subsequent_indent="  ") or [l]
        else:
            out.append("".join(ch for ch, k in zip(l.ljust(n), keep) if k).rstrip())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--lines", default=None, help="1-based range of lines to keep, e.g. 2-25")
    ap.add_argument("--width", type=int, default=100)
    a = ap.parse_args()
    lines = open(a.src).read().splitlines()
    squeezed = []
    for l in lines:                      # collapse runs of blank lines
        if l.strip() or (squeezed and squeezed[-1].strip()):
            squeezed.append(l)
    if a.lines:
        s, e = (int(x) for x in a.lines.split("-"))
        squeezed = squeezed[s - 1:e]
    render(compact(squeezed, a.width), a.out, a.width)


if __name__ == "__main__":
    main()
