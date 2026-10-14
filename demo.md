# Panel Demonstration Script

**Project:** A Zero-Trust Network with Automated Threat Detection and Response using Isolation Forest
**Presenter:** Esborn Kihiu · **Length:** about 12 minutes · **Lab folder:** `~/Networkautomation/zt-project`

> **Status of this script.** Each step is marked:
> - ✅ **ready**: works today and has been run in the lab
> - 🧪 **to test**: commands written but not yet run in the lab
> - 🛠 **built later**: depends on a piece still being built (model, response engine, brute-force generator). The commands shown are the planned ones and will be finalised and rehearsed when that piece is done.
>
> Rehearse the whole script at least twice before the real demo, and **record a video of one full run** as a backup in case the laptop runs out of memory on the day.

---

## 0. The day before

| # | What | Command / action |
|---|---|---|
| 0.1 | Run all offline tests | `source venv/bin/activate && python test_collector.py && python test_traffic.py && python test_zbx_push.py` (each must end `ALL TESTS PASSED`) |
| 0.2 | Charge the laptop, close everything except a terminal | |
| 0.3 | Have the slides and the backup video on a USB stick | |
| 0.4 | Change the Zabbix password from the default if not done yet | Zabbix → User settings → Change password; then `export ZBX_PASSWORD=...` before running scripts |

## 1. Before the panel arrives (start 15 minutes early)

**Close the browser first.** The lab needs about 4.5 GB of free RAM to build.

```bash
cd ~/Networkautomation/zt-project
./lab-up.sh
```

Wait for the end of the output (about 5 minutes). You must see:

```
   PASS  guest -> web (DMZ)
   PASS  guest -> internet
   PASS  guest -> RADIUS
   PASS  guest -> staff PC
   PASS  staff -> RADIUS
   PASS  web (DMZ) -> RADIUS
```

and three `SUCCESS` lines from `show dot1x hosts`. If any line says `FAIL`, run `./lab-down.sh` and `./lab-up.sh` again.

Then set up the screen:

1. Open the browser at **http://localhost:8080**, log in, go to **Dashboards → ZT Lab overview**.
2. Open **Terminal A** (commands you type during the demo) and **Terminal B** (the detection pipeline output).
3. In both terminals:
   ```bash
   cd ~/Networkautomation/zt-project && source venv/bin/activate
   ```
4. Clear old test alerts: Zabbix → Monitoring → Problems → select any "TEST" problems → Mass update → Close problem.

---

## 2. The network — 1 minute ✅

**Say:** "This is a working Zero Trust enterprise network running real Arista switch software in containers. There are two switches, a firewall, a DMZ web server, a RADIUS server, a SIEM collector and three users: an admin, a staff member and a guest."

Show the topology (Terminal A):

```bash
sudo containerlab inspect -t zt-dev.clab.yml
```

Optional diagram in the browser (Ctrl+C to stop it afterwards):

```bash
sudo containerlab graph -t zt-dev.clab.yml
# open http://localhost:50080
```

Then switch to Zabbix, page **Network health**: every node is monitored, and every node pushes its own traffic, CPU and memory every 30 seconds.

**Point at:** Host availability (all hosts available) and the traffic graphs.

---

## 3. Zero Trust access control — 3 minutes ✅

### 3a. Every user authenticates; RADIUS decides their segment

```bash
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"
```

**Expected:** bob → VLAN 10 ADMIN, alice → VLAN 20 STAFF, guest1 → VLAN 30 GUEST, all `SUCCESS`.

**Say:** "No port forwards traffic until the user proves who they are with 802.1X. The VLAN is not configured on the port. FreeRADIUS assigns it from the user's identity. That is identity-based access, never trust, always verify."

### 3b. A wrong password gets nothing ✅ (tested 14 Oct; takes about 90 seconds including recovery)

Log guest-pc in with a wrong password:

