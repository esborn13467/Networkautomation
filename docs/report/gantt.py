#!/usr/bin/env python3
"""Gantt chart for Appendix B -> docs/report/figures/appB_gantt.png
Edit PHASES (name, start, end) to match the real project dates, then run:
    python docs/report/gantt.py   and rebuild the report (python docs/report/make_report.py)
"""
import os
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PHASES = [  # dates given by Esborn on 16 Oct 2026
    ("Chapters 1-3",          date(2026, 4, 1), date(2026, 8, 31)),
    ("Chapters 4-6",          date(2026, 8, 1), date(2026, 10, 31)),
    ("System implementation", date(2026, 8, 1), date(2026, 10, 31)),
]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures", "appB_gantt.png")
# table-style chart (ID, task, dates, duration, one shaded cell per month), as in the guideline report
MONTHS = [date(2026, m, 1) for m in range(4, 11)]          # April .. October 2026
INK, FILL, LINE = "#000000", "#2b2a3d", "#000000"
cols = [("ID", 0.5), ("Task", 2.6), ("Start Date", 1.25), ("Due Date", 1.25), ("Duration", 1.05)]
mw = 0.42                                                  # width of one month column
W = sum(w for _, w in cols) + mw * len(MONTHS)
rh, n = 0.42, len(PHASES)
H = rh * (n + 3)                                           # title row, two header rows, phases
fig, ax = plt.subplots(figsize=(W, H))
ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")


def cell(x, y, w, h, text="", bold=False, fill=None, align="center", size=10):
    ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=fill or "white", edgecolor=LINE, linewidth=0.8))
    if text:
        ax.text(x + (0.08 if align == "left" else w / 2), y + h / 2, text, ha=align, va="center",
                fontsize=size, color=INK, fontweight="bold" if bold else "normal", family="DejaVu Serif")


cell(0, 0, W, rh, "Project Gantt Chart", bold=True, size=12)
x = 0
for name, w in cols:
    cell(x, rh, w, rh * 2, name, bold=True); x += w
cell(x, rh, mw * len(MONTHS), rh, "2026", bold=True)
for i, m in enumerate(MONTHS):
    cell(x + i * mw, rh * 2, mw, rh, m.strftime("%b")[0], bold=True)
for r, (name, s, e) in enumerate(PHASES):
    y = rh * (3 + r); x = 0
    months = (e.year - s.year) * 12 + e.month - s.month + 1
    vals = [str(r + 1), name, s.strftime("%d/%m/%Y"), e.strftime("%d/%m/%Y"), f"{months} months"]
    for (cname, w), v in zip(cols, vals):
        cell(x, y, w, rh, v, align="left" if cname == "Task" else "center"); x += w
    for i, m in enumerate(MONTHS):
        cell(x + i * mw, y, mw, rh, fill=FILL if s <= m <= e or (m.year, m.month) == (s.year, s.month) else None)
fig.savefig(OUT, dpi=200, bbox_inches="tight", pad_inches=0.05)
print("wrote", OUT)
