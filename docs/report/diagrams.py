#!/usr/bin/env python3
"""Draws every figure used in the project report (Chapters 2 to 4).

Each figure is drawn at its printed size (inches) so the font sizes in the
code are the font sizes on the page. Output: figures/*.png at 300 dpi.

    python3 diagrams.py            # all figures
    python3 diagrams.py fig4_8     # one figure
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import (Circle, Ellipse, FancyArrowPatch,
                                FancyBboxPatch, Polygon, Rectangle)

plt.rcParams["font.family"] = "Liberation Sans"
plt.rcParams["font.size"] = 8
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
LW = 0.9
GREY = "#f2f2f2"
GREY2 = "#e4e4e4"
BLUE = "#e8eef7"


# ---------------------------------------------------------------- helpers
def canvas(w, h):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=300, facecolor="white", bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print("wrote", name)


def text(ax, x, y, s, fs=8, ha="center", va="center", bold=False, italic=False, z=5, color="black", **kw):
    ax.text(x, y, s, fontsize=fs, ha=ha, va=va, zorder=z, color=color,
            fontweight="bold" if bold else "normal",
            fontstyle="italic" if italic else "normal", linespacing=1.25, **kw)


def rect(ax, x, y, w, h, s=None, fs=8, fill="white", lw=LW, ls="-", rounded=False,
         bold=False, z=2, ha="center", tx=None, ty=None, va="center", ec="black"):
    """Rectangle with lower-left corner (x, y)."""
    if rounded:
        p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.07",
                           fc=fill, ec=ec, lw=lw, ls=ls, zorder=z)
    else:
        p = Rectangle((x, y), w, h, fc=fill, ec=ec, lw=lw, ls=ls, zorder=z)
    ax.add_patch(p)
    if s is not None:
        if tx is None:
            tx = x + w / 2 if ha == "center" else x + 0.08
        if ty is None:
            ty = y + h / 2
        text(ax, tx, ty, s, fs=fs, ha=ha, va=va, bold=bold, z=z + 1)


def ellipse(ax, cx, cy, w, h, s, fs=8, fill="white", z=2):
    ax.add_patch(Ellipse((cx, cy), w, h, fc=fill, ec="black", lw=LW, zorder=z))
    text(ax, cx, cy, s, fs=fs, z=z + 1)


def diamond(ax, cx, cy, w, h, s="", fs=7.5, fill="white", z=2):
    pts = [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)]
    ax.add_patch(Polygon(pts, closed=True, fc=fill, ec="black", lw=LW, zorder=z))
    if s:
        text(ax, cx, cy, s, fs=fs, z=z + 1)


def actor(ax, cx, top, label, fs=8):
    """UML stick figure; top is the top of the head."""
    r = 0.09
    ax.add_patch(Circle((cx, top - r), r, fc="white", ec="black", lw=LW, zorder=3))
    neck = top - 2 * r
    hip = neck - 0.28
    ax.plot([cx, cx], [neck, hip], color="black", lw=LW, zorder=3)
    ax.plot([cx - 0.17, cx + 0.17], [neck - 0.09, neck - 0.09], color="black", lw=LW, zorder=3)
    ax.plot([cx, cx - 0.14], [hip, hip - 0.22], color="black", lw=LW, zorder=3)
    ax.plot([cx, cx + 0.14], [hip, hip - 0.22], color="black", lw=LW, zorder=3)
    text(ax, cx, hip - 0.27, label, fs=fs, va="top")
    return hip - 0.22  # feet


def line(ax, pts, ls="-", lw=LW, color="black", z=1):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, ls=ls, lw=lw, color=color, zorder=z, solid_capstyle="butt")


def arrow(ax, pts, ls="-", head="-|>", lw=LW, color="black", ms=9, z=4, fc=None,
          label=None, seg=0, lpos=0.5, loff=(0, 0.07), fs=7, lha="center", lva="bottom",
          lbg=False, italic=False):
    """Polyline with an arrowhead on the last point."""
    if len(pts) > 2:
        line(ax, pts[:-1], ls=ls, lw=lw, color=color, z=z)
    a = FancyArrowPatch(pts[-2], pts[-1], arrowstyle=head, mutation_scale=ms,
                        lw=lw, ls=ls, color=color, shrinkA=0, shrinkB=0, zorder=z)
    if fc is not None:
        a.set_facecolor(fc)
    ax.add_patch(a)
    if label:
        (x1, y1), (x2, y2) = pts[seg], pts[seg + 1]
        lx = x1 + (x2 - x1) * lpos + loff[0]
        ly = y1 + (y2 - y1) * lpos + loff[1]
        kw = {}
        if lbg:
            kw["bbox"] = dict(fc="white", ec="none", pad=0.6)
        text(ax, lx, ly, label, fs=fs, ha=lha, va=lva, italic=italic, z=z + 1, **kw)


def legend_row(ax, x, y, ls, label, head=True, color="black", lw=LW, fs=7):
    if head:
        arrow(ax, [(x, y), (x + 0.4, y)], ls=ls, color=color, lw=lw, ms=7)
    else:
        line(ax, [(x, y), (x + 0.4, y)], ls=ls, color=color, lw=lw)
    text(ax, x + 0.48, y, label, fs=fs, ha="left")


# ---------------------------------------------------------------- icons
def switch_icon(ax, cx, cy, w=0.62, h=0.3):
    """Generic multilayer switch: flat box with four crossing arrows."""
    rect(ax, cx - w / 2, cy - h / 2, w, h, fill="#dfe7f2", rounded=True, z=3)
    for dy, d in ((0.06, 1), (-0.06, -1)):
        x0, x1 = (cx - 0.2, cx + 0.2) if d == 1 else (cx + 0.2, cx - 0.2)
        a = FancyArrowPatch((x0, cy + dy), (x1, cy + dy), arrowstyle="-|>",
                            mutation_scale=6, lw=0.8, color="black", zorder=4)
        ax.add_patch(a)


def firewall_icon(ax, cx, cy, w=0.62, h=0.36):
    x0, y0 = cx - w / 2, cy - h / 2
    rect(ax, x0, y0, w, h, fill="#f4e3d7", z=3)
    rows = 3
    for i in range(1, rows):
        line(ax, [(x0, y0 + i * h / rows), (x0 + w, y0 + i * h / rows)], lw=0.6, z=4)
    for i in range(rows):
        off = 0 if i % 2 == 0 else w / 6
        xs = np.arange(x0 + w / 3 - off, x0 + w, w / 3)
        for x in xs:
            if x0 < x < x0 + w:
                line(ax, [(x, y0 + i * h / rows), (x, y0 + (i + 1) * h / rows)], lw=0.6, z=4)


def server_icon(ax, cx, cy, w=0.3, h=0.42):
    x0, y0 = cx - w / 2, cy - h / 2
    rect(ax, x0, y0, w, h, fill="#ececec", z=3)
    for i in range(3):
        yy = y0 + h - (i + 1) * h / 4
        line(ax, [(x0 + 0.04, yy), (x0 + w - 0.04, yy)], lw=0.6, z=4)
        ax.add_patch(Circle((x0 + w - 0.07, yy + h / 8), 0.012, fc="black", zorder=4))


def pc_icon(ax, cx, cy):
    rect(ax, cx - 0.2, cy - 0.06, 0.4, 0.27, fill="#ececec", z=3)
    rect(ax, cx - 0.16, cy - 0.02, 0.32, 0.19, fill="white", z=4, lw=0.6)
    line(ax, [(cx, cy - 0.06), (cx, cy - 0.13)], z=3)
    line(ax, [(cx - 0.12, cy - 0.13), (cx + 0.12, cy - 0.13)], z=3)


def cloud_icon(ax, cx, cy, s=1.0):
    for dx, dy, r in ((-0.22, 0, 0.15), (0, 0.07, 0.19), (0.22, 0, 0.15), (0, -0.06, 0.15)):
        ax.add_patch(Circle((cx + dx * s, cy + dy * s), r * s, fc="white", ec="black", lw=LW, zorder=2))
    for dx, dy, r in ((-0.22, 0, 0.15), (0, 0.07, 0.19), (0.22, 0, 0.15), (0, -0.06, 0.15)):
        ax.add_patch(Circle((cx + dx * s, cy + dy * s), r * s - 0.012, fc="white", ec="none", zorder=3))


# ======================================================================
# Figure 4.8  Network topology as built in containerlab
# ======================================================================
def fig4_8():
    W, H = 6.5, 6.4
    fig, ax = canvas(W, H)

    # internet
    cloud_icon(ax, 3.25, 6.08, 1.0)
    text(ax, 3.25, 6.08, "Internet", fs=8, z=6)
    text(ax, 3.95, 6.05, "reached through the host's\nDocker bridge (NAT)", fs=6.5, ha="left", italic=True)

    # edge + DMZ
    firewall_icon(ax, 3.25, 5.1)
    line(ax, [(3.25, 5.28), (3.25, 5.86)])
    text(ax, 3.3, 5.42, "eth0", fs=6.5, ha="left")
    text(ax, 2.88, 5.1, "edge\nLinux, iptables\nfirewall + NAT", fs=7.5, ha="right")
    server_icon(ax, 5.6, 5.1)
    line(ax, [(3.56, 5.1), (5.45, 5.1)])
    text(ax, 3.62, 5.14, "eth2  10.10.40.1/24", fs=6.5, ha="left", va="bottom")
    text(ax, 5.41, 5.14, "eth1", fs=6.5, ha="right", va="bottom")
    text(ax, 5.6, 4.83, "web\n10.10.40.10/24", fs=7.5, va="top")
    rect(ax, 4.95, 4.38, 1.3, 1.05, fill="none", ls="--", lw=0.7, z=1)
    text(ax, 6.2, 4.42, "DMZ 10.10.40.0/24", fs=6.5, ha="right", va="bottom", italic=True)

    # transit
    line(ax, [(3.25, 4.92), (3.25, 3.9)])
    text(ax, 3.3, 4.85, "eth1  10.10.0.2/30", fs=6.5, ha="left", va="top")
    text(ax, 3.3, 3.98, "Et3  10.10.0.1/30", fs=6.5, ha="left", va="bottom")
    text(ax, 3.17, 4.42, "routed transit\n10.10.0.0/30", fs=6.5, ha="right", italic=True)

    # core
    switch_icon(ax, 3.25, 3.75)
    text(ax, 2.88, 3.75, "core\nArista cEOS 4.36.2F", fs=7.5, ha="right")
    text(ax, 3.62, 3.75, "SVIs: Vlan10/20/30/99 = .1\nZT_POLICY ACL in on Et1", fs=6.5, ha="left")

    # trunk
    line(ax, [(3.25, 3.6), (3.25, 2.75)])
    text(ax, 3.3, 3.53, "Et1", fs=6.5, ha="left", va="top")
    text(ax, 3.3, 2.82, "Et1", fs=6.5, ha="left", va="bottom")
    text(ax, 3.17, 3.18, "802.1Q trunk\nVLANs 10, 20, 30, 99\nnative 999", fs=6.5, ha="right", italic=True)

    # acc1
    switch_icon(ax, 3.25, 2.6, w=1.3)
    text(ax, 3.98, 2.6, "acc1  Arista cEOS 4.36.2F\n802.1X on Et2-Et4\nSPAN Et2-Et4 to Et6", fs=7.5, ha="left")

    hosts = [
        (0.55, "admin-pc", "Et2", "bob\nVLAN 10\n10.10.10.50", "pc"),
        (1.65, "staff-pc", "Et3", "alice\nVLAN 20\n10.10.20.50", "pc"),
        (2.75, "guest-pc", "Et4", "guest1\nVLAN 30\n10.10.30.50", "pc"),
        (4.65, "radius", "Et5", "FreeRADIUS 3.2\nVLAN 10\n10.10.10.5", "srv"),
        (5.85, "siem", "Et6", "collector, model\nVLAN 10\n10.10.10.20", "srv"),
    ]
    top_y = 1.28
    for i, (x, name, port, info, kind) in enumerate(hosts):
        if kind == "pc":
            pc_icon(ax, x, 1.05)
        else:
            server_icon(ax, x, 1.07)
        px = 2.72 + i * 0.265
        line(ax, [(x, top_y), (px, 2.45)])
        # port label placed a little above the host along the line
        t = 0.22
        lx, ly = x + (px - x) * t, top_y + (2.45 - top_y) * t
        text(ax, lx + (0.06 if px >= x else -0.06), ly, port, fs=6.5,
             ha="left" if px >= x else "right", va="center")
        text(ax, x, 0.78, name, fs=7.5, bold=True, va="top")
        text(ax, x, 0.6, info, fs=6.5, va="top")
    text(ax, 0.05, 1.95, "802.1X access ports: the VLAN\ncomes from RADIUS after login;\nVLAN 99 until then", fs=6.5, italic=True, ha="left")
    text(ax, 6.45, 1.95, "Et6 is the SPAN\ndestination", fs=6.5, italic=True, ha="right")
    save(fig, "fig4_8_topology")


# ======================================================================
# Figure 4.7  System architecture
# ======================================================================
def fig4_7():
    W, H = 6.5, 6.5
    fig, ax = canvas(W, H)
    red = "#b00000"

    # network side
    rect(ax, 0.85, 5.9, 1.3, 0.38, "Internet", fs=7.5, rounded=True)
    rect(ax, 0.45, 4.85, 2.1, 0.7, "edge firewall (Linux)\niptables: FORWARD policy DROP\nNAT to the internet", fs=7)
    rect(ax, 2.95, 4.85, 1.2, 0.7, "DMZ web server\n10.10.40.10\nport 80 only", fs=7)
    rect(ax, 0.45, 3.65, 2.1, 0.8, "core switch (Arista cEOS)\ngateways for VLAN 10, 20, 30, 99\ninter-VLAN routing\nZT_POLICY ACL on Et1 (inbound)", fs=7)
    rect(ax, 0.45, 2.45, 2.1, 0.8, "access switch acc1 (Arista cEOS)\n802.1X authenticator, Et2-Et4\nSPAN: Et2-Et4 copied to Et6\nBPDU Guard, native VLAN 999", fs=7)
    rect(ax, 2.95, 2.5, 1.2, 0.7, "FreeRADIUS\n10.10.10.5\nuser to VLAN", fs=7)

    arrow(ax, [(1.5, 5.55), (1.5, 5.9)], head="<|-|>", ms=7)
    arrow(ax, [(2.55, 5.2), (2.95, 5.2)], head="<|-|>", ms=7)
    arrow(ax, [(1.5, 4.45), (1.5, 4.85)], head="<|-|>", ms=7, label="10.10.0.0/30", loff=(0.06, 0), lha="left", lva="center", fs=6.5)
    arrow(ax, [(1.5, 3.25), (1.5, 3.65)], head="<|-|>", ms=7, label="802.1Q trunk", loff=(0.06, 0), lha="left", lva="center", fs=6.5)
    arrow(ax, [(2.55, 2.85), (2.95, 2.85)], ls=":", head="<|-|>", ms=7)
    text(ax, 2.75, 3.3, "RADIUS\nUDP 1812", fs=6.5, va="bottom")

    users = [(1.05, "admin-pc\nbob, VLAN 10"), (2.1, "staff-pc\nalice, VLAN 20"), (3.15, "guest-pc\nguest1, VLAN 30")]
    for i, (x, s) in enumerate(users):
        rect(ax, x - 0.47, 1.65, 0.94, 0.45, s, fs=6.5)
        arrow(ax, [(x, 2.1), (1.05 + i * 0.6, 2.45)], head="<|-|>", ms=6)
    text(ax, 2.1, 1.6, "users log in with 802.1X (wpa_supplicant)", fs=6.5, va="top", italic=True)

    # SIEM pipeline band
    rect(ax, 0.1, 0.1, 4.95, 1.2, fill=BLUE, lw=0.6, z=0)
    text(ax, 0.66, 1.24, "SIEM host 10.10.10.20 (detection and response pipeline)", fs=7, ha="left", va="top", bold=True, z=1)
    boxes = [(0.3, "Collector\ntcpdump + Python\n8 features / 10 s"),
             (1.5, "Isolation Forest\nanomaly score"),
             (2.7, "Classifier\nwhich attack?"),
             (3.9, "Response engine\nblock, quarantine,\ndisable or alert")]
    for x, s in boxes:
        rect(ax, x, 0.25, 1.0, 0.7, s, fs=6.5, rounded=True)
    for (x1, _), (x2, _) in zip(boxes, boxes[1:]):
        arrow(ax, [(x1 + 1.0, 0.6), (x2, 0.6)], ms=7)

    # SPAN
    arrow(ax, [(0.52, 2.45), (0.52, 0.95)], ls="--", ms=7)
    text(ax, 0.42, 1.85, "SPAN copy to Et6", fs=6.5, rotation=90)

    # response paths
    arrow(ax, [(4.6, 0.95), (4.6, 2.85), (4.15, 2.85)], ls="-.", color=red, ms=7)
    arrow(ax, [(4.6, 2.85), (4.6, 4.05), (2.55, 4.05)], ls="-.", color=red, ms=7)
    text(ax, 3.55, 4.1, "block: deny entry for the\nsource IP in ZT_POLICY", fs=6.5, color=red, va="bottom")
    text(ax, 4.68, 2.3, "quarantine:\nuser moved to\nVLAN 99, port\nbounced on acc1", fs=6.5, color=red, ha="left")

    # Zabbix
    rect(ax, 5.3, 0.15, 1.15, 1.1, "Zabbix 7.0\n(on the host)\nhealth and threat\ndashboards", fs=6.5)
    arrow(ax, [(5.05, 0.7), (5.3, 0.7)], ls="--", ms=6)

    # policy summary
    rect(ax, 4.5, 5.12, 1.95, 1.18, fill=GREY, lw=0.6)
    text(ax, 4.58, 6.24, "Main policy rules", fs=7, bold=True, ha="left", va="top")
    text(ax, 4.58, 6.02,
         "guest: no access to admin,\n  staff or quarantine subnets\n"
         "quarantine: RADIUS (1812)\n  and SIEM only\n"
         "DMZ: cannot open\n  connections inward\n"
         "inside to DMZ: TCP 80 only", fs=6.5, ha="left", va="top")

    # legend
    y0 = 3.95
    text(ax, 4.95, y0 + 0.14, "Legend", fs=6.5, bold=True, ha="left")
    for i, (ls, lab, col) in enumerate([("-", "user traffic", "black"), ("--", "copied traffic / metrics", "black"),
                                         (":", "authentication", "black"), ("-.", "automated response", red)]):
        legend_row(ax, 4.95, y0 - 0.15 * i - 0.05, ls, lab, color=col, fs=6.0)
    save(fig, "fig4_7_architecture")


# ======================================================================
# Figure 2.1  Conceptual framework
# ======================================================================
def bullet_box(ax, x, y, w, h, title, items, fs=7.5, fill="white", ls="-"):
    rect(ax, x, y, w, h, fill=fill, ls=ls)
    text(ax, x + 0.1, y + h - 0.09, title, fs=fs + 0.5, bold=True, ha="left", va="top")
    body = "\n".join("• " + s for s in items)
    text(ax, x + 0.12, y + h - 0.3, body, fs=fs, ha="left", va="top")


def var_box(ax, x, top, w, title, items, head_fill, body_fill="white", ls="-", fs=7.6, head_fs=8.2, head_color="white"):
    """Box with a coloured title band and a bulleted body. Returns (y_bottom, height)."""
    hh = 0.27
    bh = 0.14 + 0.155 * len(items)
    h = hh + bh
    y = top - h
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.05",
                                fc=body_fill, ec="black", lw=LW, ls=ls, zorder=2))
    ax.add_patch(FancyBboxPatch((x, top - hh), w, hh, boxstyle="round,pad=0,rounding_size=0.05",
                                fc=head_fill, ec="black", lw=LW, ls=ls, zorder=3))
    ax.add_patch(Rectangle((x + 0.01, top - hh), w - 0.02, 0.06, fc=head_fill, ec="none", zorder=3))
    line(ax, [(x, top - hh), (x + w, top - hh)], ls=ls, z=4)
    text(ax, x + w / 2, top - hh / 2, title, fs=head_fs, bold=True, color=head_color, z=5)
    for i, s in enumerate(items):
        text(ax, x + 0.13, top - hh - 0.1 - 0.155 * (i + 0.5), "•  " + s, fs=fs, ha="left", z=5)
    return y, h


def fig2_1():
    W, H = 6.5, 4.05
    fig, ax = canvas(W, H)
    navy, green = "#1f3864", "#385723"
    ivx, ivw = 0.05, 2.95
    text(ax, ivx + ivw / 2, 3.92, "INDEPENDENT VARIABLES", fs=8.5, bold=True)
    text(ax, 5.35, 3.92, "DEPENDENT VARIABLE", fs=8.5, bold=True)
    ivs = [
        ("Zero Trust Access Control", ["802.1X login checked by FreeRADIUS", "VLAN assigned from the user's identity",
                                       "ZT_POLICY ACL between segments", "Edge firewall and DMZ"]),
        ("Anomaly Detection", ["Traffic mirrored to the SIEM (SPAN)", "Eight features per host every 10 s",
                               "Isolation Forest score + failed-login rule"]),
        ("Automated Response", ["Block the source IP (DoS)", "Quarantine to VLAN 99 (scan, brute force)",
                                "Disable the account (insider)", "Alert only (off-hours)"]),
    ]
    top = 3.75
    mids = []
    for t, items in ivs:
        y, h = var_box(ax, ivx, top, ivw, t, items, navy)
        mids.append(y + h / 2)
        top = y - 0.2
    bus = 3.3
    for m in mids:
        line(ax, [(ivx + ivw, m), (bus, m)])
    line(ax, [(bus, mids[0]), (bus, mids[-1])])
    mid = (mids[0] + mids[-1]) / 2
    dvx, dvw = 4.25, 2.2
    items = ["Share of attacks detected", "False alarms on normal users", "Time from detection to action",
             "Spread from a compromised host"]
    dv_h = 0.27 + 0.14 + 0.155 * len(items)
    var_box(ax, dvx, mid + dv_h / 2, dvw, "Network Security", items, green)
    text(ax, dvx + 0.1, mid - dv_h / 2 - 0.02, "measured by the four indicators above", fs=6.5, italic=True, ha="left", va="top")
    arrow(ax, [(bus, mid), (dvx, mid)], ms=12, lw=1.3)
    # moderating variables act on the relationship
    my, mh = var_box(ax, dvx, 1.05, dvw, "Moderating Variables",
                     ["Quality of the training traffic", "Anomaly score threshold", "Lab resources (8 GB RAM)"],
                     GREY2, body_fill="#fafafa", ls="--", head_color="black")
    mx = (bus + dvx) / 2
    arrow(ax, [(dvx, my + mh / 2), (mx, my + mh / 2), (mx, mid - 0.02)], ls="--", ms=9)
    save(fig, "fig2_1_conceptual_framework")


# ======================================================================
# Figure 2.2  How Isolation Forest isolates points
# ======================================================================
def _isolate(points, target, rng, lo, hi, max_depth=30):
    """Random axis-parallel splits until target is alone. Returns the list of splits."""
    pts = points
    lo, hi = lo.copy(), hi.copy()
    splits = []
    while len(pts) > 1 and len(splits) < max_depth:
        d = rng.integers(0, 2)
        a, b = pts[:, d].min(), pts[:, d].max()
        if a == b:
            continue
        s = rng.uniform(a, b)
        splits.append((d, s, lo.copy(), hi.copy()))
        if target[d] < s:
            pts = pts[pts[:, d] < s]
            hi[d] = s
        else:
            pts = pts[pts[:, d] >= s]
            lo[d] = s
    return splits


def fig2_2():
    data_rng = np.random.default_rng(7)
    normal = data_rng.normal(0.0, 1.0, size=(70, 2))
    inlier = np.array([0.15, -0.1])
    outlier = np.array([3.6, 3.1])
    pts = np.vstack([normal, inlier, outlier])
    lo, hi = np.array([-4.0, -4.0]), np.array([4.5, 4.5])
    # pick the run that shows the typical case (many splits vs few)
    best = None
    for seed in range(200):
        a = _isolate(pts, inlier, np.random.default_rng(seed), lo, hi)
        b = _isolate(pts, outlier, np.random.default_rng(seed + 1000), lo, hi)
        if 7 <= len(a) <= 10 and len(b) <= 3:
            best = (a, b)
            break
    fig, axs = plt.subplots(1, 2, figsize=(6.3, 3.0))
    for ax, splits, target, title in ((axs[0], best[0], inlier, "(a) normal session"),
                                      (axs[1], best[1], outlier, "(b) anomalous session")):
        ax.scatter(normal[:, 0], normal[:, 1], s=7, c="#7f7f7f", zorder=2)
        ax.scatter([target[0]], [target[1]], s=40, c="#b00000", marker="o", zorder=6, edgecolors="black", linewidths=0.6)
        if target is not inlier:
            ax.scatter([inlier[0]], [inlier[1]], s=7, c="#7f7f7f", zorder=2)
        else:
            ax.scatter([outlier[0]], [outlier[1]], s=7, c="#7f7f7f", zorder=2)
        for d, s, l, h in splits:
            if d == 0:
                ax.plot([s, s], [l[1], h[1]], color="black", lw=0.8, zorder=3)
            else:
                ax.plot([l[0], h[0]], [s, s], color="black", lw=0.8, zorder=3)
        ax.set_xlim(lo[0], hi[0])
        ax.set_ylim(lo[1], hi[1])
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel("requests per minute (scaled)", fontsize=7.5)
        ax.set_ylabel("unique destination ports (scaled)", fontsize=7.5)
        ax.set_title(f"{title}: isolated after {len(splits)} splits", fontsize=8)
        for sp in ax.spines.values():
            sp.set_linewidth(0.8)
    fig.tight_layout(w_pad=1.5)
    save(fig, "fig2_2_isolation_forest")


# ======================================================================
# Figure 3.1  Prototyping methodology
# ======================================================================
def fig3_1():
    W, H = 6.5, 6.1
    fig, ax = canvas(W, H)
    # main flow
    rect(ax, 0.25, 5.35, 3.35, 0.55, "1. Requirements gathering and analysis\n(literature review, supervisor feedback)", fs=7.5, rounded=True)
    rect(ax, 0.25, 4.5, 3.35, 0.55, "2. Quick design\n(topology, VLAN plan, features, response rules)", fs=7.5, rounded=True)
    arrow(ax, [(1.92, 5.35), (1.92, 5.05)], ms=8)

    rect(ax, 0.1, 1.9, 3.65, 2.3, fill=GREY, ls="--", lw=0.7, z=0, rounded=True)
    text(ax, 1.12, 4.13, "3. Prototype cycle (repeated for each prototype)", fs=7, italic=True, ha="left", va="top", z=1)
    rect(ax, 0.25, 3.15, 1.5, 0.6, "Build or extend\nthe prototype", fs=7.5, rounded=True)
    rect(ax, 2.1, 3.15, 1.5, 0.6, "Test in the lab\n(self-tests, attacks)", fs=7.5, rounded=True)
    diamond(ax, 2.85, 2.45, 1.35, 0.6, "Requirements\nmet?", fs=7)
    rect(ax, 0.25, 2.15, 1.5, 0.6, "Review results and\nrefine the design", fs=7.5, rounded=True)
    arrow(ax, [(1.0, 4.5), (1.0, 3.75)], ms=8)
    arrow(ax, [(1.75, 3.45), (2.1, 3.45)], ms=8)
    arrow(ax, [(2.85, 3.15), (2.85, 2.75)], ms=8)
    arrow(ax, [(2.175, 2.45), (1.75, 2.45)], ms=8, label="No", loff=(0, 0.04), fs=7)
    arrow(ax, [(1.0, 2.75), (1.0, 3.15)], ms=8)

    rect(ax, 2.1, 1.0, 1.5, 0.55, "4. Final validation\nagainst objectives", fs=7.5, rounded=True)
    arrow(ax, [(2.85, 2.15), (2.85, 1.55)], ms=8, label="Yes", lpos=0.75, loff=(0.06, 0), lha="left", lva="center", fs=7)
    rect(ax, 2.1, 0.15, 1.5, 0.55, "5. Report and\ndemonstration", fs=7.5, rounded=True)
    arrow(ax, [(2.85, 1.0), (2.85, 0.7)], ms=8)

    # what each prototype was
    rect(ax, 3.95, 0.15, 2.5, 5.75, fill="white", lw=0.6, z=0)
    text(ax, 5.2, 5.8, "Prototypes in this project", fs=8, bold=True, va="top")
    protos = [
        (4.35, "Prototype 1: 802.1X proof of concept",
         "one cEOS switch, FreeRADIUS and one\nclient; right password gave VLAN 20,\nwrong password left the port blocked",
         "refined: use_tunneled_reply enabled\nso RADIUS returns the VLAN"),
        (2.55, "Prototype 2: full Zero Trust lab",
         "core and acc1 switches, edge firewall,\nDMZ web server, SIEM, Zabbix and a\none-command rebuild (lab-up.sh)",
         "refined: ACL moved from SVIs to core\nEt1; MTU 1500 on all Linux nodes"),
        (0.75, "Prototype 3: detection and response",
         "collector, traffic generator, Isolation\nForest model and response engine",
         "refined: header-only capture to save\nRAM; strict labelling of windows"),
    ]
    for y, title, body, note in protos:
        rect(ax, 4.08, y, 2.25, 1.2, fill="#f7f7f7", rounded=True)
        text(ax, 4.16, y + 1.12, title, fs=7, bold=True, ha="left", va="top")
        text(ax, 4.16, y + 0.92, body, fs=6.5, ha="left", va="top")
        text(ax, 4.16, y + 0.4, note, fs=6.5, ha="left", va="top", italic=True)
    for (y1, *_), (y2, *_) in zip(protos, protos[1:]):
        arrow(ax, [(5.2, y1), (5.2, y2 + 1.2)], ms=8)
    save(fig, "fig3_1_methodology")


# ======================================================================
# Figure 4.1  Black-box view
# ======================================================================
def fig4_1():
    W, H = 6.5, 4.5
    fig, ax = canvas(W, H)
    rect(ax, 2.2, 1.75, 1.6, 1.0, "Zero Trust network\nwith automated\nthreat detection\nand response", fs=8, bold=True, fill=GREY)
    rect(ax, 0.05, 3.55, 1.35, 0.6, "Network users\n(admin, staff, guest)", fs=7.5)
    rect(ax, 0.05, 0.35, 1.35, 0.6, "Attacker\n(simulated)", fs=7.5)
    rect(ax, 5.1, 1.95, 1.35, 0.6, "Network\nadministrator", fs=7.5)

    # users
    arrow(ax, [(1.4, 3.95), (2.6, 3.95), (2.6, 2.75)], ms=8)
    text(ax, 1.48, 4.0, "802.1X credentials, normal traffic\n(web pages, downloads, ping)", fs=6.5, ha="left", va="bottom")
    arrow(ax, [(2.95, 2.75), (2.95, 3.7), (1.4, 3.7)], ms=8)
    text(ax, 1.48, 3.65, "VLAN access for their\nrole, or rejection", fs=6.5, ha="left", va="top")
    # attacker
    arrow(ax, [(1.4, 0.55), (2.6, 0.55), (2.6, 1.75)], ms=8)
    text(ax, 1.48, 0.5, "DoS flood, port scan, brute force,\ninsider download, off-hours use", fs=6.5, ha="left", va="top")
    arrow(ax, [(2.95, 1.75), (2.95, 0.8), (1.4, 0.8)], ms=8)
    text(ax, 1.48, 0.85, "source IP blocked, host moved\nto VLAN 99, or account disabled", fs=6.5, ha="left", va="bottom")
    # admin
    arrow(ax, [(5.1, 2.4), (3.8, 2.4)], ms=8)
    text(ax, 4.45, 2.45, "user accounts, VLAN\npolicy, training run,\nrelease of a host", fs=6.5, va="bottom")
    arrow(ax, [(3.8, 2.1), (5.1, 2.1)], ms=8)
    text(ax, 4.45, 2.05, "alerts, anomaly scores,\nactions and timing\n(Zabbix, incident log)", fs=6.5, va="top")
    save(fig, "fig4_1_blackbox")


# ======================================================================
# Figure 4.2  Use-case diagram
# ======================================================================
def ell_edge(cx, cy, w, h, tx, ty):
    """Point on an ellipse boundary in the direction of (tx, ty)."""
    dx, dy = tx - cx, ty - cy
    t = 1.0 / np.sqrt((dx / (w / 2)) ** 2 + (dy / (h / 2)) ** 2)
    return cx + dx * t, cy + dy * t


def fig4_2():
    W, H = 6.5, 6.4
    fig, ax = canvas(W, H)
    rect(ax, 0.8, 0.85, 4.95, 5.45, fill="white", lw=LW, z=0)
    text(ax, 3.27, 6.18, "Zero Trust Detection and Response System", fs=8.5, bold=True, va="top")
    EW, EH = 1.45, 0.55
    L, C, R = 1.62, 3.27, 4.92
    rows = {1: 5.5, 2: 4.7, 3: 3.9, 4: 3.1, 5: 2.3, 6: 1.4}
    uc = {
        "login": (L, 1, "Log in with 802.1X"),
        "access": (L, 2, "Access resources\nallowed for role"),
        "extract": (L, 3, "Extract session\nfeatures"),
        "attack": (L, 4, "Generate attack\ntraffic"),
        "block": (L, 6, "Block source IP"),
        "monitor": (C, 2, "Monitor network\ntraffic"),
        "score": (C, 3, "Score session with\nIsolation Forest"),
        "respond": (C, 4, "Respond to\nanomaly"),
        "quar": (C, 6, "Quarantine host\n(VLAN 99)"),
        "manage": (R, 1, "Manage users and\nVLAN policy"),
        "view": (R, 3, "View alerts\nand scores"),
        "release": (R, 4, "Release or re-enable\na host"),
        "disable": (L, 5, "Disable account"),
        "alert": (R, 5, "Raise alert"),
        "train": (R, 6, "Train Isolation\nForest model"),
    }
    P = {}
    for k, (x, r, s) in uc.items():
        ellipse(ax, x, rows[r], EW, EH, s, fs=7.5)
        P[k] = (x, rows[r])

    def edge(a, toward):
        return ell_edge(*P[a], EW, EH, *toward)

    def rel(a, b, kind, label=None, loff=(0.05, 0), lha="left"):
        pa, pb = edge(a, P[b]), edge(b, P[a])
        if kind == "include":
            arrow(ax, [pa, pb], ls="--", head="->", ms=9)
        elif kind == "gen":
            arrow(ax, [pa, pb], head="-|>", ms=13, fc="white")
        if label:
            mx, my = (pa[0] + pb[0]) / 2 + loff[0], (pa[1] + pb[1]) / 2 + loff[1]
            text(ax, mx, my, label, fs=6.5, ha=lha, va="center", z=6,
                 bbox=dict(fc="white", ec="none", pad=0.3))

    rel("access", "login", "include", "«include»")
    rel("monitor", "score", "include", "«include»")
    rel("score", "extract", "include", None)
    text(ax, (L + C) / 2, rows[3] + 0.27, "«include»", fs=6.5, z=6)
    rel("respond", "score", "include", None)
    # respond extends score: dashed arrow from respond to score with <<extend>>
    text(ax, 3.32, 3.5, "«extend»", fs=6.5, ha="left", va="center", z=6, bbox=dict(fc="white", ec="none", pad=0.3))
    rel("block", "respond", "gen")
    rel("quar", "respond", "gen")
    rel("alert", "respond", "gen")
    rel("disable", "respond", "gen")

    # actors
    actor(ax, 0.38, 5.5, "Network user\n(admin, staff,\nguest)", fs=7)
    actor(ax, 0.38, 3.45, "Attacker\n(simulated)", fs=7)
    actor(ax, 6.15, 4.55, "Network\nadministrator", fs=7)
    ua, aa, ma = (0.58, 5.1), (0.58, 3.05), (5.95, 4.15)

    def assoc(pt, k):
        line(ax, [pt, edge(k, pt)], z=1)

    # notation key, for readers new to UML
    kx, ky = 0.85, 0.55
    text(ax, kx, ky, "Notation:", fs=6.5, bold=True, ha="left")
    arrow(ax, [(kx + 0.55, ky), (kx + 0.95, ky)], ls="--", head="->", ms=8)
    text(ax, kx + 1.0, ky, "\u00abinclude\u00bb always happens as part of the other use case", fs=6.5, ha="left")
    arrow(ax, [(kx + 0.55, ky - 0.17), (kx + 0.95, ky - 0.17)], ls="--", head="->", ms=8)
    text(ax, kx + 1.0, ky - 0.17, "\u00abextend\u00bb happens only when a condition is met (score above threshold)", fs=6.5, ha="left")
    arrow(ax, [(kx + 0.55, ky - 0.34), (kx + 0.95, ky - 0.34)], head="-|>", ms=11, fc="white")
    text(ax, kx + 1.0, ky - 0.34, "is a kind of (generalization)", fs=6.5, ha="left")

    assoc(ua, "login")
    assoc(ua, "access")
    assoc(aa, "attack")
    for k in ("manage", "monitor", "view", "release", "train"):
        assoc(ma, k)
    save(fig, "fig4_2_usecase")


# ======================================================================
# Figure 4.3  Sequence diagram (one anomalous window)
# ======================================================================
def fig4_3():
    W, H = 6.5, 9.0
    fig, ax = canvas(W, H)
    names = ["guest-pc\n(attacker)", "acc1\naccess switch", "SIEM\ncollector", "Isolation\nForest",
             "Response\nengine", "core\nswitch", "Free-\nRADIUS", "Zabbix"]
    X = [0.42 + i * 0.808 for i in range(len(names))]
    top, bottom = 8.9, 0.3
    for x, n in zip(X, names):
        rect(ax, x - 0.37, top - 0.44, 0.74, 0.44, n, fs=7, fill=GREY)
        line(ax, [(x, top - 0.44), (x, bottom)], ls=(0, (4, 3)), lw=0.6, z=0)
    A, S, COL, M, RE, CORE, RAD, ZBX = range(8)

    def act(i, y1, y2):
        rect(ax, X[i] - 0.05, y2, 0.1, y1 - y2, fill="white", z=3, lw=0.7)

    def msg(i, j, y, s, ret=False, ha="center"):
        xi = X[i] + (0.05 if j > i else -0.05)
        xj = X[j] + (-0.05 if j > i else 0.05)
        arrow(ax, [(xi, y), (xj, y)], ls="--" if ret else "-", head="->" if ret else "-|>", ms=8, z=4)
        mx = (xi + xj) / 2 if ha == "center" else (xi + (0.08 if j > i else -0.08))
        text(ax, mx, y + 0.035, s, fs=6.5, ha=ha if ha == "center" else ("left" if j > i else "right"),
             va="bottom", z=6, bbox=dict(fc="white", ec="none", pad=0.2))

    def self_msg(i, y, s, h=0.2):
        x = X[i] + 0.05
        line(ax, [(x, y), (x + 0.22, y), (x + 0.22, y - h)], z=4)
        arrow(ax, [(x + 0.22, y - h), (x, y - h)], ms=7, z=4)
        text(ax, x + 0.27, y - h / 2, s, fs=6.5, ha="left", va="center", z=6,
             bbox=dict(fc="white", ec="none", pad=0.2))

    def frame(x1, x2, y1, y2, tag, guards):
        rect(ax, x1, y2, x2 - x1, y1 - y2, fill="none", lw=0.7, z=2)
        pw = 0.07 * len(tag) + 0.12
        ax.add_patch(Polygon([(x1, y1), (x1 + pw, y1), (x1 + pw, y1 - 0.12), (x1 + pw - 0.06, y1 - 0.18), (x1, y1 - 0.18)],
                             closed=True, fc="white", ec="black", lw=0.7, zorder=5))
        text(ax, x1 + 0.05, y1 - 0.09, tag, fs=6.5, bold=True, ha="left", z=6)
        for gy, g, sep in guards:
            if sep:
                line(ax, [(x1, gy), (x2, gy)], ls=(0, (5, 3)), lw=0.7, z=2)
            text(ax, x1 + (pw + 0.05 if not sep else 0.05), gy - 0.1, g, fs=6.5, ha="left", va="center", z=6,
                 bbox=dict(fc="white", ec="none", pad=0.2))

    y = 8.2
    msg(A, S, y, "1: attack packets (HTTP flood)")
    act(S, y, y - 0.35)
    msg(S, COL, y - 0.3, "2: mirrored copy (SPAN to Et6)")
    act(COL, y - 0.3, 5.6)
    self_msg(COL, 7.6, "3: close 10 s window, extract\n    8 features per host", h=0.25)
    msg(COL, M, 7.05, "4: score(features)")
    act(M, 7.05, 6.75)
    msg(M, COL, 6.75, "5: anomaly score", ret=True)
    msg(COL, ZBX, 6.45, "6: push score (every window)")

    frame(0.08, 6.48, 6.2, 0.5, "alt", [(6.2, "[score above threshold, or 5 or more failed logins]", False)])
    msg(COL, RE, 5.75, "7: anomaly(host, features, reason)")
    act(RE, 5.75, 0.7)
    self_msg(RE, 5.5, "8: classify attack type", h=0.2)

    frame(0.16, 6.4, 5.1, 1.55, "alt",
          [(5.1, "[DoS]", False), (4.3, "[port scan, brute force or insider]", True), (2.3, "[off-hours or unclassified]", True)])
    msg(RE, CORE, 4.75, "9: add deny line (seq. 71-79)")
    act(CORE, 4.75, 4.5)
    msg(CORE, RE, 4.5, "10: config saved", ret=True)
    msg(RE, RAD, 3.9, "11: rule: VLAN 99, or reject")
    msg(RE, S, 3.55, "12: bounce the user's port")
    act(S, 3.55, 2.75)
    msg(S, RAD, 3.25, "13: Access-Request (re-login)")
    act(RAD, 3.25, 2.95)
    msg(RAD, S, 2.95, "14: Accept with VLAN 99, or Reject", ret=True)
    msg(RE, A, 2.6, "15: re-address PC to 10.10.99.x (quarantine)")
    self_msg(RE, 2.0, "16: alert only, no change", h=0.2)

    msg(RE, ZBX, 1.25, "17: alert, action, response time")
    self_msg(RE, 0.98, "18: write incident record", h=0.18)
    save(fig, "fig4_3_sequence")


# ======================================================================
# Figure 4.4  Activity diagram (one pass of the pipeline loop)
# ======================================================================
def fig4_4():
    W, H = 6.5, 8.9
    fig, ax = canvas(W, H)
    cx = 3.1

    def act_box(x, y, s, w=2.0, h=0.44):
        rect(ax, x - w / 2, y - h / 2, w, h, s, fs=7.5, rounded=True)

    def bar(x, y, w):
        ax.add_patch(Rectangle((x - w / 2, y - 0.03), w, 0.06, fc="black", zorder=3))

    ax.add_patch(Circle((cx, 8.7), 0.09, fc="black", zorder=3))
    diamond(ax, cx, 8.3, 0.3, 0.22)
    arrow(ax, [(cx, 8.61), (cx, 8.41)], ms=8)
    arrow(ax, [(cx, 8.19), (cx, 7.98)], ms=8)
    bar(cx, 7.95, 3.4)
    act_box(1.95, 7.45, "Capture mirrored packets\nfor 10 s (tcpdump on SIEM)", w=2.1)
    act_box(4.25, 7.45, "Read new Access-Reject\nlines from FreeRADIUS", w=2.1)
    arrow(ax, [(1.95, 7.92), (1.95, 7.67)], ms=8)
    arrow(ax, [(4.25, 7.92), (4.25, 7.67)], ms=8)
    bar(cx, 6.95, 3.4)
    arrow(ax, [(1.95, 7.23), (1.95, 6.98)], ms=8)
    arrow(ax, [(4.25, 7.23), (4.25, 6.98)], ms=8)

    steps = [(6.45, "Group packets by host and\ncompute the eight features"),
             (5.8, "Scale the features and get the\nIsolation Forest anomaly score"),
             (5.15, "Push the score to Zabbix")]
    prev = 6.92
    for y, s in steps:
        arrow(ax, [(cx, prev), (cx, y + 0.22)], ms=8)
        act_box(cx, y, s, w=2.4)
        prev = y - 0.22
    diamond(ax, cx, 4.4, 2.0, 0.7, "score above threshold,\nor 5+ failed logins?", fs=6.8)
    arrow(ax, [(cx, prev), (cx, 4.75)], ms=8)
    # no -> back to the merge node
    arrow(ax, [(cx - 1.0, 4.4), (0.25, 4.4), (0.25, 8.3), (cx - 0.15, 8.3)], ms=8)
    text(ax, cx - 1.05, 4.45, "[no]", fs=7, ha="right", va="bottom")
    text(ax, 0.32, 6.4, "next\nwindow", fs=6.5, ha="left", italic=True)

    act_box(cx, 3.62, "Classify the attack type\nfrom the features", w=2.4)
    arrow(ax, [(cx, 4.05), (cx, 3.84)], ms=8)
    text(ax, cx + 0.06, 3.95, "[yes]", fs=7, ha="left", va="center")
    diamond(ax, cx, 2.98, 1.3, 0.48, "attack type?", fs=7)
    arrow(ax, [(cx, 3.4), (cx, 3.22)], ms=8)

    xs = [0.9, 2.4, 3.9, 5.4]
    bx = [("Add a deny line for\nthe source IP\non core", "[DoS]"),
          ("Move the user to\nVLAN 99 and\nbounce the port", "[port scan or\nbrute force]"),
          ("Reject the user's\nlogin (disable)\nand bounce the port", "[insider]"),
          ("Alert only;\naccess not\nchanged", "[off-hours or\nunclassified]")]
    line(ax, [(cx, 2.74), (cx, 2.6)])
    line(ax, [(xs[0], 2.6), (xs[-1], 2.6)])
    for x, (s, g) in zip(xs, bx):
        arrow(ax, [(x, 2.6), (x, 2.22)], ms=8)
        text(ax, x + 0.05, 2.43, g, fs=6, ha="left", va="center")
        act_box(x, 1.95, s, w=1.38, h=0.54)
    for x in xs:
        line(ax, [(x, 1.68), (x, 1.52)])
    line(ax, [(xs[0], 1.52), (xs[-1], 1.52)])
    diamond(ax, cx, 1.33, 0.3, 0.22)
    arrow(ax, [(cx, 1.52), (cx, 1.44)], ms=7)
    act_box(cx, 0.85, "Write the incident record, send the alert\nand action to Zabbix, log the response time", w=3.2, h=0.46)
    arrow(ax, [(cx, 1.22), (cx, 1.08)], ms=8)
    diamond(ax, cx, 0.25, 1.2, 0.36, "stop requested?", fs=6.5)
    arrow(ax, [(cx, 0.62), (cx, 0.43)], ms=8)
    arrow(ax, [(cx + 0.6, 0.25), (6.4, 0.25), (6.4, 8.3), (cx + 0.15, 8.3)], ms=8)
    text(ax, cx + 0.66, 0.3, "[no]", fs=7, ha="left", va="bottom")
    # end node
    arrow(ax, [(cx - 0.6, 0.25), (1.25, 0.25)], ms=8)
    text(ax, cx - 0.66, 0.3, "[yes]", fs=7, ha="right", va="bottom")
    ax.add_patch(Circle((1.15, 0.25), 0.1, fc="white", ec="black", lw=LW, zorder=3))
    ax.add_patch(Circle((1.15, 0.25), 0.06, fc="black", zorder=4))
    save(fig, "fig4_4_activity")


# ======================================================================
# Figure 4.5  Entity relationship diagram (crow's foot)
# ======================================================================
ROW = 0.165
HEAD = 0.24


def entity(ax, x, top, w, name, attrs):
    h = HEAD + ROW * len(attrs) + 0.06
    rect(ax, x, top - h, w, h, fill="white")
    rect(ax, x, top - HEAD, w, HEAD, name, fs=7.5, bold=True, fill=GREY2)
    for i, (key, a) in enumerate(attrs):
        y = top - HEAD - 0.03 - ROW * (i + 0.5)
        text(ax, x + 0.08, y, key, fs=6.5, ha="left", bold=True)
        text(ax, x + 0.36, y, a, fs=6.5, ha="left", italic=(key == "FK"))
    return (x, top - h, w, h)


def crow_end(ax, p, d, card):
    """Draw a crow's-foot end at point p (on the entity), d = unit vector away from the entity."""
    p, d = np.array(p, float), np.array(d, float)
    n = np.array([-d[1], d[0]])

    def bar(t):
        c = p + d * t
        line(ax, [c + n * 0.06, c - n * 0.06], z=4)

    def circ(t):
        c = p + d * t
        ax.add_patch(Circle(c, 0.035, fc="white", ec="black", lw=0.8, zorder=5))

    def crow():
        tip = p + d * 0.14
        for s in (-1, 0, 1):
            line(ax, [tip, p + n * 0.07 * s], z=4)

    if card == "1":        # exactly one
        bar(0.08); bar(0.15)
    elif card == "0..1":
        bar(0.08); circ(0.2)
    elif card == "1..*":
        crow(); bar(0.2)
    elif card == "0..*":
        crow(); circ(0.22)


