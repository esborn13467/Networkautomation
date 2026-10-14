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

    def apply_radius_rules(self):
        self.rules_text = zr.NetworkActions.radius_rules(self.state["radius"])

    def readdress(self, pc, ip, gw):
        self.addr = (pc, ip, gw)

    def wait_port(self, port, want, timeout=20):
        return True, 1.0

    def bounce(self, port):
        self.push("acc1", zr.NetworkActions.bounce_port(port))


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

# ---- 7. RADIUS rules: quarantine overrides the VLAN but keeps the password check; disable rejects ----
txt = zr.NetworkActions.radius_rules({"guest1": "quarantine", "alice": "disabled"})
assert 'Tunnel-Private-Group-Id := "99"' in txt and "Fall-Through = Yes" in txt
assert "alice Auth-Type := Reject" in txt and "Cleartext-Password" not in txt
assert zr.NetworkActions.radius_rules({}) == ""
assert zr.NetworkActions.bounce_port("Ethernet4") == ["interface Ethernet4", "shutdown", "no shutdown"]
assert [zr.NetworkActions.quarantine_ip(ip) for ip in ("10.10.10.50", "10.10.20.50", "10.10.30.50")] == ["10.10.99.10", "10.10.99.20", "10.10.99.30"]
print("PASS RADIUS rule text, port bounce commands, one unique quarantine address per PC")

# ---- 8. quarantine: rule written, port bounced, address moved, logged once ----
e3 = FakeEngine()
e3.state = {"blocked": {}, "radius": {}}
q = e3.quarantine("guest-pc", attack="portscan", reason="model")
assert q["action"] == "QUARANTINED guest-pc" and "in VLAN 99" in q["detail"]
assert 'guest1' in e3.rules_text and e3.sent[-1] == ("acc1", ["interface Ethernet4", "shutdown", "no shutdown"])
assert e3.addr == ("guest-pc", "10.10.99.30", "10.10.99.1")
assert e3.quarantine("guest-pc") is None
print("PASS quarantine: RADIUS rule, port bounce, 10.10.99.30, no double action")

# ---- 9. restore puts the PC back on its own address and clears the rule ----
assert e3.restore("guest-pc") and e3.state["radius"] == {} and e3.rules_text == ""
assert e3.addr == ("guest-pc", "10.10.30.50", "10.10.30.1")
assert not e3.restore("guest-pc")
d = e3.disable("staff-pc", attack="insider")
assert d["action"] == "DISABLED account alice" and e3.state["radius"] == {"alice": "disabled"}
print("PASS release restores address; disable rejects the account")
# state on disk at this point: staff and admin addresses blocked (test 3), alice disabled, guest free
assert e3.contained("staff-pc") == "blocked" and e3.contained("guest-pc") is None
e3.state["blocked"] = {}
e3._save()
assert e3.contained("staff-pc") == "disabled"
from zt_pipeline import pc_for_ip
assert [pc_for_ip(x) for x in ("10.10.99.10", "10.10.99.20", "10.10.99.30", "10.10.99.50", "10.10.30.50")] == \
    ["admin-pc", "staff-pc", "guest-pc", None, "guest-pc"]
print("PASS contained() reports engine actions; every quarantine address maps to exactly one PC")
print("\nALL TESTS PASSED")
