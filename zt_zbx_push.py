#!/usr/bin/env python3
"""
zt_zbx_push.py - every lab node pushes its own metrics to Zabbix (trapper items)

SNMP and ping only let Zabbix *ask* the switches and *ping* the hosts. This script
makes all nine lab nodes *push* data: for each node it reads the container's own
counters (interface packets/bytes, CPU time, memory) and sends them to the Zabbix
server with the Zabbix sender protocol (TCP 10051). Zabbix turns the counters
into per-second rates. The same channel carries security alerts from the
detection pipeline (see send_alert, used by the response engine later).

Usage:
  python zt_zbx_push.py setup                 # once per lab-up (after zbx_setup.py)
  python zt_zbx_push.py run --interval 30     # push loop; Ctrl+C to stop
  python zt_zbx_push.py once                  # one push, prints what was sent
  python zt_zbx_push.py alert guest-pc "test alert"
"""
import argparse
import json
import socket
import struct
import subprocess
import sys
import time

import zbx_setup as zs   # reuses its api() and login (runs no setup on import, see guard there)

NODES = zs.SNMP_HOSTS + zs.ICMP_HOSTS
TEMPLATE = "ZT Push"
TRAPPER, FLOAT, TEXT, UNSIGNED = 2, 0, 4, 3
CHANGE_PER_SEC = 10

# key, name, value type, units, preprocessing
ITEMS = [
    ("zt.net.in.pps",  "Data ports: packets in per second",  FLOAT, "pps", CHANGE_PER_SEC),
    ("zt.net.out.pps", "Data ports: packets out per second", FLOAT, "pps", CHANGE_PER_SEC),
    ("zt.net.in.bps",  "Data ports: bytes in per second",    FLOAT, "Bps", CHANGE_PER_SEC),
    ("zt.net.out.bps", "Data ports: bytes out per second",   FLOAT, "Bps", CHANGE_PER_SEC),
    ("zt.net.drops",   "Data ports: dropped packets per second", FLOAT, "", CHANGE_PER_SEC),
    ("zt.cpu.pct",     "Container CPU usage",                FLOAT, "%", None),
    ("zt.mem.bytes",   "Container memory in use",            UNSIGNED, "B", None),
    ("zt.alert",       "Security alert (detection pipeline)", TEXT, "", None),
    ("zt.anomaly.score", "Anomaly score (Isolation Forest)",  FLOAT, "", None),
    ("zt.action",      "Last response action",               TEXT, "", None),
    ("zt.response.ms", "Detection-to-action time",           FLOAT, "ms", None),
]
# Anomaly score convention: score = -IsolationForest.decision_function(x), so above the
# threshold (0 by default, tuned later) means anomalous. The macro lets the threshold
# be changed in Zabbix without touching the template.
SCORE_MACRO = "{$ZT.SCORE.THRESHOLD}"
TRIGGERS = [
    ("High packet rate on {HOST.NAME}", "last(/ZT Push/zt.net.in.pps)>1000 or last(/ZT Push/zt.net.out.pps)>1000", 3),
    ("Container CPU above 80% on {HOST.NAME}", "min(/ZT Push/zt.cpu.pct,2m)>80", 2),
    ("Security alert on {HOST.NAME}: {ITEM.LASTVALUE}", "nodata(/ZT Push/zt.alert,30m)=0", 4),
    ("Anomaly score above threshold on {HOST.NAME}", "last(/ZT Push/zt.anomaly.score)>" + SCORE_MACRO, 3),
]


# ---------- Zabbix sender protocol ----------
def server_addr():
    fmt = '{{(index .NetworkSettings.Networks "clab").IPAddress}}'
    ip = subprocess.check_output(["docker", "inspect", "-f", fmt, "zbx-server"], text=True).strip()
    return ip, 10051


def frame(payload):
    body = json.dumps(payload).encode()
    return b"ZBXD\x01" + struct.pack("<Q", len(body)) + body


def send(values, addr=None):
    """values: list of (host, key, value). Returns the server's reply text."""
    now = int(time.time())
    data = [{"host": h, "key": k, "value": str(v), "clock": now} for h, k, v in values]
    with socket.create_connection(addr or server_addr(), timeout=10) as s:
        s.sendall(frame({"request": "sender data", "data": data}))
        head = s.recv(13)
        if not head.startswith(b"ZBXD"):
            raise RuntimeError("unexpected reply from Zabbix server")
        n = struct.unpack("<Q", head[5:13])[0]
        body = b""
        while len(body) < n:
            body += s.recv(n - len(body))
    return json.loads(body).get("info", "")