def relation(ax, pts, c_start, c_end, label=None, lpos=None, lha="center", lva="bottom"):
    line(ax, pts, z=3)
    d0 = np.array(pts[0]) - np.array(pts[1]); d0 /= np.linalg.norm(d0)
    d1 = np.array(pts[-1]) - np.array(pts[-2]); d1 /= np.linalg.norm(d1)
    crow_end(ax, pts[0], -d0, c_start)
    crow_end(ax, pts[-1], -d1, c_end)
    if label:
        text(ax, lpos[0], lpos[1], label, fs=6.5, italic=True, ha=lha, va=lva)


def fig4_5():
    W, H = 6.5, 5.75
    fig, ax = canvas(W, H)
    c1, c2, c3, w = 0.05, 2.4, 4.75, 1.7
    auth = entity(ax, c1, 5.65, w, "AUTH_EVENT", [("PK", "event_id"), ("FK", "username"), ("", "mac_address"),
                                                  ("", "result (accept / reject)"), ("", "received_at")])
    user = entity(ax, c2, 5.65, w, "USER_ACCOUNT", [("PK", "username"), ("", "password"), ("FK", "vlan_id"),
                                                    ("", "status (active / quarantined)")])
    vlan = entity(ax, c3, 5.65, w, "VLAN", [("PK", "vlan_id"), ("", "name"), ("", "subnet"), ("", "gateway")])
    host = entity(ax, c2, 4.1, w, "HOST", [("PK", "host_ip"), ("", "node_name"), ("", "mac_address"),
                                           ("", "switch_port"), ("FK", "username"), ("FK", "vlan_id")])
    sess = entity(ax, c1, 4.1, w, "SESSION_WINDOW", [("PK", "session_id"), ("FK", "host_ip"), ("", "window_start"),
                                                     ("", "packet_count"), ("", "avg_packet_size"), ("", "bytes_transferred"),
                                                     ("", "connection_duration"), ("", "failed_logins"), ("", "unique_dst_ports"),
                                                     ("", "requests_per_min"), ("", "off_hours"), ("", "anomaly_score"), ("", "label")])
    alert = entity(ax, c2, 2.35, w, "ALERT", [("PK", "alert_id"), ("FK", "session_id"), ("", "attack_type"),
                                              ("", "score"), ("", "created_at")])
    act = entity(ax, c3, 2.35, w, "RESPONSE_ACTION", [("PK", "action_id"), ("FK", "alert_id"), ("", "action_type"),
                                                      ("", "target (IP or user)"), ("", "executed_at"), ("", "response_ms"),
                                                      ("", "released_at")])
    y = 5.12
    relation(ax, [(c2, y), (c1 + w, y)], "1", "0..*", "makes", (2.225, y + 0.06))
    relation(ax, [(c3, y), (c2 + w, y)], "1", "0..*", "assigned to", (4.575, y + 0.06))
    ux = c2 + w / 2
    relation(ax, [(ux, user[1]), (ux, 4.1)], "0..1", "0..*", "logs in on", (ux + 0.08, (user[1] + 4.1) / 2), lha="left", lva="center")
    relation(ax, [(c3 + w / 2, vlan[1]), (c3 + w / 2, 3.45), (c2 + w, 3.45)], "1", "0..*", "contains", (c3 + w / 2 + 0.08, 4.0), lha="left", lva="center")
    relation(ax, [(c2, 3.45), (c1 + w, 3.45)], "1", "0..*", "generates", (2.225, 3.51))
    relation(ax, [(c1 + w, 1.9), (c2, 1.9)], "1", "0..1", "raises", (2.225, 1.96))
    relation(ax, [(c2 + w, 1.9), (c3, 1.9)], "1", "1..*", "triggers", (4.575, 1.96))
    # key
    kx, ky = 2.4, 0.75
    text(ax, kx, ky, "Notation (crow's foot):", fs=6.5, bold=True, ha="left")
    for i, (card, s) in enumerate([("1", "exactly one"), ("0..1", "zero or one"), ("0..*", "zero or many"), ("1..*", "one or many")]):
        yy = ky - 0.17 - i * 0.15
        line(ax, [(kx + 0.05, yy), (kx + 0.45, yy)], z=3)
        crow_end(ax, (kx + 0.45, yy), (-1, 0), card)
        text(ax, kx + 0.55, yy, s, fs=6.5, ha="left")
    save(fig, "fig4_5_erd")


