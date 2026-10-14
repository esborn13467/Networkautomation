#!/usr/bin/env python3
"""
zt_respond.py - automated response engine (Phase 3, step 3F)

Classes follow the Chapter 4 class diagram:
  AlertBuilder    classifies a flagged window and builds the alert record
  NetworkActions  produces the exact CLI commands for each action (pure, unit-tested)
  ResponseEngine  applies actions over SSH (Netmiko), remembers what it has already
                  done so a host is not acted on twice, logs every incident and
                  pushes alerts, actions and timings to Zabbix

Actions (Chapter 4 activity diagram):
  block       deny every packet from the source IP: a line in ZT_POLICY on the core,
              above the final permit (sequence numbers 71-79 are reserved for this)
  quarantine  identity-based, as Cisco ISE does it: a RADIUS rule sends the user to
              VLAN 99, the access port is bounced so the PC logs in again (~5 s), and
              the PC is re-addressed into 10.10.99.0/24 (stand-in for DHCP, exactly as
              lab-up.sh addresses the PCs). ZT_POLICY lines 20-40 then allow it to reach
              only RADIUS (udp 1812) and the SIEM.
  disable     the account is rejected by RADIUS and the port is bounced, so the PC
              fails 802.1X and gets no network at all
  alert       no access change; an analyst decides

RADIUS rules live in /etc/freeradius/3.0/zt_dynamic inside the radius container,
included at the top of radius/users. FreeRADIUS reloads on SIGHUP only when the
main users file changed, so the engine touches it before each reload.

Usage:
  python zt_respond.py block 10.10.30.50
  python zt_respond.py unblock 10.10.30.50
  python zt_respond.py quarantine guest-pc
  python zt_respond.py release guest-pc
  python zt_respond.py disable staff-pc
  python zt_respond.py enable staff-pc
  python zt_respond.py status
  python zt_respond.py reset          # undo every action taken by the engine
"""
import argparse
import json
import os
import re
import subprocess
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(HERE, "logs")
STATE = os.path.join(LOGS, "response_state.json")
INCIDENTS = os.path.join(LOGS, "incidents.jsonl")

SWITCHES = {"core": "clab-zt-core", "acc1": "clab-zt-acc1"}
SWITCH_USER, SWITCH_PASS = "admin", "admin"            # lab only, as in apply_config.py
ACL = "ZT_POLICY"
BLOCK_SEQS = range(71, 80)                              # between the guest rules (50-70) and permit (80)
HOSTS = {"10.10.10.50": "admin-pc", "10.10.20.50": "staff-pc", "10.10.30.50": "guest-pc"}
# PC -> 802.1X user, access port on acc1, normal address and gateway
ENDPOINTS = {
    "admin-pc": {"user": "bob", "port": "Ethernet2", "ip": "10.10.10.50", "gw": "10.10.10.1"},
    "staff-pc": {"user": "alice", "port": "Ethernet3", "ip": "10.10.20.50", "gw": "10.10.20.1"},
    "guest-pc": {"user": "guest1", "port": "Ethernet4", "ip": "10.10.30.50", "gw": "10.10.30.1"},
}
QUARANTINE_VLAN, QUARANTINE_NET, QUARANTINE_GW = "99", "10.10.99", "10.10.99.1"
RADIUS_NODE = "clab-zt-radius"
RADIUS_DIR = "/etc/freeradius/3.0"
PROTECTED = {"10.10.10.5", "10.10.10.20", "10.10.10.11", "10.10.10.1", "10.10.20.1", "10.10.30.1", "10.10.99.1"}


