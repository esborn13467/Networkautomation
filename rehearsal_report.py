#!/usr/bin/env python3
"""Summarise a rehearsal folder (see rehearsal.sh): actions and timings from the incident
log, lowest free memory, and what Zabbix received during the run (via its API).
Writes summary.json, including a paragraph for Chapter 5, and prints the summary."""
import json
import os
import sys

import zbx_setup as zs

out = sys.argv[1]
start = int(open(os.path.join(out, "start_epoch")).read())
inc = [json.loads(l) for l in open(os.path.join(out, "incidents.jsonl"))]
mem = [int(l.split()[1]) for l in open(os.path.join(out, "memory.log")) if len(l.split()) == 2]

first = {}
for i in inc:
    if "already" not in i["attack"] and i["attack"] not in first:
        first[i["attack"]] = i
expected = {"dos": "BLOCKED", "portscan": "QUARANTINED", "bruteforce": "QUARANTINED",
            "insider": "DISABLED", "offhours": "ALERT ONLY"}
ok = {a: a in first and first[a]["action"].startswith(v) for a, v in expected.items()}
false_alerts = [i for i in inc if i["attack"] == "unclassified"]
drastic_mistakes = [i for i in inc if i["attack"] not in expected and "already" not in i["attack"]
                    and i["action"] != "ALERT ONLY"]

zs.login()
pcs = ["zt-admin-pc", "zt-staff-pc", "zt-guest-pc"]
hosts = {h["hostid"]: h["host"] for h in zs.api("host.get", {"filter": {"host": pcs}, "output": ["host"]})}
scores = zs.api("item.get", {"hostids": list(hosts), "filter": {"key_": "zt.anomaly.score"}, "output": ["itemid"]})
nscores = sum(len(zs.api("history.get", {"itemids": [s["itemid"]], "history": 0, "time_from": start,
                                         "output": "extend"})) for s in scores)
actions = zs.api("item.get", {"hostids": list(hosts), "filter": {"key_": "zt.action"}, "output": ["itemid"]})
nactions = sum(len(zs.api("history.get", {"itemids": [a["itemid"]], "history": 4, "time_from": start,
                                          "output": "extend"})) for a in actions)
problems = zs.api("event.get", {"time_from": start, "source": 0, "object": 0, "value": 1,
                                "search": {"name": "Security alert"}, "output": ["name"]})

s = {
    "attacks_answered_correctly": sum(ok.values()), "per_attack": {a: (first[a]["action"], first[a].get("response_ms"))
                                                                   if a in first else None for a in expected},
    "false_alerts_alert_only": len(false_alerts), "wrong_drastic_actions": len(drastic_mistakes),
    "min_free_mb": min(mem) if mem else None, "zabbix_scores": nscores, "zabbix_actions": nactions,
    "zabbix_security_problems": len(problems),
}
times = [first[a]["response_ms"] / 1000 for a in expected if a in first]
s["paragraph"] = (
    f"A final rehearsal of the full demonstration repeated the end-to-end test with Zabbix and the push loop running. "
    f"{s['attacks_answered_correctly']} of the 5 attacks were answered automatically with the expected action, "
    + (f"{min(times):.1f} to {max(times):.1f} seconds after the window closed, " if times else "")
    + f"and Zabbix received {nscores} anomaly scores, {nactions} response actions and {len(problems)} security-alert "
    f"problems during the run. "
    + (f"{len(false_alerts)} alert-only false alarm{'s' if len(false_alerts) != 1 else ''} occurred and no user was "
       f"blocked, quarantined or disabled by mistake. " if not drastic_mistakes else
       f"{len(drastic_mistakes)} drastic action(s) were taken by mistake. ")
    + (f"The lowest free memory during the run was {min(mem)} MB." if mem else ""))
json.dump(s, open(os.path.join(out, "summary.json"), "w"), indent=2)
print(json.dumps({k: v for k, v in s.items() if k != "paragraph"}, indent=2))
print("\n" + s["paragraph"])