```bash
docker exec clab-zt-guest-pc pkill wpa_supplicant
docker exec clab-zt-guest-pc sh -c "sed 's/password=.*/password=\"WRONG\"/' /etc/wpa.conf > /tmp/bad.conf && wpa_supplicant -D wired -i eth1 -c /tmp/bad.conf -B -f /tmp/bad.log"
sleep 10
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"
docker exec clab-zt-guest-pc ping -c 2 -W 2 10.10.30.1
```

**Expected:** Et4 shows `FAILED` with no VLAN, and the ping to its own gateway gets 100% packet loss.

Show the RADIUS server's decision:

```bash
docker exec clab-zt-radius grep -c "Sent Access-Reject" /tmp/radius.log
```

Restore guest-pc (the port has a 60-second quiet period after a failure, so it is bounced):

```bash
docker exec clab-zt-guest-pc pkill wpa_supplicant
python apply_config.py clab-zt-acc1 bounce4.cfg > /dev/null
docker exec clab-zt-guest-pc wpa_supplicant -D wired -i eth1 -c /etc/wpa.conf -B -f /tmp/wpa.log
sleep 25
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"
```

**Expected:** guest1 back to `SUCCESS` on VLAN 30.

### 3c. Least privilege between segments

```bash
docker exec clab-zt-guest-pc curl -s -m 4 http://10.10.40.10          # guest -> DMZ web: allowed
docker exec clab-zt-guest-pc ping -c 2 -W 2 10.10.10.5                 # guest -> RADIUS: blocked
docker exec clab-zt-guest-pc ping -c 2 -W 2 10.10.20.50                # guest -> staff PC: blocked
docker exec clab-zt-staff-pc ping -c 2 -W 2 10.10.10.5                 # staff -> RADIUS: allowed
docker exec clab-zt-web ping -c 2 -W 2 10.10.10.5                      # DMZ -> internal: blocked
```

**Expected:** `ZT-DMZ-web-server`, then 100% loss, 100% loss, replies, 100% loss.

Prove the switch and the firewall did the blocking:

```bash
docker exec clab-zt-core Cli -p 15 -c "show ip access-lists ZT_POLICY"
docker exec clab-zt-edge iptables -L FORWARD -n -v
```

**Point at:** the `match N packets` counters on lines 50 and 60 (guest → admin, guest → staff) increasing, and the edge DROP counters.

**Say:** "Guests can use the public web server in the DMZ but cannot see a single internal system. A quarantined device, which we will see shortly, may only talk to RADIUS and the SIEM (lines 20 to 40)."

---

## 4. Normal operation — 1 minute 🛠 (built later: pipeline + background traffic command)

Terminal B, start the detection pipeline. It captures the mirrored traffic, computes eight features per host every 10 seconds, scores them with the Isolation Forest, and responds:

```bash
python zt_pipeline.py
```

Terminal A, start normal background traffic on all three PCs for 15 minutes (✅ command ready):

```bash
python zt_traffic.py background --seconds 900
```

Zabbix page **Threat detection and response**:

**Point at:** the three anomaly-score lines sitting low and flat below the red threshold line; no security alerts.

**Say:** "The model learned normal behaviour only from normal traffic. It has never seen an attack. Legitimate users keep working and nothing is flagged."

---

## 5. Attack 1: Denial of service → block IP — 2 minutes 🛠

Terminal A:

```bash
python zt_traffic.py attack --mode dos --seconds 40
```

**What the panel sees, in order:**

1. Network health page: guest-pc's packets per second jump from tens to thousands.
2. Detection page: guest-pc's anomaly score crosses the red line within one or two 10-second windows.
3. Terminal B: `ANOMALY guest-pc ... classified DoS -> BLOCK 10.10.30.50`.
4. Security alerts: a new problem for zt-guest-pc; *Last response action* shows `BLOCKED 10.10.30.50`; *Detection-to-action time* shows the milliseconds.

Prove the block is real:

```bash
docker exec clab-zt-core Cli -p 15 -c "show ip access-lists ZT_POLICY"   # new deny line for 10.10.30.50 with rising counters
docker exec clab-zt-guest-pc curl -s -m 4 http://10.10.40.10 || echo BLOCKED
```

Reset before the next attack:

```bash
python zt_respond.py reset
```