class NetworkActions:
    """Exact CLI command lists. No I/O, so every command is unit-testable."""

    @staticmethod
    def block_ip(ip, seq):
        return [f"ip access-list {ACL}", f"{seq} deny ip host {ip} any"]

    @staticmethod
    def unblock_ip(seq):
        return [f"ip access-list {ACL}", f"no {seq}"]

    @staticmethod
    def bounce_port(port):
        """Link down/up: the PC's supplicant starts a fresh 802.1X login."""
        return [f"interface {port}", "shutdown", "no shutdown"]

    @staticmethod
    def radius_rules(rules):
        """zt_dynamic file content. rules: {user: 'quarantine' | 'disabled'}"""
        out = []
        for user, kind in sorted(rules.items()):
            if kind == "disabled":
                out.append(f'{user} Auth-Type := Reject\n\tReply-Message := "Account disabled by ZT response engine"\n')
            else:
                out.append(f'{user}\n\tTunnel-Type := VLAN, Tunnel-Medium-Type := IEEE-802, '
                           f'Tunnel-Private-Group-Id := "{QUARANTINE_VLAN}",\n\tFall-Through = Yes\n')
        return "\n".join(out)

    @staticmethod
    def quarantine_ip(normal_ip):
        """Same host number in the quarantine subnet: 10.10.30.50 -> 10.10.99.50"""
        return f"{QUARANTINE_NET}.{normal_ip.rsplit('.', 1)[1]}"


class AlertBuilder:
    """Turns a flagged window into a structured alert."""

    @staticmethod
    def build(host_ip, attack, action, detail="", reason="", score=None, window_start=""):
        return {
            "time": datetime.now().isoformat(timespec="seconds"),
            "host_ip": host_ip, "host": HOSTS.get(host_ip, host_ip),
            "attack": attack, "action": action, "reason": reason,
            "score": None if score is None else round(float(score), 4),
            "window_start": window_start, "detail": detail,
        }


