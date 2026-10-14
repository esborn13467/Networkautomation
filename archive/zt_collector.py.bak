#!/usr/bin/env python3
"""
zt_collector.py - log collection and feature extraction (Phase 3, step 1)

Reads two sources from the lab:
  1. Packets mirrored to the SIEM host (SPAN session on acc1, Et2-4 -> Et6),
     captured with tcpdump inside clab-zt-siem.
  2. The FreeRADIUS debug log on clab-zt-radius, tailed live for
     "Access-Reject" events (failed 802.1X logins). The log carries no
     timestamps, so each reject is stamped when it is read.

A "session" is one host's activity during one time window (default 10 s).
For each session it computes the eight features named in Chapter 4, section 4.2:
  packet_count, avg_packet_size, bytes_transferred, connection_duration,
  failed_logins, unique_dst_ports, requests_per_min, off_hours

Labels (--label / --attack) are written only so results can be evaluated
later. The model itself never sees them.

Usage:
  python zt_collector.py --seconds 60 --out data/baseline.csv --label 0 --attack normal --sim-hours 8-17
"""
import argparse
import csv
import os
import random
import re
import subprocess
import threading
import time
from collections import defaultdict
from datetime import datetime

LAB = "clab-zt-"
SIEM_IP = "10.10.10.20"
RADIUS_IP = "10.10.10.5"
GATEWAYS = {"10.10.10.1", "10.10.20.1", "10.10.30.1", "10.10.99.1"}
INFRA = {SIEM_IP, RADIUS_IP, "10.10.10.11"} | GATEWAYS   # 10.10.10.11 = acc1 (RADIUS NAS)
ACCESS_NETS = ("10.10.10.", "10.10.20.", "10.10.30.", "10.10.99.")
PC_NODES = ["admin-pc", "staff-pc", "guest-pc"]

WINDOW = 10               # seconds per session
BUSINESS_HOURS = (8, 18)  # 08:00 to 17:59 counts as business hours

FEATURES = [
    "packet_count", "avg_packet_size", "bytes_transferred", "connection_duration",
    "failed_logins", "unique_dst_ports", "requests_per_min", "off_hours",
]
COLUMNS = ["window_start", "host_ip"] + FEATURES + ["label", "attack_type"]

# ---------- RADIUS log parsing ----------
RE_USER = re.compile(r'^\((\d+)\)\s+User-Name = "([^"]*)"')
RE_MAC = re.compile(r'^\((\d+)\)\s+Calling-Station-Id = "([0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2}){5})"')
RE_REJECT = re.compile(r'^\((\d+)\) Sent Access-Reject')


class RadiusRejectParser:
    """Feed it log lines; it returns (mac, username) when a reject is sent."""

    def __init__(self):
        self.user = {}
        self.mac = {}

    def feed(self, line):
        m = RE_USER.match(line)
        if m:
            self.user[m.group(1)] = m.group(2)
            return None
        m = RE_MAC.match(line)
        if m:
            self.mac[m.group(1)] = m.group(2).lower().replace("-", ":")
            return None
        m = RE_REJECT.match(line)
        if m:
            n = m.group(1)
            mac = self.mac.pop(n, None)
            user = self.user.pop(n, None)
            if mac:
                return (mac, user)
        return None


# ---------- feature extraction (pure functions, unit-tested) ----------
def is_host(ip):
    return ip.startswith(ACCESS_NETS) and ip not in INFRA


def parse_hours(spec):
    """None -> use the real clock. '14' -> fixed hour. '8-17' -> random per window."""
    if not spec:
        return None
    if "-" in spec:
        a, b = spec.split("-")
        return (int(a), int(b))
    return (int(spec), int(spec))


def hour_for(ts, sim):
    if sim is None:
        return datetime.fromtimestamp(ts).hour
    return random.randint(sim[0], sim[1])


