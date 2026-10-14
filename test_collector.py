#!/usr/bin/env python3
"""Offline checks for zt_collector.py. No lab needed: python test_collector.py"""
from zt_collector import RadiusRejectParser, build_rows

T0 = 1_000_000.0
MAC = "aa:c1:ab:01:b0:73"

# ---- 1. RADIUS parser, using line shapes copied from the real log ----
LOG = '''\
(38)   Calling-Station-Id = "AA-C1-AB-01-B0-73"
(38)   User-Name = "guest1"
(38) suffix: No '@' in User-Name = "guest1", looking up realm NULL
(38) attr_filter.access_reject: EXPAND %{User-Name}
(38) Sent Access-Reject Id 8 from 10.10.10.5:1812 to 10.10.10.11:49310 length 44
(39)   Calling-Station-Id = "AA-C1-AB-39-A0-D5"
(39)   User-Name = "bob"
(39) Sent Access-Accept Id 9 from 10.10.10.5:1812 to 10.10.10.11:49310 length 44
(40)   Calling-Station-Id = "AA-C1-AB-01-B0-73"
(40) Sent Access-Challenge Id 10 from 10.10.10.5:1812 to 10.10.10.11:49310 length 60
(41)   Calling-Station-Id = "AA-C1-AB-01-B0-73"
(41)   User-Name = "guest1"
(41) Sent Access-Reject Id 11 from 10.10.10.5:1812 to 10.10.10.11:49310 length 44
'''
p = RadiusRejectParser()
events = [e for e in (p.feed(l) for l in LOG.splitlines()) if e]
assert events == [(MAC, "guest1"), (MAC, "guest1")], events
print("PASS radius parser: 2 rejects found, accept/challenge ignored, user line not confused with suffix line")


# ---- helpers to fabricate packets: (ts, src, dst, proto, sport, dport, len, syn_no_ack) ----
def http_flow(t, host, sport, server="10.10.40.10"):
    return [
        (t,        host,   server, 6, sport, 80, 60,  True),
        (t + .01,  server, host,   6, 80, sport, 60,  False),
        (t + .02,  host,   server, 6, sport, 80, 52,  False),
        (t + .03,  host,   server, 6, sport, 80, 127, False),
        (t + .05,  server, host,   6, 80, sport, 500, False),
    ]


# ---- 2. normal: three web requests in one window ----
pk = []
for i in range(3):
    pk += http_flow(T0 + 1 + i * 2, "10.10.20.50", 40000 + i)
rows = build_rows(pk, [], {}, T0, "0", "normal", (10, 10))
r = [x for x in rows if x["host_ip"] == "10.10.20.50"][0]
assert r["packet_count"] == 15 and r["unique_dst_ports"] == 1, r
assert r["requests_per_min"] == 18.0 and r["off_hours"] == 0 and r["failed_logins"] == 0, r
assert r["bytes_transferred"] == 3 * (60 + 60 + 52 + 127 + 500), r
print("PASS normal browsing:", {k: r[k] for k in ("packet_count", "unique_dst_ports", "requests_per_min", "bytes_transferred")})

# the web server is not a host: no row for 10.10.40.10
assert not any(x["host_ip"] == "10.10.40.10" for x in rows)
print("PASS server side not scored as a host")

# ---- 3. port scan: 20 ports, one SYN each ----
pk = [(T0 + 12 + i * .05, "10.10.30.50", "10.10.40.10", 6, 50000 + i, 1 + i, 60, True) for i in range(20)]
r = build_rows(pk, [], {}, T0, "1", "port_scan", (10, 10))[0]
assert r["unique_dst_ports"] == 20 and r["requests_per_min"] == 120.0 and r["connection_duration"] == 0, r
print("PASS port scan:", {k: r[k] for k in ("unique_dst_ports", "requests_per_min", "connection_duration")})

# ---- 4. UDP flood: one flow, many big packets ----
pk = [(T0 + 25 + i * .005, "10.10.10.50", "10.10.40.10", 17, 5000, 9999, 1400, False) for i in range(500)]
r = build_rows(pk, [], {}, T0, "1", "dos", (10, 10))[0]
assert r["packet_count"] == 500 and r["avg_packet_size"] == 1400 and r["bytes_transferred"] == 700000, r
assert r["connection_duration"] > 2.4, r
print("PASS flood:", {k: r[k] for k in ("packet_count", "avg_packet_size", "bytes_transferred", "connection_duration")})

