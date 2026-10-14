#!/usr/bin/env python3
"""
zt_traffic.py - traffic generator and labelled dataset runs (Phase 3, step 2)

Puts a small agent (/tmp/zt_agent.py, standard library only) inside each PC
container and drives it with `docker exec`. Every run captures through
zt_collector, so the rows it writes are exactly what the model will see.

Modes (the attacker is always one lab PC, every target is a fixed lab address):
  normal    all three PCs browse the DMZ web server and ping at human-like pace
  dos       guest-pc floods the web server with HTTP requests       -> packet_count, requests_per_min
  portscan  guest-pc probes TCP ports on the web server one by one  -> unique_dst_ports
  insider   staff-pc pulls a large file from the web server again and again -> bytes_transferred
  offhours  staff-pc behaves normally but at night (off_hours flag set on the attack windows)

Normal traffic keeps running on all three PCs during every attack, as it would
in a real network.

Strict labelling: a window of the attacking host is labelled 1 only when the
attack covers at least 90 % of it. Windows that the attack only partly covers
are dropped, so a half-attack window never shows up as a "false alarm".
Windows of the other hosts, and attacker windows with no attack in them, are 0.

Usage:
  python zt_traffic.py setup
  python zt_traffic.py run --mode normal   --seconds 600 --out data/normal_01.csv
  python zt_traffic.py run --mode dos      --seconds 60  --attack-start 15 --attack-len 30 --out data/dos_01.csv
  python zt_traffic.py stop
"""
import argparse
import os
import subprocess
import threading
import time
from datetime import datetime

import zt_collector as zc

LAB = zc.LAB
PCS = {"admin-pc": "10.10.10.50", "staff-pc": "10.10.20.50", "guest-pc": "10.10.30.50"}
GATEWAY = {"admin-pc": "10.10.10.1", "staff-pc": "10.10.20.1", "guest-pc": "10.10.30.1"}
WEB = "10.10.40.10"
RADIUS = zc.RADIUS_IP

ATTACKER = {"dos": "guest-pc", "portscan": "guest-pc", "insider": "staff-pc", "offhours": "staff-pc"}
DEFAULT_RATE = {"dos": 80, "portscan": 30, "insider": 1_500_000}   # req/s, ports/s, bytes/s
STRICT = 0.9

# ---------- the agent that runs inside each PC (Python 3.11, stdlib only) ----------
AGENT = r'''
import ipaddress, random, socket, subprocess, sys, threading, time, urllib.request

LAB_NET = ipaddress.ip_network("10.10.0.0/16")


def lab_only(ip):
    if ipaddress.ip_address(ip) not in LAB_NET:
        raise SystemExit("refusing non-lab target " + ip)
    return ip


def get(url, timeout=3):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            while r.read(65536):
                pass
    except Exception:
        pass


def ping(ip):
    subprocess.run(["ping", "-c", "1", "-W", "1", ip], capture_output=True)


def normal(seconds, web, gw, extra, seed):
    """Human-like: alternating busy and quiet minutes, mostly small page loads."""
    random.seed(seed)
    end = time.time() + seconds
    pace, switch = random.choice([2.0, 4.0, 8.0]), time.time() + random.uniform(30, 90)
    while time.time() < end:
        if time.time() > switch:
            pace, switch = random.choice([2.0, 4.0, 8.0]), time.time() + random.uniform(30, 90)
        r = random.random()
        if r < 0.55:
            get("http://%s/" % web)
        elif r < 0.65:
            get("http://%s/doc.bin" % web)
        elif r < 0.85:
            ping(gw)
        elif extra:
            ping(random.choice(extra))
        time.sleep(max(0.0, min(random.expovariate(1.0 / pace), end - time.time())))


def dos(seconds, target, rate):
    """HTTP flood: `rate` new connections per second spread over 8 threads."""
    end, threads = time.time() + seconds, 8
    gap = threads / float(rate)

    def worker():
        while time.time() < end:
            t = time.time()
            get("http://%s/" % target, timeout=2)
            time.sleep(max(0.0, gap - (time.time() - t)))
    ts = [threading.Thread(target=worker, daemon=True) for _ in range(threads)]
    [t.start() for t in ts]
    [t.join() for t in ts]


def portscan(seconds, target, rate):
    """TCP connect scan, one new port every 1/rate seconds, from port 1 upward."""
    end, port = time.time() + seconds, 1

    def probe(p):
        s = socket.socket()
        s.settimeout(1.0)
        try:
            s.connect_ex((target, p))
        finally:
            s.close()
    while time.time() < end:
        threading.Thread(target=probe, args=(port,), daemon=True).start()
        port = port % 65535 + 1
        time.sleep(1.0 / rate)
    time.sleep(1.2)


def insider(seconds, target, rate):
    """Bulk download of a large file, throttled to `rate` bytes per second."""
    end = time.time() + seconds
    while time.time() < end:
        try:
            with urllib.request.urlopen("http://%s/big.bin" % target, timeout=5) as r:
                while time.time() < end:
                    t = time.time()
                    if not r.read(65536):
                        break
                    time.sleep(max(0.0, 65536.0 / rate - (time.time() - t)))
        except Exception:
            time.sleep(0.5)


if __name__ == "__main__":
    mode, seconds = sys.argv[1], float(sys.argv[2])
    if mode == "normal":
        extra = [lab_only(x) for x in sys.argv[5].split(",") if x]
        normal(seconds, lab_only(sys.argv[3]), lab_only(sys.argv[4]), extra, int(sys.argv[6]))
    else:
        target, rate = lab_only(sys.argv[3]), float(sys.argv[4])
        {"dos": dos, "portscan": portscan, "insider": insider}[mode](seconds, target, rate)
'''