# ---------- reading a node ----------
READ = "cat /proc/net/dev; echo ==; cat /sys/fs/cgroup/cpu.stat; echo ==; cat /sys/fs/cgroup/memory.current"


def parse_node(text):
    """Turn the READ output into counters. eth0 (management) is ignored."""
    netdev, cpu, mem = text.split("==\n")
    rx_b = rx_p = tx_b = tx_p = drops = 0
    for line in netdev.splitlines():
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        name = name.strip()
        if not name.startswith("eth") or name == "eth0":
            continue
        f = [int(x) for x in rest.split()]
        rx_b += f[0]; rx_p += f[1]; drops += f[3]
        tx_b += f[8]; tx_p += f[9]; drops += f[11]
    usec = int(next(l.split()[1] for l in cpu.splitlines() if l.startswith("usage_usec")))
    return {"rx_b": rx_b, "rx_p": rx_p, "tx_b": tx_b, "tx_p": tx_p, "drops": drops,
            "cpu_usec": usec, "mem": int(mem.strip())}


def read_node(node):
    r = subprocess.run(["docker", "exec", f"clab-zt-{node}", "sh", "-c", READ],
                       capture_output=True, text=True, timeout=15)
    return parse_node(r.stdout) if r.returncode == 0 else None


def values_for(node, c, prev, dt):
    host = f"zt-{node}"
    out = [(host, "zt.net.in.pps", c["rx_p"]), (host, "zt.net.out.pps", c["tx_p"]),
           (host, "zt.net.in.bps", c["rx_b"]), (host, "zt.net.out.bps", c["tx_b"]),
           (host, "zt.net.drops", c["drops"]), (host, "zt.mem.bytes", c["mem"])]
    if prev and dt > 0:
        out.append((host, "zt.cpu.pct", round((c["cpu_usec"] - prev["cpu_usec"]) / 1e6 / dt * 100, 2)))
    return out


def push_all(prev, last_t):
    now, vals, cur = time.time(), [], {}
    for n in NODES:
        c = read_node(n)
        if c:
            cur[n] = c
            vals += values_for(n, c, prev.get(n), now - last_t if last_t else 0)
    info = send(vals) if vals else "no nodes reachable"
    return cur, now, info, vals


def send_alert(node, text):
    """Called by the response engine: shows up in Zabbix as a Problem on that host."""
    return send([(f"zt-{node}", "zt.alert", text)])


def send_score(node, score):
    """Called by the pipeline every window: one anomaly score per host."""
    return send([(f"zt-{node}", "zt.anomaly.score", round(float(score), 4))])


def send_action(node, action, response_ms):
    """Called by the response engine after an action is applied."""
    return send([(f"zt-{node}", "zt.action", action), (f"zt-{node}", "zt.response.ms", round(response_ms, 1))])


# ---------- Zabbix configuration ----------
def setup():
    gid = zs.api("templategroup.get", {"filter": {"name": ["Templates"]}})[0]["groupid"]
    old = zs.api("template.get", {"filter": {"host": [TEMPLATE]}, "output": ["templateid"]})
    if old:
        zs.api("template.delete", [old[0]["templateid"]])
    tid = zs.api("template.create", {"host": TEMPLATE, "groups": [{"groupid": gid}],
                                     "macros": [{"macro": SCORE_MACRO, "value": "0"}]})["templateids"][0]
    for key, name, vtype, units, pre in ITEMS:
        item = {"hostid": tid, "key_": key, "name": name, "type": TRAPPER, "value_type": vtype, "units": units}
        if pre:
            item["preprocessing"] = [{"type": pre, "params": "", "error_handler": 0, "error_handler_params": ""}]
        zs.api("item.create", item)
    for desc, expr, prio in TRIGGERS:
        t = {"description": desc, "expression": expr, "priority": prio}
        if "zt.alert" in expr:
            t["manual_close"] = 1
            t["type"] = 0          # one open problem per host until an admin closes it
        zs.api("trigger.create", t)
    hosts = zs.api("host.get", {"filter": {"host": [f"zt-{n}" for n in NODES]}, "output": ["hostid", "host"],
                                "selectParentTemplates": ["templateid"]})
    for h in hosts:
        tmpls = [{"templateid": t["templateid"]} for t in h["parentTemplates"]] + [{"templateid": tid}]
        zs.api("host.update", {"hostid": h["hostid"], "templates": tmpls})
    print(f"template '{TEMPLATE}' with {len(ITEMS)} items and {len(TRIGGERS)} triggers linked to {len(hosts)} hosts")
    dashboard()