# ======================================================================
# Figure 4.6  Class diagram
# ======================================================================
CROW = 0.15


def uml_class(ax, x, top, w, name, attrs, methods, stereo=None):
    nh = 0.24 + (0.13 if stereo else 0)
    ah = CROW * max(len(attrs), 1) + 0.06
    mh = CROW * max(len(methods), 1) + 0.06
    h = nh + ah + mh
    rect(ax, x, top - h, w, h, fill="white")
    rect(ax, x, top - nh, w, nh, fill=GREY2)
    if stereo:
        text(ax, x + w / 2, top - 0.1, stereo, fs=6, italic=True)
        text(ax, x + w / 2, top - 0.25, name, fs=7.5, bold=True)
    else:
        text(ax, x + w / 2, top - nh / 2, name, fs=7.5, bold=True)
    line(ax, [(x, top - nh - ah), (x + w, top - nh - ah)], z=3)
    for i, a in enumerate(attrs):
        text(ax, x + 0.06, top - nh - 0.03 - CROW * (i + 0.5), a, fs=6.3, ha="left")
    for i, m in enumerate(methods):
        text(ax, x + 0.06, top - nh - ah - 0.03 - CROW * (i + 0.5), m, fs=6.3, ha="left")
    return dict(x=x, y=top - h, w=w, h=h, top=top, cx=x + w / 2, cy=top - h / 2)


