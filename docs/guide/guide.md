# Part A: How My Project Works

This part explains every piece of the system in plain words. Each section has the same three parts: **the idea**, **where it lives in your lab**, and **a command to see it yourself**. Run the commands from the project folder after starting the lab (Exercise 1 in Part B).

## A1. The big picture

Think of the network as an office building:

- **The door with a badge reader** is 802.1X. Nobody gets in without showing who they are.
- **HR's staff list** is the RADIUS server. It decides who you are and which floor you may go to.
- **The floors** are VLANs: one for admins, one for staff, one for guests, and an isolation room (quarantine).
- **The doors between floors** are the ZT_POLICY rules on the core switch.
- **Reception** is the DMZ: visitors can reach the public web server there, nothing else.
- **The CCTV room** is the SIEM: it gets a copy of everything happening on the user floors.
- **The analyst watching CCTV** is the Isolation Forest: it notices behaviour that is unusual.
- **The security guard** is the response engine: it acts on what the analyst reports.
- **The control-room screens** are Zabbix.

Zero Trust means the building never assumes someone is safe because they are already inside. Every login is checked, every floor is separated, and behaviour keeps being watched after login.

## A2. The lab: containers instead of real hardware

Every device is a **container**: a small, isolated Linux system running on your laptop. **Containerlab** reads one file, `zt-dev.clab.yml`, which lists every device and every cable, and builds the whole network from it. The two switches run **Arista cEOS**, the real software Arista puts on its physical switches.

| Device | Container name | Job |
|---|---|---|
| core | clab-zt-core | Routes between VLANs, holds the ZT_POLICY rules |
| acc1 | clab-zt-acc1 | Access switch: the ports where PCs plug in, does 802.1X |
| edge | clab-zt-edge | Firewall between the inside, the DMZ and the internet |
| web | clab-zt-web | Public web server in the DMZ |
| radius | clab-zt-radius | FreeRADIUS: checks logins, assigns VLANs |
| siem | clab-zt-siem | Receives a copy of all user traffic |
| admin-pc, staff-pc, guest-pc | clab-zt-admin-pc ... | The three users' computers |
| new-pc | clab-zt-new-pc | A spare desk for the "add a new PC" exercise |

See it:

```
docker ps --format '{{.Names}}  {{.Status}}'
```

Two command patterns appear everywhere in this guide:

- `docker exec clab-zt-guest-pc <command>` runs a command **inside** a container, as if you were sitting at that PC.
- `docker exec clab-zt-acc1 Cli -p 15 -c "<command>"` runs a command on a **switch's own command line**, the same commands a network engineer types on a real Arista switch.

## A3. 802.1X and RADIUS: proving who you are

**The idea.** When a PC is plugged into a switch port, the port stays closed. The PC (the **supplicant**, here `wpa_supplicant`) sends a username and password. The switch (the **authenticator**) passes them to the RADIUS server (the **authentication server**). If RADIUS says yes, it also says **which VLAN** the user belongs to, and the switch opens the port into that VLAN. If RADIUS says no, the port stays closed.

**Where it lives.**

- `radius/users`: the user list. Each user has a password and a VLAN number (bob 10, alice 20, guest1 30).
- `client/admin-pc.conf`, `staff-pc.conf`, `guest-pc.conf`: each PC's login details.
- `acc1.cfg`: the switch side (`dot1x pae authenticator`, `dot1x port-control auto` on the user ports).

See it:

```
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"
cat radius/users
```

> The VLAN follows the **person**, not the port. If bob plugged into guest-pc's port, he would still land in VLAN 10.

## A4. VLANs: separate floors

| VLAN | Name | Network | Who |
|---|---|---|---|
| 10 | ADMIN | 10.10.10.0/24 | bob (admin-pc .50), RADIUS .5, SIEM .20 |
| 20 | STAFF | 10.10.20.0/24 | alice (staff-pc .50) |
| 30 | GUEST | 10.10.30.0/24 | guest1 (guest-pc .50) |
| 99 | QUARANTINE | 10.10.99.0/24 | unauthenticated or isolated devices |
| DMZ | - | 10.10.40.0/24 | the public web server .10 |

Each VLAN is its own network. Traffic between them must pass through the core switch, which is where the rules are applied.

See it:

```
docker exec clab-zt-acc1 Cli -p 15 -c "show interfaces status"
docker exec clab-zt-guest-pc ip -4 addr show eth1
```

## A5. ZT_POLICY: the doors between floors

**The idea.** One list of rules on the core switch decides which floor may talk to which. It is checked from the top; the first matching line wins. Each line keeps a **counter** of how many packets it matched, which is your proof that the rule is working.

| Line | Rule | Meaning |
|---|---|---|
| 10 | permit DHCP | address requests always allowed |
| 20 | permit quarantine to RADIUS port 1812 | an isolated PC may log in again |
| 30 | permit quarantine to SIEM | an isolated PC may be investigated |
| 40 | deny quarantine to anything | nothing else for quarantine |
| 50 | deny guest to admin | |
| 60 | deny guest to staff | |
| 70 | deny guest to quarantine | |
| 71-79 | (empty) | reserved for automatic blocks by the response engine |
| 80 | permit everything else | |

See it:

```
docker exec clab-zt-core Cli -p 15 -c "show ip access-lists ZT_POLICY"
```

## A6. The edge firewall and the DMZ

**The idea.** The edge is a Linux firewall (`iptables`). Inside users may reach the internet and the DMZ web server on port 80 only. The DMZ may never start a connection inward, so even if the web server were hacked, it could not reach the inside.

See it:

```
docker exec clab-zt-edge iptables -L FORWARD -n -v
```

## A7. The mirror port and the SIEM

**The idea.** The access switch copies every packet from the three user ports to port 6, where the SIEM is connected. This is called **SPAN** or port mirroring. The SIEM only listens; it never sends on that port.

See it:

```
docker exec clab-zt-acc1 Cli -p 15 -c "show monitor session"
```

## A8. The eight features: what the camera writes down

Every 10 seconds, for each PC, the collector (`zt_collector.py`) turns the copied packets into eight numbers:

| Feature | Plain meaning | Goes up during |
|---|---|---|
| packet_count | how many packets | DoS, data theft |
| avg_packet_size | average packet size | data theft (big packets) |
| bytes_transferred | total data moved | data theft |
| connection_duration | how long connections last | |
| failed_logins | wrong-password attempts (from the RADIUS log) | brute force |
| unique_dst_ports | how many different ports it tried | port scan |
| requests_per_min | new connections per minute | DoS, port scan |
| off_hours | 1 if outside working hours | off-hours use |

## A9. Isolation Forest: the analyst

**The idea.** Imagine playing "20 questions" with a list of windows: "more than 500 packets?", "more than 3 ports?". Normal windows look alike, so it takes many questions to single one out. An unusual window gets singled out in very few questions. **Fewer questions means more suspicious**, and that is the anomaly score. Above the threshold (-0.019) the window is **flagged**.

The model was trained on traffic in which attacks were rare, **without ever being told which windows were attacks**. One extra rule catches slow password guessing: **5 or more failed logins in 10 seconds** is always flagged. Together this is the **hybrid detector**: 100% of attack windows detected in testing, 1.1% false alarms.

Where it lives: `zt_model.py` (the model), `models/zt_iforest.joblib` (the trained model), `results/` (the test results and charts).

## A10. The response engine: the security guard

When a window is flagged, `zt_respond.py` first decides which attack it looks like, then acts:

| Attack | Recognised by | Action | How it is done |
|---|---|---|---|
| DoS | 300+ connections per minute | **Block IP** | adds a deny line (71-79) to ZT_POLICY |
| Port scan | 10+ different ports | **Quarantine** | RADIUS moves the user to VLAN 99, port bounced |
| Brute force | 5+ failed logins | **Quarantine** | same |
| Insider data theft | 5 MB+ in 10 seconds | **Disable account** | RADIUS rejects the user, port bounced |
| Off-hours or unclear | off-hours flag, or nothing else matches | **Alert only** | nobody is cut off; a person decides |

**Bouncing a port** means switching it off and on. The PC then logs in again, and RADIUS answers with the new decision (VLAN 99, or reject).

## A11. The pipeline: putting it all together

`zt_pipeline.py` runs everything in a loop: copy packets, build the eight features every 10 seconds, score each PC, push the scores to Zabbix, and call the response engine for a flagged PC. It prints one line per window, for example:

```
20:56:26  staff-pc -0.184 | guest-pc +0.034  << FLAGGED (model)
   !! guest-pc: dos -> BLOCKED 10.10.30.50 in 1.1 s after the window closed
```

Negative scores are normal; positive or near zero is suspicious.

## A12. Zabbix: the control room

Zabbix (http://localhost:8080, user **Admin**, password **zabbix**) shows two dashboard pages under **Dashboards > ZT Lab overview**:

- **Network health**: every device up or down, traffic, CPU and memory.
- **Threat detection and response**: each PC's anomaly score against the red threshold line, the security alerts, the last action and how long it took.

Every lab device sends its own numbers to Zabbix every 30 seconds (`zt_zbx_push.py`); the pipeline sends scores and alerts every 10 seconds.

## A13. Where everything lives

| File | What it is |
|---|---|
| zt-dev.clab.yml | the whole network: devices and cables |
| core.cfg, acc1.cfg, policy.cfg | switch configurations |
| edge-fw.sh | edge firewall rules |
| radius/users, radius/clients.conf | RADIUS users and allowed switches |
| client/*.conf | each PC's login details |
| lab-up.sh, lab-down.sh | build and remove the lab |
| zt_collector.py | packets to eight features |
| zt_model.py | the Isolation Forest and the hybrid rule |
| zt_respond.py | the response engine |
| zt_pipeline.py | the live loop |
| zt_traffic.py | normal traffic and attacks for testing |
| demo.md | the panel demonstration script |

# Part B: Hands-on Exercises

## B0. Before you start

Open a terminal and run these two commands first, every time:

```
cd ~/Networkautomation/zt-project
source venv/bin/activate
```

> Type each command exactly, one at a time, and compare the result with "You should see". If something looks different, stop and ask.

Some exercises need **two terminals** side by side. Open the second one with the **+** in the Terminal panel and run the same two commands in it.

## Exercise 1: Start the lab and check it is healthy

1. Close other heavy programs (browser, Free Download Manager):

```
pkill fdm
```

2. Remove anything left over, then build the lab (about 5 minutes, asks for your password):

```
./lab-down.sh
./lab-up.sh
```

You should see at the end: **6 lines with PASS**, then a table where **bob, alice and guest1 are SUCCESS** in VLANs 10, 20 and 30.

3. Check every container is running (10 lab containers and 3 Zabbix ones):

```
docker ps --format '{{.Names}}  {{.Status}}'
```

> After the laptop restarts, the lab always comes back half-built. Always run ./lab-down.sh and then ./lab-up.sh again.

## Exercise 2: Look around the Zero Trust controls

1. Who is logged in, and in which VLAN:

```
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"
```

You should see: `Et2 bob ... SUCCESS ... 10`, `Et3 alice ... 20`, `Et4 guest1 ... 30`.

2. The state of every switch port (port 7 is the unplugged new desk):

```
docker exec clab-zt-acc1 Cli -p 15 -c "show interfaces status"
```

3. The user list in RADIUS:

```
cat radius/users
```

4. The rules between VLANs and their counters:

```
docker exec clab-zt-core Cli -p 15 -c "show ip access-lists ZT_POLICY"
```

5. The edge firewall:

```
docker exec clab-zt-edge iptables -L FORWARD -n -v
```

## Exercise 3: Unplug a PC and plug it back in

This shows "never trust, always verify": access is checked again every time a device connects, no matter what it had before.

1. Note how many logins RADIUS has accepted so far:

```
docker exec clab-zt-radius grep -c "Sent Access-Accept" /tmp/radius.log
```

2. Unplug staff-pc (link down), and look at the switch:

```
docker exec clab-zt-staff-pc ip link set eth1 down
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"
```

You should see: **alice is gone** from the table. The switch forgot her session the moment the cable came out.

3. Plug it back in, wait 5 seconds, and look again:

```
docker exec clab-zt-staff-pc ip link set eth1 up
sleep 5
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"
docker exec clab-zt-radius grep -c "Sent Access-Accept" /tmp/radius.log
```

You should see: alice **SUCCESS in VLAN 20** again, and the accept count **one higher**. She had to log in again; her earlier access counted for nothing.

4. Now the same, but with the login program stopped (as if the device had no credentials):

```
docker exec clab-zt-staff-pc pkill wpa_supplicant
docker exec clab-zt-staff-pc ip link set eth1 down
docker exec clab-zt-staff-pc ip link set eth1 up
sleep 5
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"
docker exec clab-zt-staff-pc ping -c 2 -W 2 10.10.20.1
```

You should see: **no SUCCESS for alice**, and the ping to her own gateway fails (100% packet loss). The port is connected but closed.

5. Put it back: start the login program again.

```
docker exec clab-zt-staff-pc wpa_supplicant -D wired -i eth1 -c /etc/wpa.conf -B
sleep 5
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"
```

You should see: alice **SUCCESS** in VLAN 20.

## Exercise 4: A wrong password gets nothing

1. Log guest-pc in with a wrong password:

```
docker exec clab-zt-guest-pc pkill wpa_supplicant
docker exec clab-zt-guest-pc sh -c "sed 's/password=.*/password=\"WRONG\"/' /etc/wpa.conf > /tmp/bad.conf"
docker exec clab-zt-guest-pc wpa_supplicant -D wired -i eth1 -c /tmp/bad.conf -B
sleep 10
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"
docker exec clab-zt-guest-pc ping -c 2 -W 2 10.10.30.1
```

You should see: `Et4 guest1 ... FAILED` with no VLAN, and the ping fails.

2. Put it back. After a failure the port waits 60 seconds before trying again, so it is switched off and on to skip the wait:

```
docker exec clab-zt-guest-pc pkill wpa_supplicant
python apply_config.py clab-zt-acc1 bounce4.cfg
docker exec clab-zt-guest-pc wpa_supplicant -D wired -i eth1 -c /etc/wpa.conf -B
sleep 10
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"
```

You should see: guest1 **SUCCESS** in VLAN 30 again.

## Exercise 5: Try to move laterally from the guest PC

An attacker on the guest network tries to reach other internal systems.

1. Reset the rule counters so you only see this exercise:

```
docker exec clab-zt-core Cli -p 15 -c "clear ip access-lists counters ZT_POLICY"
```

2. From guest-pc, try the admin PC, the staff PC and the RADIUS server, then the web server it is allowed to use:

```
docker exec clab-zt-guest-pc ping -c 2 -W 2 10.10.10.50
docker exec clab-zt-guest-pc ping -c 2 -W 2 10.10.20.50
docker exec clab-zt-guest-pc ping -c 2 -W 2 10.10.10.5
docker exec clab-zt-guest-pc curl -s -m 4 http://10.10.40.10
```

You should see: the three pings fail (100% packet loss), and the web server answers `ZT-DMZ-web-server`.

3. See which rules stopped it:

```
docker exec clab-zt-core Cli -p 15 -c "show ip access-lists ZT_POLICY"
```

You should see: **line 50** (guest to admin) and **line 60** (guest to staff) now have match counters. That is the proof that the core switch blocked the lateral movement.

> Honest limit for the panel: traffic between two PCs in the **same** VLAN never reaches the core switch, so it is not filtered. The lab has one PC per VLAN, so it never happens here. Filtering inside a VLAN would need private VLANs or per-port ACLs (future work).

## Exercise 6: Add a new PC (onboarding a new staff member)

A new staff member, **carol**, gets a desk. The cable is already run to switch port 7, but her PC is unplugged and she has no account yet.

1. Look at the new desk's port first:

```
docker exec clab-zt-acc1 Cli -p 15 -c "show interfaces status"
```

You should see: `Et7 notconnect 99`. Nothing plugged in.

2. **Plug in** her PC:

```
docker exec clab-zt-new-pc ip link set eth1 up
sleep 4
docker exec clab-zt-acc1 Cli -p 15 -c "show interfaces status"
```

You should see: `Et7 connected`, but **no VLAN**. The cable works; the network does not trust it yet.

3. Her PC **tries to log in** as carol (she has no account):

```
docker exec clab-zt-new-pc wpa_supplicant -D wired -i eth1 -c /etc/wpa.conf -B
sleep 8
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"
docker exec clab-zt-radius grep "Sent Access-Reject" /tmp/radius.log | tail -1
```

You should see: `Et7 carol FAILED`, and RADIUS logged an **Access-Reject**.

4. **Create carol's account** in RADIUS: a password and VLAN 20 (Staff). This adds two lines to the end of the user list:

```
printf 'carol  Cleartext-Password := "carolpass"\n    Tunnel-Type = VLAN, Tunnel-Medium-Type = IEEE-802, Tunnel-Private-Group-Id = "20"\n' >> radius/users
tail -2 radius/users
```

> Always add to this file with >> (append) or a normal editor like nano. Do not use sed -i on it: that replaces the file, and the RADIUS container would keep reading the old one.

5. **Tell RADIUS to reload** its user list:

```
docker exec clab-zt-radius sh -c 'touch /etc/freeradius/3.0/mods-config/files/authorize; kill -HUP $(pgrep -o freeradius)'
docker exec clab-zt-radius sh -c 'grep "HUP - " /tmp/radius.log | tail -1'
```

You should see: `HUP - Files loaded by a module have changed.`

6. **Unplug and plug back in**, so the switch starts a fresh login:

```
docker exec clab-zt-new-pc ip link set eth1 down
sleep 2
docker exec clab-zt-new-pc ip link set eth1 up
sleep 8
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"
```

You should see: **`Et7 carol SUCCESS 20 STAFF`**. RADIUS put her on the staff floor because of her identity.

7. Give her PC its address (the lab has no DHCP server, so this is done by hand, exactly as lab-up.sh does for the other PCs), and test:

```
docker exec clab-zt-new-pc sh -c 'ip addr add 10.10.20.60/24 dev eth1; ip route replace default via 10.10.20.1'
docker exec clab-zt-new-pc curl -s -m 4 http://10.10.40.10
```

You should see: `ZT-DMZ-web-server`. Carol is fully onboarded.

8. **Clean up**, so you can repeat the exercise: remove her account, reload RADIUS, unplug her PC.

```
git show HEAD:radius/users > radius/users
docker exec clab-zt-radius sh -c 'touch /etc/freeradius/3.0/mods-config/files/authorize; kill -HUP $(pgrep -o freeradius)'
docker exec clab-zt-new-pc pkill wpa_supplicant
docker exec clab-zt-new-pc sh -c 'ip addr flush dev eth1 scope global; ip link set eth1 down'
```

### How the new desk was added to the lab (for the panel)

If asked "how would you add a PC to the topology itself", the answer is three changes, all already done for new-pc:

- **zt-dev.clab.yml**: a new node (`new-pc`) and a new cable (`acc1:eth7` to `new-pc:eth1`).
- **acc1.cfg**: port Ethernet7 configured like the other user ports (`dot1x pae authenticator`, `dot1x port-control auto`, default VLAN 99).
- **client/new-pc.conf**: the PC's login details (carol).

Then the lab is rebuilt with `./lab-down.sh` and `./lab-up.sh`. Creating the RADIUS account (step 4 above) is the part an administrator does every time a new person joins.

## Exercise 7: Watch the detector

You need two terminals: **A** for commands, **B** for the detector.

1. In **terminal A**, start normal traffic on the three PCs for 15 minutes:

```
python zt_traffic.py background --seconds 900
```

2. In **terminal B**, start the detector:

```
python zt_pipeline.py
```

You should see: one line every 10 seconds with each PC's score, all negative, nothing flagged.

3. Open Zabbix in the browser (http://localhost:8080, Admin / zabbix) and go to **Dashboards > ZT Lab overview > Threat detection and response**. The three score lines sit below the red threshold line.

> Only one detector can run at a time. To stop it: Ctrl+C in terminal B.

## Exercise 8: Attack 1, denial of service, blocked

With the detector running in terminal B:

1. In terminal A, start the attack from guest-pc (40 seconds):

```
python zt_traffic.py attack --mode dos --seconds 40
```

You should see in terminal B within 10 to 20 seconds:

```
... guest-pc +0.0xx  << FLAGGED (model)
   !! guest-pc: dos -> BLOCKED 10.10.30.50 in 1.x s after the window closed
```

2. Prove it:

```
docker exec clab-zt-core Cli -p 15 -c "show ip access-lists ZT_POLICY"
docker exec clab-zt-guest-pc curl -s -m 4 http://10.10.40.10 || echo BLOCKED
docker exec clab-zt-staff-pc curl -s -m 4 http://10.10.40.10
```

You should see: a new **line 71 deny ip host 10.10.30.50 any** with a rising counter; guest-pc is BLOCKED; staff-pc still gets the web page.

3. Reset before the next attack:

```
python zt_respond.py reset
```

## Exercise 9: Attack 2, port scan, quarantined

1. In terminal A:

```
python zt_traffic.py attack --mode portscan --seconds 40
```

You should see in terminal B: `guest-pc: portscan -> QUARANTINED guest-pc`.

2. Prove it:

```
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"
docker exec clab-zt-guest-pc ip -4 addr show eth1
docker exec clab-zt-guest-pc curl -s -m 3 http://10.10.40.10 || echo "no access"
```

You should see: `Et4 guest1 SUCCESS 99 QUARANTINE`, address **10.10.99.30**, and no access.

3. Reset:

```
python zt_respond.py reset
```

## Exercise 10: Attack 3, brute force, quarantined

1. In terminal A (about 5 wrong passwords per second against guest-pc's port):

```
python zt_traffic.py attack --mode bruteforce --seconds 40
docker exec clab-zt-radius grep -c "Sent Access-Reject" /tmp/radius.log
```

You should see in terminal B: `FLAGGED (model+rule)` and `guest-pc: bruteforce -> QUARANTINED guest-pc`. "model+rule" means both the Isolation Forest and the failed-login rule caught it.

2. Reset:

```
python zt_respond.py reset
```

## Exercise 11: Attack 4, insider data theft, account disabled

1. In terminal A (staff-pc downloads large amounts of data):

```
python zt_traffic.py attack --mode insider --seconds 40
```

You should see in terminal B: `staff-pc: insider -> DISABLED account alice`.

2. Prove it:

```
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"
```

You should see: `Et3 alice FAILED`. Her account is rejected; staff-pc has no network.

3. Reset (this also brings alice back):

```
python zt_respond.py reset
```

## Exercise 12: Attack 5, off-hours session, alert only

1. In terminal A:

```
python zt_traffic.py attack --mode offhours --seconds 40
```

You should see in terminal B: `staff-pc: offhours -> ALERT ONLY`. Nothing is blocked:

```
docker exec clab-zt-staff-pc curl -s -m 4 http://10.10.40.10
```

> Why alert only: working at 2 a.m. is unusual but may be legitimate. The system tells an analyst instead of cutting the person off.

## Exercise 13: Finish and shut down

1. Stop the detector: **Ctrl+C** in terminal B.
2. In terminal A, stop the traffic and undo all actions:

```
python zt_traffic.py stop
python zt_respond.py reset
```

3. If you are done for the day, remove the lab:

```
./lab-down.sh
```

# Part C: Help

## When something goes wrong

| Problem | What to do |
|---|---|
| "Only ... MB available (need 4500)" | Close the browser and Free Download Manager (`pkill fdm`). If still short by a little: `MIN_MB=4300 ./lab-up.sh` |
| A switch command says it cannot connect | The lab is half-built (often after a restart): `./lab-down.sh` then `./lab-up.sh` |
| A PC shows FAILED in show dot1x hosts | Repeat step 2 of Exercise 4 for that PC (Et2 admin, Et3 staff, Et4 guest) |
| "Another pipeline is already running" | Stop the old one with the kill command it prints |
| Everything should go back to normal | `python zt_respond.py reset` |
| Zabbix page is empty | Wait a minute after lab-up; check `python zbx_setup.py status` |
| Anything else | Copy the error and ask |

## Command cheat sheet

| I want to... | Command |
|---|---|
| Build the lab | `./lab-up.sh` |
| Remove the lab | `./lab-down.sh` |
| See who is logged in | `docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"` |
| See the VLAN rules | `docker exec clab-zt-core Cli -p 15 -c "show ip access-lists ZT_POLICY"` |
| Run a command on a PC | `docker exec clab-zt-guest-pc <command>` |
| Start normal traffic | `python zt_traffic.py background --seconds 900` |
| Start the detector | `python zt_pipeline.py` |
| Launch an attack | `python zt_traffic.py attack --mode dos --seconds 40` (or portscan, bruteforce, insider, offhours) |
| Undo all responses | `python zt_respond.py reset` |
| Open Zabbix | http://localhost:8080 (Admin / zabbix) |