def build_rows(packets, rejects, mac_to_ip, t0, label="", attack="", sim_hours=None, window=WINDOW):
    """
    packets : list of (ts, src, dst, proto, sport, dport, ip_len, is_syn_no_ack)
    rejects : list of (ts, mac)
    mac_to_ip: {'aa:bb:..': '10.10.30.50'}
    Returns a list of dict rows, one per (host, window) that had any activity.
    """
    per = defaultdict(lambda: {"pk": [], "flows": {}, "fails": 0})

    for (ts, src, dst, proto, sport, dport, ln, syn) in packets:
        if SIEM_IP in (src, dst):
            continue  # the collector does not score its own host
        w = int((ts - t0) // window)
        key = (proto, tuple(sorted([(src, sport), (dst, dport)])))
        for host in (src, dst):
            if not is_host(host):
                continue
            cell = per[(host, w)]
            cell["pk"].append(ln)
            fl = cell["flows"].setdefault(key, {"first": ts, "last": ts, "init": None, "dport": None})
            fl["last"] = max(fl["last"], ts)
            fl["first"] = min(fl["first"], ts)
            if fl["init"] is None or (syn and fl["init"][1] is False):
                fl["init"] = (src, syn)
                fl["dport"] = dport

    for (ts, mac) in rejects:
        ip = mac_to_ip.get(mac)
        if ip:
            per[(ip, int((ts - t0) // window))]["fails"] += 1

    rows = []
    for (host, w), c in sorted(per.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        n = len(c["pk"])
        flows = list(c["flows"].values())
        mine = [f for f in flows if f["init"] and f["init"][0] == host]
        ports = {f["dport"] for f in mine if f["dport"]}
        durs = [f["last"] - f["first"] for f in flows]
        wstart = t0 + w * window
        hr = hour_for(wstart, sim_hours)
        rows.append({
            "window_start": datetime.fromtimestamp(wstart).strftime("%Y-%m-%d %H:%M:%S"),
            "host_ip": host,
            "packet_count": n,
            "avg_packet_size": round(sum(c["pk"]) / n, 2) if n else 0,
            "bytes_transferred": sum(c["pk"]),
            "connection_duration": round(sum(durs) / len(durs), 4) if durs else 0,
            "failed_logins": c["fails"],
            "unique_dst_ports": len(ports),
            "requests_per_min": round(len(mine) * 60.0 / window, 2),
            "off_hours": 0 if BUSINESS_HOURS[0] <= hr < BUSINESS_HOURS[1] else 1,
            "label": label,
            "attack_type": attack,
        })
    return rows


# ---------- lab I/O ----------
def sh(cmd, timeout=None):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)


def learn_endpoints():
    """MAC -> IP for each PC, read from the containers themselves."""
    out = {}
    for node in PC_NODES:
        mac = sh(f"docker exec {LAB}{node} cat /sys/class/net/eth1/address").stdout.strip().lower()
        ipout = sh(f"docker exec {LAB}{node} ip -4 -o addr show eth1").stdout
        ips = re.findall(r"inet (\d+\.\d+\.\d+\.\d+)/", ipout)
        ips = [i for i in ips if i.startswith(ACCESS_NETS)]
        if mac and ips:
            out[mac] = ips[0]
    return out


def read_packets(pcap_path):
    from scapy.all import rdpcap, IP, TCP, UDP
    pkts = []
    for p in rdpcap(pcap_path):
        if IP not in p:
            continue
        ip = p[IP]
        sport = dport = 0
        syn = False
        if TCP in p:
            sport, dport = p[TCP].sport, p[TCP].dport
            f = int(p[TCP].flags)
            syn = bool(f & 0x02) and not (f & 0x10)
        elif UDP in p:
            sport, dport = p[UDP].sport, p[UDP].dport
        pkts.append((float(p.time), ip.src, ip.dst, ip.proto, sport, dport, int(ip.len), syn))
    return pkts


def collect_batch(seconds, label="", attack="", sim_hours=None, keep_pcap=None):
    """Capture `seconds` of mirrored traffic + RADIUS rejects, return feature rows."""
    mac_to_ip = learn_endpoints()
    if not mac_to_ip:
        raise SystemExit("Could not read PC MAC/IP from the lab. Is it running?")

    rejects, parser, lock = [], RadiusRejectParser(), threading.Lock()
    tail = subprocess.Popen(
        ["docker", "exec", f"{LAB}radius", "tail", "-n", "0", "-F", "/tmp/radius.log"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

    def reader():
        for line in tail.stdout:
            hit = parser.feed(line.rstrip("\n"))
            if hit:
                with lock:
                    rejects.append((time.time(), hit[0]))
    th = threading.Thread(target=reader, daemon=True)
    th.start()

    t0 = time.time()
    sh(f"docker exec {LAB}siem timeout {seconds} tcpdump -n -i eth1 -U -w /tmp/cap.pcap ip", timeout=seconds + 30)
    tail.terminate()
    th.join(timeout=2)

    local = keep_pcap or "/tmp/zt_cap.pcap"
    sh(f"docker cp {LAB}siem:/tmp/cap.pcap {local}")
    pkts = read_packets(local)
    with lock:
        rj = list(rejects)
    return build_rows(pkts, rj, mac_to_ip, t0, label, attack, sim_hours)


def write_csv(rows, path):
    new = not os.path.exists(path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if new:
            w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=60)
    ap.add_argument("--out", default="data/sessions.csv")
    ap.add_argument("--label", default="", help="0 normal / 1 attack, for evaluation only")
    ap.add_argument("--attack", default="")
    ap.add_argument("--sim-hours", default=None, help="e.g. 8-17 (random per window) or 2 (fixed)")
    a = ap.parse_args()
    rows = collect_batch(a.seconds, a.label, a.attack, parse_hours(a.sim_hours))
    write_csv(rows, a.out)
    print(f"{len(rows)} sessions -> {a.out}")
    for r in rows[:10]:
        print({k: r[k] for k in ["host_ip"] + FEATURES})