def sh(cmd, inp=None):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, input=inp)


def setup():
    """Copy the agent into each PC and put test files on the web server."""
    for pc in PCS:
        r = sh(f"docker exec -i {LAB}{pc} sh -c 'cat > /tmp/zt_agent.py'", AGENT)
        if r.returncode:
            raise SystemExit(f"could not reach {pc}: {r.stderr.strip()}")
    sh(f"docker exec {LAB}web sh -c '"
       "[ -f /srv/www/doc.bin ] || head -c 200000 /dev/urandom > /srv/www/doc.bin; "
       "[ -f /srv/www/big.bin ] || head -c 20000000 /dev/urandom > /srv/www/big.bin'")
    print("agent installed on", ", ".join(PCS), "| doc.bin (200 kB) and big.bin (20 MB) on web")


def stop():
    for pc in PCS:
        sh(f"docker exec {LAB}{pc} pkill -f zt_agent.py")


def start_normal(seconds):
    for i, pc in enumerate(PCS):
        extra = RADIUS if pc != "guest-pc" else ""
        seed = int(time.time()) + i
        sh(f"docker exec -d {LAB}{pc} python3 /tmp/zt_agent.py normal {seconds} {WEB} {GATEWAY[pc]} '{extra}' {seed}")


def start_attack(mode, seconds, rate):
    pc = ATTACKER[mode]
    if mode != "offhours":
        sh(f"docker exec -d {LAB}{pc} python3 /tmp/zt_agent.py {mode} {seconds} {WEB} {rate}")


# ---------- labelling (pure, unit-tested) ----------
def window_index(row, t0, window=zc.WINDOW):
    ws = datetime.strptime(row["window_start"], "%Y-%m-%d %H:%M:%S").timestamp()
    return round((ws - t0) / window)


def label_rows(rows, t0, mode, attacker_ip, a0, a1, window=zc.WINDOW):
    """Apply strict labelling. Returns (kept_rows, dropped_count)."""
    kept, dropped = [], 0
    for r in rows:
        r = dict(r)
        r["label"], r["attack_type"] = 0, "normal"
        if mode != "normal" and r["host_ip"] == attacker_ip:
            w = window_index(r, t0, window)
            ws, we = t0 + w * window, t0 + (w + 1) * window
            frac = max(0.0, min(we, a1) - max(ws, a0)) / window
            if frac >= STRICT:
                r["label"], r["attack_type"] = 1, mode
                if mode == "offhours":
                    r["off_hours"] = 1
            elif frac > 0:
                dropped += 1
                continue
        kept.append(r)
    return kept, dropped


def run(mode, seconds, attack_start, attack_len, rate, out, sim_hours):
    if mode != "normal" and attack_start + attack_len > seconds:
        raise SystemExit("attack must end before the capture does")
    setup()
    stop()
    start_normal(seconds + 5)
    time.sleep(2)                      # let normal traffic settle before t0

    result = {}
    cap = threading.Thread(target=lambda: result.update(r=zc.capture(seconds)))
    cap.start()
    a0 = a1 = None
    if mode != "normal":
        time.sleep(attack_start)
        start_attack(mode, attack_len, rate)
        a0 = time.time()
        a1 = a0 + attack_len
        print(f"attack '{mode}' from {ATTACKER[mode]} for {attack_len}s")
    cap.join()
    stop()

    pkts, rejects, mac_to_ip, t0 = result["r"]
    rows = zc.build_rows(pkts, rejects, mac_to_ip, t0, sim_hours=sim_hours)
    attacker_ip = PCS.get(ATTACKER.get(mode, ""), "")
    rows, dropped = label_rows(rows, t0, mode, attacker_ip, a0, a1)
    zc.write_csv(rows, out)

    n1 = sum(r["label"] == 1 for r in rows)
    print(f"{len(pkts)} packets -> {len(rows)} rows ({n1} attack, {len(rows) - n1} normal, {dropped} transition dropped) -> {out}")
    for r in rows:
        print(f"  {r['window_start'][11:]} {r['host_ip']:<12} pk={r['packet_count']:<6} bytes={r['bytes_transferred']:<9} "
              f"ports={r['unique_dst_ports']:<4} rpm={r['requests_per_min']:<7} fail={r['failed_logins']} "
              f"off={r['off_hours']} label={r['label']} {r['attack_type']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["setup", "run", "stop"])
    ap.add_argument("--mode", default="normal", choices=["normal", "dos", "portscan", "insider", "offhours"])
    ap.add_argument("--seconds", type=int, default=60, help="capture length; use a multiple of 10")
    ap.add_argument("--attack-start", type=int, default=15, help="seconds after capture start")
    ap.add_argument("--attack-len", type=int, default=30)
    ap.add_argument("--rate", type=float, default=None, help="dos req/s, portscan ports/s, insider bytes/s")
    ap.add_argument("--out", default="data/sessions.csv")
    ap.add_argument("--sim-hours", default="8-17", help="business-hours clock for every window (see zt_collector)")
    a = ap.parse_args()
    if a.cmd == "setup":
        setup()
    elif a.cmd == "stop":
        stop()
    else:
        rate = a.rate or DEFAULT_RATE.get(a.mode, 0)
        run(a.mode, a.seconds, a.attack_start, a.attack_len, rate, a.out, zc.parse_hours(a.sim_hours))