def composition(ax, whole, part, mult="1", filled=True, label=None):
    """Line from part to whole with a diamond at the whole end."""
    (x1, y1), (x2, y2) = part, whole
    d = np.array([x2 - x1, y2 - y1], float)
    L = np.linalg.norm(d)
    d /= L
    n = np.array([-d[1], d[0]])
    tip = np.array([x2, y2])
    back = tip - d * 0.2
    mid = tip - d * 0.1
    line(ax, [(x1, y1), tuple(back)], z=3)
    ax.add_patch(Polygon([tip, mid + n * 0.055, back, mid - n * 0.055], closed=True,
                         fc="black" if filled else "white", ec="black", lw=0.8, zorder=4))
    if mult:
        p = np.array([x1, y1]) + d * 0.12 + n * 0.08
        text(ax, p[0], p[1], mult, fs=6.5)


def depend(ax, p0, p1, label=None, lpos=0.5, loff=(0.05, 0.05), lha="left"):
    """Dashed dependency arrow (uses / calls) with an open head."""
    arrow(ax, [p0, p1], ls="--", head="->", ms=9)
    if label:
        x = p0[0] + (p1[0] - p0[0]) * lpos + loff[0]
        y = p0[1] + (p1[1] - p0[1]) * lpos + loff[1]
        text(ax, x, y, label, fs=6.0, italic=True, ha=lha, z=6, bbox=dict(fc="white", ec="none", pad=0.2))


