#!/usr/bin/env python3
"""Offline checks for zt_zbx_push.py. No lab or Zabbix needed: python test_zbx_push.py"""
import json
import socket
import struct
import threading

from zt_zbx_push import parse_node, values_for, send

# ---- 1. counters from a real cEOS read (eth0 = management, must be ignored) ----
TEXT = """Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
  eth0:  136214    1268    0    0    0     0          0         0   184668    1378    0    0    0     0       0          0
  eth3: 1375456   12702    0  372    0     0          0         0  1169494   12801    0    0    0     0       0          0
  eth1: 1231073   12910    0    1    0     0          0         0  1569503   13850    0    2    0     0       0          0
    lo:     500       5    0    0    0     0          0         0      500       5    0    0    0     0       0          0
==
usage_usec 224934424
user_usec 1
==
1527697408
"""
c = parse_node(TEXT)
assert c == {"rx_b": 1375456 + 1231073, "rx_p": 12702 + 12910, "tx_b": 1169494 + 1569503,
             "tx_p": 12801 + 13850, "drops": 372 + 1 + 2, "cpu_usec": 224934424, "mem": 1527697408}, c
print("PASS node counters: data ports summed, eth0 and lo ignored, drops counted both ways")

# ---- 2. CPU % from two reads 10 s apart (2 s of CPU time = 20 %) ----
prev = dict(c, cpu_usec=c["cpu_usec"] - 2_000_000)
v = dict(((k, val) for _, k, val in values_for("core", c, prev, 10.0)))
assert v["zt.cpu.pct"] == 20.0 and v["zt.net.in.pps"] == c["rx_p"], v
assert "zt.cpu.pct" not in dict((k, 1) for _, k, _ in values_for("core", c, None, 0))
print("PASS CPU %: 20.0 from 2 s CPU in 10 s; skipped on the first read")

# ---- 3. sender protocol round trip against a fake Zabbix server ----
got = {}
srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(1)


def fake():
    conn, _ = srv.accept()
    head = conn.recv(13)
    n = struct.unpack("<Q", head[5:13])[0]
    body = b""
    while len(body) < n:
        body += conn.recv(n - len(body))
    got["head"], got["req"] = head[:5], json.loads(body)
    reply = json.dumps({"response": "success", "info": "processed: 1; failed: 0; total: 1"}).encode()
    conn.sendall(b"ZBXD\x01" + struct.pack("<Q", len(reply)) + reply)
    conn.close()


threading.Thread(target=fake, daemon=True).start()
info = send([("zt-guest-pc", "zt.alert", "DoS from 10.10.30.50")], srv.getsockname())
assert got["head"] == b"ZBXD\x01" and got["req"]["request"] == "sender data"
assert got["req"]["data"][0]["host"] == "zt-guest-pc" and got["req"]["data"][0]["value"] == "DoS from 10.10.30.50"
assert info.startswith("processed: 1")
print("PASS sender protocol: header, JSON body and server reply handled")
print("\nALL TESTS PASSED")
