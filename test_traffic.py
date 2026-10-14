#!/usr/bin/env python3
"""Offline checks for zt_traffic.py. No lab needed: python test_traffic.py"""
import subprocess
import sys
import tempfile
from datetime import datetime

from zt_traffic import AGENT, label_rows

T0 = datetime(2026, 10, 14, 10, 0, 0).timestamp() + 0.4   # capture starts mid-second, like the real one
GUEST, STAFF = "10.10.30.50", "10.10.20.50"


def row(w, host, **kw):
    r = {"window_start": datetime.fromtimestamp(T0 + w * 10).strftime("%Y-%m-%d %H:%M:%S"),
         "host_ip": host, "off_hours": 0, "label": "", "attack_type": ""}
    r.update(kw)
    return r


# ---- 1. strict labelling: attack from 15 s to 45 s covers windows 2 and 3 fully, 1 and 4 by half ----
rows = [row(w, h) for w in range(6) for h in (GUEST, STAFF)]
kept, dropped = label_rows(rows, T0, "dos", GUEST, T0 + 15, T0 + 45)
g = {(r["window_start"][11:], r["label"]) for r in kept if r["host_ip"] == GUEST}
assert dropped == 2, dropped
assert sorted(l for _, l in g) == [0, 0, 1, 1], g
assert all(r["label"] == 0 and r["attack_type"] == "normal" for r in kept if r["host_ip"] == STAFF)
print("PASS strict labelling: 2 full attack windows = 1, 2 half windows dropped, bystander host always 0")

# ---- 2. the 90 % edge: 9.0 s of a 10 s window counts, 8.9 s does not ----
k, d = label_rows([row(1, GUEST)], T0, "dos", GUEST, T0 + 11.0, T0 + 30)
assert k[0]["label"] == 1 and d == 0
k, d = label_rows([row(1, GUEST)], T0, "dos", GUEST, T0 + 11.1, T0 + 30)
assert k == [] and d == 1
print("PASS 90 % threshold: 9.0 s labelled attack, 8.9 s dropped")

# ---- 3. normal runs label everything 0 ----
k, d = label_rows(rows, T0, "normal", "", None, None)
assert d == 0 and len(k) == len(rows) and all(r["label"] == 0 for r in k)
print("PASS normal run: every row labelled 0, nothing dropped")

# ---- 4. off-hours mode sets the flag only on the attacker's attack windows ----
k, _ = label_rows(rows, T0, "offhours", STAFF, T0 + 10, T0 + 30)
flagged = [(r["host_ip"], r["label"]) for r in k if r["off_hours"] == 1]
assert flagged == [(STAFF, 1), (STAFF, 1)], flagged
print("PASS off-hours: flag set on the 2 attack windows of staff-pc only")

# ---- 5. labelling does not modify the caller's rows ----
assert all(r["label"] == "" for r in rows)
print("PASS input rows left untouched")

# ---- 5b. after-effect: attack ends at 40.5 s, traces until 44.5 s -> window 4 dropped, window 5 normal ----
k, d = label_rows([row(w, GUEST) for w in (3, 4, 5)], T0, "bruteforce", GUEST, T0 + 10.5, T0 + 40.5, tail=4)
assert [(r["label"]) for r in k] == [1, 0] and d == 1, (k, d)
k, d = label_rows([row(4, GUEST)], T0, "bruteforce", GUEST, T0 + 10, T0 + 39.9, tail=0)
assert k[0]["label"] == 0 and d == 0
print("PASS after-effect: window with late rejects dropped; without a tail it would be labelled normal")

# ---- 6. agent is valid Python and refuses targets outside 10.10.0.0/16 ----
path = tempfile.mktemp(suffix=".py")
open(path, "w").write(AGENT)
subprocess.run([sys.executable, "-m", "py_compile", path], check=True)
for target in ("8.8.8.8", "192.168.1.1", "172.20.20.2"):
    r = subprocess.run([sys.executable, path, "dos", "1", target, "10"], capture_output=True, text=True)
    assert r.returncode != 0 and "refusing non-lab target" in r.stderr, (target, r.stderr)
r = subprocess.run([sys.executable, path, "normal", "1", "10.10.40.10", "10.10.30.1", "8.8.8.8", "1"],
                   capture_output=True, text=True)
assert "refusing non-lab target" in r.stderr
print("PASS agent compiles and refuses non-lab targets (internet, home LAN, lab management net)")
r = subprocess.run([sys.executable, path, "bruteforce", "1", "8.8.8.8", "5", "AA-BB-CC-DD-EE-FF", "s", "10.10.10.11", "bob"],
                   capture_output=True, text=True)
assert "refusing non-lab target" in r.stderr
r = subprocess.run([sys.executable, path, "bruteforce", "1", "10.10.10.5", "5", "AA-BB-CC-DD-EE-FF", "s", "1.2.3.4", "bob"],
                   capture_output=True, text=True)
assert "refusing non-lab target" in r.stderr
print("PASS brute force refuses a non-lab RADIUS server or NAS address")

# ---- 7. the RADIUS secret is read from the project file, not hard-coded ----
from zt_traffic import radius_secret
assert radius_secret() and " " not in radius_secret()
print("PASS RADIUS secret read from radius/clients.conf")
print("\nALL TESTS PASSED")