class ResponseEngine:
    def __init__(self, zabbix=True):
        self.sessions = {}
        self.zabbix = zabbix
        os.makedirs(LOGS, exist_ok=True)
        self.state = self._load()

    # ----- plumbing -----
    def _load(self):
        try:
            with open(STATE) as f:
                st = json.load(f)
        except (OSError, ValueError):
            st = {}
        st.setdefault("blocked", {})
        st.setdefault("radius", {})
        return st

    def _save(self):
        with open(STATE, "w") as f:
            json.dump(self.state, f, indent=2)

    @staticmethod
    def _alive(conn):
        """Check the SSH transport only. Netmiko's is_alive() writes a NUL byte to the
        channel, which leaves the Arista CLI out of step: the next command then times out."""
        try:
            return conn.remote_conn.get_transport().is_active()
        except Exception:
            return False

    def session(self, switch):
        """One SSH session per switch, kept open so actions take ~0.1 s, not ~1 s."""
        conn = self.sessions.get(switch)
        if conn is None or not self._alive(conn):
            from netmiko import ConnectHandler
            conn = ConnectHandler(device_type="arista_eos", host=SWITCHES[switch],
                                  username=SWITCH_USER, password=SWITCH_PASS)
            conn.enable()
            self.sessions[switch] = conn
        return conn

    def push(self, switch, commands):
        out = self.session(switch).send_config_set(commands)
        if "% " in out:
            raise RuntimeError(f"{switch} rejected: {out}")
        return out

    # ----- RADIUS, ports and endpoints -----
    def apply_radius_rules(self):
        text = NetworkActions.radius_rules(self.state["radius"])
        subprocess.run(["docker", "exec", "-i", RADIUS_NODE, "sh", "-c", f"cat > {RADIUS_DIR}/zt_dynamic"],
                       input=text, text=True, check=True)
        subprocess.run(["docker", "exec", RADIUS_NODE, "sh", "-c",
                        f"touch {RADIUS_DIR}/mods-config/files/authorize; kill -HUP $(pgrep -o freeradius)"],
                       check=True)
        time.sleep(0.5)                                 # let FreeRADIUS finish the reload

    def bounce(self, port):
        self.push("acc1", NetworkActions.bounce_port(port))

    def readdress(self, pc, ip, gw):
        """Lab stand-in for a DHCP renew after the VLAN change (the lab has no DHCP)."""
        subprocess.run(["docker", "exec", f"clab-zt-{pc}", "sh", "-c",
                        f"ip addr flush dev eth1 scope global; ip addr add {ip}/24 dev eth1; "
                        f"ip route replace default via {gw}"], check=True)

    def port_state(self, port):
        """(state, vlan) of the 802.1X session on an acc1 port, e.g. ('SUCCESS', '99')."""
        out = self.session("acc1").send_command("show dot1x hosts")
        short = "Et" + port.replace("Ethernet", "")
        for line in out.splitlines():
            f = line.split()
            if f and f[0] == short:
                vlan = f[6] if len(f) > 6 and f[6].isdigit() else ""
                return f[4], vlan
        return "NONE", ""

    def wait_port(self, port, want, timeout=20):
        """Poll until want(state, vlan) holds; returns (ok, seconds)."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            st, vlan = self.port_state(port)
            if want(st, vlan):
                return True, time.time() - t0
            time.sleep(1)
        return False, time.time() - t0

    def record(self, alert, response_ms=None):
        if response_ms is not None:
            alert["response_ms"] = round(response_ms, 1)
        with open(INCIDENTS, "a") as f:
            f.write(json.dumps(alert) + "\n")
        if self.zabbix:
            try:
                import zt_zbx_push as zbx
                node = alert["host"]
                zbx.send_alert(node, f"{alert['attack']} -> {alert['action']} ({alert['reason'] or 'manual'})")
                zbx.send_action(node, alert["action"], alert.get("response_ms") or 0)
            except Exception as e:          # Zabbix down must never stop a response
                print("   (Zabbix not updated:", e, ")")
        return alert

    # ----- actions -----
    def block(self, ip, attack="manual", reason="", score=None, window_start="", t_detect=None):
        if ip in PROTECTED:
            raise SystemExit(f"refusing to block infrastructure address {ip}")
        if ip in self.state["blocked"]:
            return None                                 # already acted on: do nothing twice
        used = set(self.state["blocked"].values())
        seq = next((s for s in BLOCK_SEQS if s not in used), None)
        if seq is None:
            raise RuntimeError("no free block sequence numbers (71-79)")
        t0 = t_detect or time.time()
        self.push("core", NetworkActions.block_ip(ip, seq))
        ms = (time.time() - t0) * 1000
        self.state["blocked"][ip] = seq
        self._save()
        return self.record(AlertBuilder.build(ip, attack, f"BLOCKED {ip}", f"{ACL} seq {seq} on core",
                                              reason, score, window_start), ms)

    def unblock(self, ip):
        seq = self.state["blocked"].pop(ip, None)
        if seq is None:
            return False
        self.push("core", NetworkActions.unblock_ip(seq))
        self._save()
        return True

    def quarantine(self, pc, attack="manual", reason="", score=None, window_start="", t_detect=None):
        ep = ENDPOINTS[pc]
        if self.state["radius"].get(ep["user"]):
            return None                                 # already quarantined or disabled
        t0 = t_detect or time.time()
        self.state["radius"][ep["user"]] = "quarantine"
        self._save()
        self.apply_radius_rules()
        self.bounce(ep["port"])
        ms = (time.time() - t0) * 1000                  # action applied
        ok, secs = self.wait_port(ep["port"], lambda st, v: st == "SUCCESS" and v == QUARANTINE_VLAN)
        qip = NetworkActions.quarantine_ip(ep["ip"])
        self.readdress(pc, qip, QUARANTINE_GW)
        detail = (f"RADIUS sends {ep['user']} to VLAN {QUARANTINE_VLAN}; {ep['port']} bounced; "
                  f"{'in VLAN 99 after %.1f s' % secs if ok else 'VLAN 99 NOT confirmed'}; address {qip}")
        return self.record(AlertBuilder.build(ep["ip"], attack, f"QUARANTINED {pc}", detail,
                                              reason, score, window_start), ms)

    def disable(self, pc, attack="manual", reason="", score=None, window_start="", t_detect=None):
        ep = ENDPOINTS[pc]
        if self.state["radius"].get(ep["user"]) == "disabled":
            return None
        t0 = t_detect or time.time()
        self.state["radius"][ep["user"]] = "disabled"
        self._save()
        self.apply_radius_rules()
        self.bounce(ep["port"])
        ms = (time.time() - t0) * 1000
        ok, secs = self.wait_port(ep["port"], lambda st, v: st != "SUCCESS")
        detail = (f"RADIUS rejects {ep['user']}; {ep['port']} bounced; "
                  f"{'port unauthorised after %.1f s' % secs if ok else 'port state NOT confirmed'}")
        return self.record(AlertBuilder.build(ep["ip"], attack, f"DISABLED account {ep['user']}", detail,
                                              reason, score, window_start), ms)

    def restore(self, pc):
        """Undo quarantine or disable: remove the rule, log the PC in again, normal address."""
        ep = ENDPOINTS[pc]
        kind = self.state["radius"].pop(ep["user"], None)
        if kind is None:
            return False
        self._save()
        self.apply_radius_rules()
        if kind == "disabled":
            # after a failed login the port waits out a 60 s quiet period: restart the supplicant
            subprocess.run(["docker", "exec", f"clab-zt-{pc}", "pkill", "wpa_supplicant"])
        self.bounce(ep["port"])
        if kind == "disabled":
            subprocess.run(["docker", "exec", f"clab-zt-{pc}", "wpa_supplicant", "-D", "wired", "-i", "eth1",
                            "-c", "/etc/wpa.conf", "-B", "-f", "/tmp/wpa.log"], capture_output=True)
        ok, secs = self.wait_port(ep["port"], lambda st, v: st == "SUCCESS" and v not in ("", QUARANTINE_VLAN), 40)
        self.readdress(pc, ep["ip"], ep["gw"])
        print(f"{pc}: {'back in its VLAN after %.1f s' % secs if ok else 'NOT confirmed, check show dot1x hosts'}")
        return ok

    def alert_only(self, ip, attack, reason="", score=None, window_start="", t_detect=None):
        ms = (time.time() - (t_detect or time.time())) * 1000
        return self.record(AlertBuilder.build(ip, attack, "ALERT ONLY", "no access change; analyst to review",
                                              reason, score, window_start), ms)

    def reset(self):
        """Undo everything the engine did (used between demo steps)."""
        for ip in list(self.state["blocked"]):
            self.unblock(ip)
            print("unblocked", ip)
        users = {ep["user"]: pc for pc, ep in ENDPOINTS.items()}
        for user in list(self.state["radius"]):
            self.restore(users[user])
        # also clear stray lines in the reserved range, e.g. after a crash
        acl = self.session("core").send_command(f"show ip access-lists {ACL}")
        for seq in BLOCK_SEQS:
            if f"\n        {seq} " in acl:
                self.push("core", NetworkActions.unblock_ip(seq))
                print("removed stray line", seq)

    def status(self):
        acl = self.session("core").send_command(f"show ip access-lists {ACL}")
        return self.state, acl

    def close(self):
        for c in self.sessions.values():
            c.disconnect()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["block", "unblock", "quarantine", "release", "disable", "enable", "status", "reset"])
    ap.add_argument("target", nargs="?")
    a = ap.parse_args()
    eng = ResponseEngine()
    try:
        if a.cmd == "block":
            r = eng.block(a.target)
            print(json.dumps(r, indent=2) if r else f"{a.target} is already blocked")
        elif a.cmd == "unblock":
            print("unblocked" if eng.unblock(a.target) else f"{a.target} was not blocked")
        elif a.cmd in ("quarantine", "disable"):
            r = getattr(eng, a.cmd)(a.target)
            print(json.dumps(r, indent=2) if r else f"{a.target} already has a RADIUS action")
        elif a.cmd in ("release", "enable"):
            eng.restore(a.target) or print(f"{a.target} had no RADIUS action")
        elif a.cmd == "reset":
            eng.reset()
            print("reset done")
        else:
            st, acl = eng.status()
            print(json.dumps(st, indent=2))
            print(acl)
    finally:
        eng.close()
