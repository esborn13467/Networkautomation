#!/usr/bin/env python3
"""
zt_pipeline.py - live detection and response pipeline (Phase 3, step 3F.5)

PipelineOrchestrator (Chapter 4 class diagram) runs on the host and, without gaps:
  1. streams the SPAN mirror from the SIEM (tcpdump writing pcap to stdout) and
     tails the RADIUS log for rejects
  2. every 10 s builds the 8 features per PC (zt_collector.build_rows)
  3. scores each PC with the hybrid detector (zt_model.detect) and pushes the
     scores to Zabbix
  4. for a flagged PC: classifies the attack (AlertBuilder.classify) and calls the
     response engine (block / quarantine / disable / alert)
  5. times everything: response_ms = end of the evidence window -> action applied

Clock: the model was trained on business-hours traffic, so by default every window
is treated as 12:00 (--hour 12). Off-hours behaviour is simulated per host with
`python zt_traffic.py attack --mode offhours`, which writes /tmp/zt_night.json;
use --real-clock to take the hour from the laptop clock instead.

Usage:
  python zt_pipeline.py                 # Ctrl+C to stop
  python zt_pipeline.py --no-response   # detect and alert only, change nothing
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime

import pandas as pd

import zt_collector as zc
from zt_model import AnomalyDetector, MODEL_PATH, detect
from zt_respond import ACTION_FOR, ENDPOINTS, AlertBuilder, NetworkActions, ResponseEngine

WINDOW = zc.WINDOW
GRACE = 1.0                     # wait this long after a window ends for late packets
NIGHT_FILE = "/tmp/zt_night.json"
PID_FILE = "/tmp/zt_pipeline.pid"
ALERT_REPEAT = 60               # same host + attack type alerted at most once a minute
PC_BY_MAC = {}                  # filled from the lab


def pc_for_ip(ip):
    """PC name for its normal or its own quarantine address (10.10.99.10 / .20 / .30)."""
    for pc, ep in ENDPOINTS.items():
        if ip in (ep["ip"], NetworkActions.quarantine_ip(ep["ip"])):
            return pc
    return None


def night_hosts():
    try:
        with open(NIGHT_FILE) as f:
            return {h for h, until in json.load(f).items() if until > time.time()}
    except (OSError, ValueError):
        return set()


class PipelineOrchestrator:
    def __init__(self, respond=True, hour=12, real_clock=False, verbose=True):
        if not os.path.exists(MODEL_PATH):
            sys.exit("No trained model. Run: python zt_model.py train")
        self.det = AnomalyDetector.load()
        self.engine = ResponseEngine() if respond else None
        self.respond, self.hour, self.real_clock, self.verbose = respond, hour, real_clock, verbose
        self.lock = threading.Lock()
        self.packets = defaultdict(list)    # window index -> packets
        self.rejects = []                   # (ts, mac)
        self.last_alert = {}
        self.mac_to_ip = {}
        self.t0 = None
        self.procs = []
        self.zbx_ok = True

    # ----- inputs -----
    def _stream_packets(self):
        p = subprocess.Popen(["docker", "exec", f"{zc.LAB}siem", "tcpdump", "-n", "-s", "128", "-i", "eth1",
                              "-U", "-w", "-", "ip"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.procs.append(p)
        for pkt in zc.iter_packets(p.stdout):
            if pkt[0] < self.t0:
                continue
            with self.lock:
                self.packets[int((pkt[0] - self.t0) // WINDOW)].append(pkt)

    def _tail_radius(self):
        p = subprocess.Popen(["docker", "exec", f"{zc.LAB}radius", "tail", "-n", "0", "-F", "/tmp/radius.log"],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        self.procs.append(p)
        parser = zc.RadiusRejectParser()
        for line in p.stdout:
            hit = parser.feed(line.rstrip("\n"))
            if hit:
                with self.lock:
                    self.rejects.append((time.time(), hit[0]))

    # ----- one window -----
    def features(self, w):
        with self.lock:
            pkts = self.packets.pop(w, [])
            lo, hi = self.t0 + w * WINDOW, self.t0 + (w + 1) * WINDOW
            rj = [r for r in self.rejects if lo <= r[0] < hi]
            self.rejects = [r for r in self.rejects if r[0] >= hi]
        hours = None if self.real_clock else (self.hour, self.hour)
        rows = [dict(r, window=w) for r in zc.build_rows(pkts, rj, self.mac_to_ip, self.t0, sim_hours=hours)
                if pc_for_ip(r["host_ip"])]
        night = night_hosts()
        for r in rows:
            if pc_for_ip(r["host_ip"]) in night:
                r["off_hours"] = 1
        return pd.DataFrame(rows)

    def push_scores(self, df):
        if not self.zbx_ok:
            return
        try:
            import zt_zbx_push as zbx
            zbx.send([(f"zt-{pc_for_ip(r.host_ip)}", "zt.anomaly.score", round(float(r.score), 4))
                      for r in df.itertuples()])
        except Exception as e:
            self.zbx_ok = False
            print(f"   (Zabbix unreachable, scores not pushed: {e})")

    def handle(self, row, window_end):
        pc = pc_for_ip(row["host_ip"])
        attack = AlertBuilder.classify(row)
        action = ACTION_FOR[attack]
        key = (pc, attack)
        if time.time() - self.last_alert.get(key, 0) < ALERT_REPEAT:
            return None
        self.last_alert[key] = time.time()
        args = dict(attack=attack, reason=row["reason"], score=row["score"],
                    window_start=row["window_start"], t_detect=window_end)
        ip = ENDPOINTS[pc]["ip"]
        if not self.respond:
            return {"action": f"WOULD {action.upper()} {pc}", "attack": attack}
        done = self.engine.contained(pc)
        if done:                            # already acted on: log the sighting, change nothing
            return self.engine.alert_only(ip, **dict(args, attack=f"{attack} (already {done})"))
        if action == "block":
            res = self.engine.block(ip, **args)
        elif action == "quarantine":
            res = self.engine.quarantine(pc, **args)
        elif action == "disable":
            res = self.engine.disable(pc, **args)
        else:
            res = self.engine.alert_only(ip, **args)
        self.mac_to_ip = zc.learn_endpoints()   # quarantine changes the PC's address
        return res

    def process(self, w):
        window_end = self.t0 + (w + 1) * WINDOW
        df = self.features(w)
        stamp = datetime.fromtimestamp(self.t0 + w * WINDOW).strftime("%H:%M:%S")
        if df.empty:
            print(f"{stamp}  (no traffic)")
            return
        df = df.join(detect(self.det, df))
        self.push_scores(df)
        parts = []
        for r in df.sort_values("host_ip").itertuples():
            pc = pc_for_ip(r.host_ip)
            mark = f"  << FLAGGED ({r.reason})" if r.flag else ""
            parts.append(f"{pc} {r.score:+.3f}{mark}")
        print(f"{stamp}  " + " | ".join(parts), flush=True)
        for _, row in df[df["flag"]].iterrows():
            try:
                res = self.handle(row, window_end)
            except Exception as e:          # a failed response must never stop detection
                pc = pc_for_ip(row["host_ip"])
                print(f"   !! {pc}: RESPONSE FAILED ({type(e).__name__}: {e})", flush=True)
                if self.engine:
                    try:
                        self.engine.record(AlertBuilder.build(row["host_ip"], AlertBuilder.classify(row),
                                                              "RESPONSE FAILED", str(e), row["reason"],
                                                              row["score"], row["window_start"]))
                    except Exception:
                        pass
                continue
            if res:
                ms = res.get("response_ms")
                timing = f" in {ms / 1000:.1f} s after the window closed" if ms else ""
                print(f"   !! {pc_for_ip(row['host_ip'])}: {res['attack']} -> {res['action']}{timing}", flush=True)

    # ----- main loop -----
    @staticmethod
    def claim_single_instance():
        """Two pipelines would both respond to every attack: allow only one."""
        try:
            with open(PID_FILE) as f:
                other = int(f.read().strip())
            os.kill(other, 0)                       # raises if that process is gone
            sys.exit(f"Another pipeline is already running (pid {other}). Stop it first: kill {other}")
        except (OSError, ValueError):
            pass
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

    def run(self):
        self.claim_single_instance()
        signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
        self.mac_to_ip = zc.learn_endpoints()
        if not self.mac_to_ip:
            sys.exit("Could not read the PCs from the lab. Is it running?")
        if self.engine:
            self.engine.session("core")
            self.engine.session("acc1")              # SSH ready before the first attack
        self.t0 = time.time()
        for target in (self._stream_packets, self._tail_radius):
            threading.Thread(target=target, daemon=True).start()
        mode = "detect + respond" if self.respond else "detect only (no response)"
        clock = "laptop clock" if self.real_clock else f"business hours ({self.hour}:00)"
        print(f"ZT pipeline running: {mode}; {len(self.mac_to_ip)} PCs; threshold {self.det.threshold:+.3f}; "
              f"clock {clock}. Ctrl+C to stop.\n", flush=True)
        w, refresh = 0, time.time()
        try:
            while True:
                time.sleep(max(0.0, self.t0 + (w + 1) * WINDOW + GRACE - time.time()))
                self.process(w)
                w += 1
                if time.time() - refresh > 60:
                    self.mac_to_ip, refresh = zc.learn_endpoints(), time.time()
        except KeyboardInterrupt:
            print("\nstopping")
        finally:
            for p in self.procs:
                p.terminate()
            subprocess.run(["docker", "exec", f"{zc.LAB}siem", "pkill", "tcpdump"], capture_output=True)
            if self.engine:
                self.engine.close()
            try:
                os.remove(PID_FILE)
            except OSError:
                pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-response", action="store_true", help="detect and alert, change nothing")
    ap.add_argument("--hour", type=int, default=12, help="simulated hour for every window (default 12)")
    ap.add_argument("--real-clock", action="store_true", help="use the laptop clock for off_hours")
    a = ap.parse_args()
    PipelineOrchestrator(respond=not a.no_response, hour=a.hour, real_clock=a.real_clock).run()