---

## 6. Attack 2: Port scan or brute force → quarantine — 2 minutes 🛠

Port scan from guest-pc:

```bash
python zt_traffic.py attack --mode portscan --seconds 40
```

or brute force against RADIUS (✅ attack command ready; about 5 wrong passwords per second for guest-pc's port):

```bash
python zt_traffic.py attack --mode bruteforce --seconds 40
docker exec clab-zt-radius grep -c "Sent Access-Reject" /tmp/radius.log   # rejects climbing
```

**Expected:** score crosses the line → classified `portscan` / `bruteforce` → **QUARANTINE**.

Prove the quarantine:

```bash
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"          # host no longer in its VLAN
docker exec clab-zt-core Cli -p 15 -c "show ip access-lists ZT_POLICY"   # lines 20-40 counting the quarantined traffic
```

**Say:** "The device is isolated automatically. It can still reach RADIUS to re-authenticate and the SIEM for investigation, and nothing else. No administrator had to be awake."

Reset:

```bash
python zt_respond.py reset
```

---

## 7. Attack 3: Off-hours session → alert only — 1 minute 🛠

```bash
python zt_traffic.py attack --mode offhours --seconds 40
```

**Expected:** staff-pc flagged, classified `off-hours`, action `ALERT ONLY`. Access is not changed.

**Say:** "Not every anomaly should cut someone off. A staff member working at 2 a.m. is unusual but may be legitimate, so, as in the Chapter 4 activity diagram, the system raises an alert and leaves the decision to an analyst."

---

## 8. Results — 2 minutes 🛠 (slides)

Slides generated from the datasets (Chapter 5):

| Attack | Detection rate | False positive rate | Mean response time |
|---|---|---|---|
| DoS | from evaluation | from evaluation | from evaluation |
| Port scan | | | |
| Brute force | | | |
| Insider | | | |
| Off-hours | | | |

Plus: the anomaly-score histogram (normal vs attack) and the confusion matrix.

**Say:** "Trained only on normal traffic, tested on separate runs the model had never seen, including weak attacks at five intensities."

---

## 9. After the demo

```bash
./lab-down.sh
```

## If something goes wrong

| Problem | Fix |
|---|---|
| Laptop freezes / very slow | Play the backup video. Afterwards: `./lab-down.sh`, close the browser, `./lab-up.sh` |
| A self-test says FAIL | `./lab-down.sh && ./lab-up.sh` |
| A PC shows FAILED in `show dot1x hosts` | Repeat the restore commands at the end of step 3b for that PC (bounce its port: Et2 admin, Et3 staff, Et4 guest) |
| Zabbix page empty | `docker start zbx-db zbx-server zbx-web`, wait 30 s; check `tail /tmp/zt_zbx_push.log` |
| Graphs flat although traffic is running | Push loop not running: `nohup python zt_zbx_push.py run > /tmp/zt_zbx_push.log 2>&1 &` |
| Response did not trigger | Show the pipeline output in Terminal B (score and threshold), then `python zt_respond.py reset` and repeat the attack |

## Likely panel questions

- **Why not Packet Tracer / Cisco ISE?** Packet Tracer has no real SSH from the host, so the Python pipeline would have nothing to connect to. cEOS is real switch software; FreeRADIUS implements the same AAA and dynamic VLAN principles as ISE.
- **Why Isolation Forest?** It is unsupervised: it learns only from normal traffic, so it can flag attacks it has never seen, and it is fast enough to score every 10 seconds.
- **How do you avoid false alarms?** The threshold was tuned on a separate normal run; off-hours anomalies only alert; windows that an attack only partly covers were excluded from evaluation so the metrics are honest.
- **Is the traffic real?** Yes, real packets through real switch software, captured from a SPAN mirror port, as in an enterprise SOC. The traffic itself is generated, as stated in the scope (Chapter 1.4).
- **What are the limitations?** Simulated users, one access switch, 8 GB RAM, the cEOS-lab software data plane (no ACLs on SVIs), and the off-hours flag simulated rather than waiting for night-time.
