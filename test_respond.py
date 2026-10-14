#!/usr/bin/env python3
"""Offline checks for zt_respond.py. No lab needed: python test_respond.py"""
import json
import os
import tempfile

import zt_respond as zr

# keep test state and incidents out of the real logs/
tmp = tempfile.mkdtemp()
zr.LOGS, zr.STATE, zr.INCIDENTS = tmp, os.path.join(tmp, "s.json"), os.path.join(tmp, "i.jsonl")


class FakeEngine(zr.ResponseEngine):
    """Records the commands instead of sending them over SSH."""

    def __init__(self):
        super().__init__(zabbix=False)
        self.sent = []

    def push(self, switch, commands):
        self.sent.append((switch, commands))
        return ""


# ---- 1. exact CLI commands ----
assert zr.NetworkActions.block_ip("10.10.30.50", 71) == ["ip access-list ZT_POLICY", "71 deny ip host 10.10.30.50 any"]
assert zr.NetworkActions.unblock_ip(71) == ["ip access-list ZT_POLICY", "no 71"]
assert all(50 < s < 80 for s in zr.BLOCK_SEQS)
print("PASS block/unblock commands; reserved lines sit after the guest rules and before permit 80")

# ---- 2. block records an incident, a second block of the same IP does nothing ----
e = FakeEngine()
a = e.block("10.10.30.50", attack="dos", reason="model", score=0.12)
assert a["action"] == "BLOCKED 10.10.30.50" and a["host"] == "guest-pc" and a["reason"] == "model"
assert e.block("10.10.30.50") is None and len(e.sent) == 1
inc = [json.loads(l) for l in open(zr.INCIDENTS)]
assert len(inc) == 1 and inc[0]["attack"] == "dos" and "response_ms" in inc[0]
print("PASS block logged once; repeated block of the same host ignored")

# ---- 3. each blocked host gets its own line; unblock frees it ----
e.block("10.10.20.50")
assert e.state["blocked"] == {"10.10.30.50": 71, "10.10.20.50": 72}
assert e.unblock("10.10.30.50") and e.sent[-1] == ("core", ["ip access-list ZT_POLICY", "no 71"])
e.block("10.10.10.50")
assert e.state["blocked"]["10.10.10.50"] == 71
assert not e.unblock("10.10.99.99")
print("PASS separate ACL line per host, lines reused after unblock")

# ---- 4. state survives a restart of the engine ----
e2 = FakeEngine()
assert e2.state["blocked"] == {"10.10.20.50": 72, "10.10.10.50": 71}
print("PASS state persisted between runs")

# ---- 5. infrastructure can never be blocked ----
for ip in ("10.10.10.5", "10.10.10.20", "10.10.10.11", "10.10.30.1"):
    try:
        e2.block(ip)
        raise AssertionError(ip)
    except SystemExit as ex:
        assert "refusing" in str(ex)
print("PASS RADIUS, SIEM, switch and gateways protected from blocking")

# ---- 6. alert-only changes nothing on the network ----
n = len(e2.sent)
r = e2.alert_only("10.10.20.50", "offhours", reason="model")
assert r["action"] == "ALERT ONLY" and len(e2.sent) == n
print("PASS alert-only: incident logged, no commands sent")
print("\nALL TESTS PASSED")