def dashboard():
    name = "ZT Lab overview"
    old = zs.api("dashboard.get", {"filter": {"name": [name]}, "output": ["dashboardid"]})
    if old:
        zs.api("dashboard.delete", [old[0]["dashboardid"]])

    def graph(x, y, title, item):
        return {"type": "svggraph", "name": title, "x": x, "y": y, "width": 36, "height": 5, "fields": [
            {"type": 1, "name": "ds.0.hosts.0", "value": "zt-*"},
            {"type": 1, "name": "ds.0.items.0", "value": item},
            {"type": 0, "name": "ds.0.aggregate_function", "value": 0},
            {"type": 0, "name": "legend_lines", "value": 5},
        ]}
    health = [
        {"type": "problems", "name": "Security alerts and problems", "x": 0, "y": 0, "width": 36, "height": 5,
         "fields": [{"type": 0, "name": "show_lines", "value": 15}]},
        {"type": "hostavail", "name": "Host availability", "x": 36, "y": 0, "width": 36, "height": 5, "fields": []},
        graph(0, 5, "Packets in per second (all nodes)", "Data ports: packets in per second"),
        graph(36, 5, "Bytes in per second (all nodes)", "Data ports: bytes in per second"),
        graph(0, 10, "Container CPU %", "Container CPU usage"),
        graph(36, 10, "Container memory", "Container memory in use"),
    ]
    pcs = [f"zt-{n}" for n in ("admin-pc", "staff-pc", "guest-pc")]
    hosts = zs.api("host.get", {"filter": {"host": [f"zt-{n}" for n in NODES]}, "output": ["hostid"]})
    ids = {}
    for key in ("zt.action", "zt.response.ms"):
        its = zs.api("item.get", {"hostids": [h["hostid"] for h in hosts], "filter": {"key_": key}, "output": ["itemid"]})
        ids[key] = [i["itemid"] for i in its]

    names = {i["itemid"]: i["hosts"][0]["host"] for key in ids
             for i in zs.api("item.get", {"itemids": ids[key], "output": ["itemid"], "selectHosts": ["host"]})}

    def itemlist(x, y, w, title, key):
        # "Item history" widget (Zabbix 7.0): one column per host, newest values first
        f = []
        for n, i in enumerate(sorted((i for i in ids[key] if names[i] in pcs), key=lambda i: names[i])):
            f += [{"type": 1, "name": f"columns.{n}.name", "value": names[i]},
                  {"type": 4, "name": f"columns.{n}.itemid", "value": i}]
        return {"type": "itemhistory", "name": title, "x": x, "y": y, "width": w, "height": 5,
                "fields": f + [{"type": 0, "name": "show_lines", "value": 10}]}
    score = {"type": "svggraph", "name": "Anomaly score per PC (red line = threshold)", "x": 0, "y": 0, "width": 72, "height": 6,
             "fields": [{"type": 1, "name": f"ds.0.hosts.{n}", "value": h} for n, h in enumerate(pcs)] + [
                 {"type": 1, "name": "ds.0.items.0", "value": "Anomaly score (Isolation Forest)"},
                 {"type": 0, "name": "simple_triggers", "value": 1},
                 {"type": 0, "name": "legend_lines", "value": 3}]}
    detection = [
        score,
        {"type": "problems", "name": "Security alerts", "x": 0, "y": 6, "width": 36, "height": 5,
         "fields": [{"type": 1, "name": "problem", "value": "Security alert"}, {"type": 0, "name": "show_lines", "value": 10}]},
        itemlist(36, 6, 36, "Last response action per host", "zt.action"),
        itemlist(0, 11, 72, "Detection-to-action time (ms)", "zt.response.ms"),
    ]
    zs.api("dashboard.create", {"name": name, "display_period": 30, "auto_start": 0,
                                "pages": [{"name": "Network health", "widgets": health},
                                          {"name": "Threat detection and response", "widgets": detection}]})
    print(f"dashboard '{name}' created: Dashboards > All dashboards > {name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["setup", "run", "once", "alert"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--interval", type=int, default=30)
    a = ap.parse_args()
    if a.cmd == "setup":
        zs.login()
        setup()
    elif a.cmd == "alert":
        print(send_alert(a.args[0], " ".join(a.args[1:]) or "test alert"))
    elif a.cmd == "once":
        cur, t, info, vals = push_all({}, 0)
        for v in vals:
            print(v)
        print(info)
    else:
        prev, last = {}, 0
        while True:
            try:
                prev, last, info, _ = push_all(prev, last)
                print(time.strftime("%H:%M:%S"), info, flush=True)
            except Exception as e:      # keep pushing if Zabbix restarts
                print(time.strftime("%H:%M:%S"), "push failed:", e, file=sys.stderr, flush=True)
            time.sleep(a.interval)