def fig4_6():
    W, H = 6.5, 6.75
    fig, ax = canvas(W, H)
    w = 1.95
    c1, c2, c3 = 0.05, 2.28, 4.5
    t1 = 6.7
    col = uml_class(ax, c1, t1, w, "zt_collector", ["WINDOW = 10 s", "FEATURES: 8 names"],
                    ["capture(seconds)", "read_packets(pcap)", "build_rows(packets, rejects)", "collect_batch(seconds)"],
                    stereo="\u00abmodule\u00bb zt_collector.py")
    det = uml_class(ax, c2, t1, w, "AnomalyDetector",
                    ["scaler: StandardScaler", "forest: IsolationForest (200)", "threshold: float"],
                    ["fit(rows)", "score(rows)", "tune(normal_rows, q=0.99)", "predict(rows)", "save() / load()"],
                    stereo="zt_model.py")
    hyb = uml_class(ax, c3, t1, w, "detect()", ["BRUTE_FORCE_RULE = 5"],
                    ["detect(det, rows): flag, reason", "flag = model OR rule"],
                    stereo="\u00abfunction\u00bb zt_model.py")
    t2 = min(col["y"], det["y"], hyb["y"]) - 0.45
    rad = uml_class(ax, c1, t2, w, "RadiusRejectParser", ["user: dict", "mac: dict"],
                    ["feed(line): (mac, user)"], stereo="zt_collector.py")
    orc = uml_class(ax, c2, t2, w, "PipelineOrchestrator", ["detector: AnomalyDetector", "engine: ResponseEngine"],
                    ["features(window)", "push_scores(df)", "handle(row, window_end)", "process(window)", "run()"],
                    stereo="zt_pipeline.py")
    zbx = uml_class(ax, c3, t2, w, "zt_zbx_push", ["port 10051 (sender)"],
                    ["send_score(node, score)", "send_alert(node, text)", "send_action(node, action, ms)"],
                    stereo="\u00abmodule\u00bb zt_zbx_push.py")
    t3 = min(rad["y"], orc["y"], zbx["y"]) - 0.45
    alb = uml_class(ax, c1, t3, w, "AlertBuilder", [],
                    ["classify(row): attack type", "build(host_ip, attack,", "    action, ...): alert"], stereo="zt_respond.py")
    eng = uml_class(ax, c2, t3, w, "ResponseEngine", ["sessions: dict (Netmiko)", "state: dict"],
                    ["block(ip) / unblock(ip)", "quarantine(pc)", "disable(pc) / restore(pc)", "alert_only(ip, attack)",
                     "record(alert, response_ms)", "reset()"], stereo="zt_respond.py")
    nac = uml_class(ax, c3, t3, w, "NetworkActions", [],
                    ["block_ip(ip, seq)", "unblock_ip(seq)", "bounce_port(port)", "radius_rules(rules)", "quarantine_ip(ip)"],
                    stereo="zt_respond.py")

    # ownership (composition): the orchestrator owns the detector and the engine
    composition(ax, (orc["cx"], orc["top"]), (det["cx"], det["y"]))
    composition(ax, (orc["cx"], orc["y"]), (eng["cx"], eng["top"]))
    composition(ax, (col["x"] + 0.4, col["y"]), (col["x"] + 0.4, rad["top"]))
    # uses / calls
    depend(ax, (orc["x"], orc["top"] - 0.15), (col["x"] + w - 0.3, col["y"]), "uses", lpos=0.45, loff=(0.04, 0.02))
    depend(ax, (orc["x"] + w, orc["top"] - 0.15), (hyb["x"] + 0.4, hyb["y"]), "calls", lpos=0.45, loff=(0.04, 0.02))
    depend(ax, (hyb["x"], hyb["cy"]), (det["x"] + w, hyb["cy"]), "uses", lpos=0.5, loff=(0, 0.05), lha="center")
    depend(ax, (orc["x"] + w, orc["cy"]), (zbx["x"], orc["cy"]), "scores", lpos=0.5, loff=(0, 0.05), lha="center")
    depend(ax, (orc["x"], orc["y"] + 0.15), (alb["x"] + w - 0.3, alb["top"]), "classify", lpos=0.5, loff=(-0.05, 0.02), lha="right")
    depend(ax, (eng["x"], eng["cy"]), (alb["x"] + w, eng["cy"]), "builds", lpos=0.5, loff=(0, 0.05), lha="center")
    depend(ax, (eng["x"] + w, eng["cy"]), (nac["x"], eng["cy"]), "uses", lpos=0.5, loff=(0, 0.05), lha="center")
    depend(ax, (eng["x"] + w, eng["top"] - 0.15), (zbx["x"] + 0.4, zbx["y"]), "alerts", lpos=0.5, loff=(0.04, 0.0))
    save(fig, "fig4_6_class")


FIGS = {k: v for k, v in globals().items() if k.startswith("fig") and callable(v)}

if __name__ == "__main__":
    names = sys.argv[1:] or sorted(FIGS)
    for n in names:
        FIGS[n]()