# ---- 5. failed logins with no IP traffic still make a row; unknown MACs are ignored ----
rj = [(T0 + 31, MAC), (T0 + 33, MAC), (T0 + 34, "de:ad:be:ef:00:00")]
rows = build_rows([], rj, {MAC: "10.10.30.50"}, T0, "1", "brute_force", (10, 10))
assert len(rows) == 1 and rows[0]["host_ip"] == "10.10.30.50", rows
assert rows[0]["failed_logins"] == 2 and rows[0]["packet_count"] == 0, rows
print("PASS failed logins: 2 counted for the right host, unknown MAC ignored")

# ---- 6. off-hours flag follows the simulated hour ----
pk = http_flow(T0 + 1, "10.10.20.50", 41000)
assert build_rows(pk, [], {}, T0, "", "", (2, 2))[0]["off_hours"] == 1
assert build_rows(pk, [], {}, T0, "", "", (7, 7))[0]["off_hours"] == 1
assert build_rows(pk, [], {}, T0, "", "", (8, 8))[0]["off_hours"] == 0
assert build_rows(pk, [], {}, T0, "", "", (17, 17))[0]["off_hours"] == 0
assert build_rows(pk, [], {}, T0, "", "", (18, 18))[0]["off_hours"] == 1
print("PASS off-hours boundaries: 07h=1, 08h=0, 17h=0, 18h=1")

# ---- 7. traffic to or from the SIEM is excluded ----
pk = [(T0 + 1, "10.10.20.50", "10.10.10.20", 1, 0, 0, 84, False)]
assert build_rows(pk, [], {}, T0) == []
print("PASS SIEM-bound traffic excluded")

# ---- 8. two windows are kept separate ----
pk = http_flow(T0 + 1, "10.10.20.50", 42000) + http_flow(T0 + 13, "10.10.20.50", 42001)
rows = build_rows(pk, [], {}, T0, "", "", (10, 10))
assert [x["packet_count"] for x in rows] == [5, 5], rows
print("PASS windowing: two 10 s windows -> two rows")

# ---- 9. fast pcap reader agrees with scapy (TCP SYN, ACK, UDP, ICMP, VLAN tag, truncated capture) ----
import os, tempfile
from scapy.all import Ether, Dot1Q, IP, TCP, UDP, ICMP, Raw, wrpcap
from zt_collector import read_packets
frames = [
    Ether() / IP(src="10.10.30.50", dst="10.10.40.10") / TCP(sport=40000, dport=80, flags="S"),
    Ether() / IP(src="10.10.40.10", dst="10.10.30.50") / TCP(sport=80, dport=40000, flags="SA"),
    Ether() / IP(src="10.10.20.50", dst="10.10.40.10") / TCP(sport=40001, dport=80, flags="A") / Raw(b"x" * 1400),
    Ether() / IP(src="10.10.10.50", dst="1.1.1.1") / UDP(sport=5353, dport=53) / Raw(b"q" * 30),
    Ether() / IP(src="10.10.10.50", dst="10.10.10.1") / ICMP(),
    Ether() / Dot1Q(vlan=30) / IP(src="10.10.30.50", dst="10.10.40.10") / TCP(sport=40002, dport=22, flags="S"),
]
for i, fr in enumerate(frames):
    fr.time = T0 + i * 0.5
path = os.path.join(tempfile.mkdtemp(), "t.pcap")
wrpcap(path, frames)
os.system(f"tcpdump -r {path} -s 128 -w {path}.snap 2>/dev/null")  # truncate like the live capture, if tcpdump exists
got = read_packets(path + ".snap" if os.path.exists(path + ".snap") else path)
want = [(T0, "10.10.30.50", "10.10.40.10", 6, 40000, 80, 40, True),
        (T0 + 0.5, "10.10.40.10", "10.10.30.50", 6, 80, 40000, 40, False),
        (T0 + 1.0, "10.10.20.50", "10.10.40.10", 6, 40001, 80, 1440, False),
        (T0 + 1.5, "10.10.10.50", "1.1.1.1", 17, 5353, 53, 58, False),
        (T0 + 2.0, "10.10.10.50", "10.10.10.1", 1, 0, 0, 28, False),
        (T0 + 2.5, "10.10.30.50", "10.10.40.10", 6, 40002, 22, 40, True)]
assert [(round(p[0], 3),) + p[1:] for p in got] == want, got
print("PASS pcap reader: TCP/UDP/ICMP, SYN flag, 802.1Q tag, real IP length kept after truncation")
print("\nALL TESTS PASSED")
