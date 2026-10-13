
## PHASE 1 COMPLETE (13 Oct 2026)
- 802.1X verified on cEOS 4.36.2F: PEAP/MSCHAPv2 via FreeRADIUS; RADIUS-assigned VLAN works
  (alice -> VLAN 20); wrong password -> Access-Reject, port FAILED, no VLAN.
- Needed fix: FreeRADIUS use_tunneled_reply = yes (baked into image zt-node:2).
- Switch config pushed over Netmiko (apply_config.py + sw1.cfg). Files: Dockerfile, phase1b.clab.yml.
- Not tested yet: MAB fallback, Auth failure VLAN (to VLAN 99), multiple ports/hosts.
- Gotchas: docker bind mounts break with sed -i on the host (edit inside container or replace via cat >);
  Netmiko lands in user mode so call conn.enable(); show dot1x all summary is invalid on EOS.
- Host has 8 GB RAM; cEOS ~1 GB each; reduce lab if needed.
- Report notes: dot1x done on real cEOS; RADIUS = FreeRADIUS (stand-in for Cisco ISE);
  PEAP cert is the default self-signed one (lab only); creds are lab-only plaintext.

## NEXT: Phase 2, full topology (1 core + 2-3 access + Linux containers), Zabbix, baseline configs

## CORRECTION (13 Oct 2026)
- Attacks per the proposal (3.5.2): brute-force, DoS, insider (off-hours/port scan/exfil). NOT rogue switch/VLAN hop/MAC spoof.
- Response engine must include: disable compromised account (abstract), plus block IP, quarantine, alert, log.
- DMZ segment = 10.10.40.0/24 (edge .1, web .10). Quarantine stays VLAN 99, 10.10.99.0/24.
- Figure 2.1 needs redrawing: FreeRADIUS, single core, VLANs 10/20/30/99, add Zabbix, drop IoT/wireless/TACACS+.

## STATUS 13 Oct 2026, evening
- Phase 1 complete (dot1x + RADIUS-assigned VLAN verified).
- Phase 2A in progress: zt-dev.clab.yml deployed (core + acc1 + edge, web, radius, siem, admin/staff/guest PCs).
  9 nodes ran fine; ~2.9 GiB total (cEOS ~1.4-1.5 GiB each, Linux containers ~12 MiB combined).
- core.cfg written (VLANs, SVIs, GUEST_ACL, QUARANTINE_ACL, default route to edge).
  Apply with: python apply_config.py clab-zt-core core.cfg  (check configs/core-running.cfg for GUEST_ACL).
- RADIUS now: clients 10.10.10.0/24, users bob->VLAN10, alice->VLAN20, guest1->VLAN30.
  Image zt-node:3 (adds iptables, curl, python3; includes use_tunneled_reply fix).
- Addressing: core<->edge 10.10.0.0/30 (.1/.2); DMZ 10.10.40.0/24 (edge .1, web .10); servers on VLAN 10 (radius .5, siem .20).

## Hardware / stability lessons
- Laptop has ONE 8 GiB SODIMM (slot 1 empty); 7.1 GiB visible. Verify in BIOS / reseat / buy a 2nd stick.
- Deploying 3 cEOS at once froze the laptop. Use: sudo containerlab deploy -t zt-dev.clab.yml --max-workers 1
- Close Chrome/SharePoint tab before deploying. earlyoom installed (args: -r 60 -m 4 -s 100).
- Swap: 12 GiB existing; drive type of 1 TB disk not yet checked (lsblk -d -o NAME,ROTA,...).

## Still to do
- 2B: acc1 config (access ports with dot1x, fixed VLAN 10 ports for radius/siem, trunk to core). Plan the quarantine vs dot1x interaction.
- 2C: edge iptables NAT/firewall + DMZ web server (python3 -m http.server).
- 2D: Zabbix + SNMP (check RAM headroom first).
- Phase 3: Python pipeline (collector, Isolation Forest, response incl. DISABLE ACCOUNT).
- Phase 4: attacks (brute-force, DoS, insider), metrics, report.
- Report edits: Ch3 3.4.2 tools; Ch4 4.1/4.4.1 + Figs 4.7/4.8; redraw Fig 2.1 (FreeRADIUS, one core, VLANs 10/20/30/99, Zabbix, no IoT/wireless/TACACS+).
