const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, LevelFormat, PageBreak, TableOfContents, Footer, PageNumber, ImageRun,
} = require("docx");

const path = require("path");
const OUT = process.argv[2] || path.join(__dirname, "..", "ZT_Project_Implementation_Log.docx");
const STAMP = new Date().toLocaleString("en-GB", { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" });
const W = 9026; // A4 text width with 1" margins (DXA)
const ACCENT = "1F4E79";

// ---------- helpers ----------
const runs = (t) => {
  // **bold** and `code` inline markup
  const out = [];
  t.split(/(\*\*[^*]+\*\*|`[^`]+`)/).forEach((p) => {
    if (!p) return;
    if (p.startsWith("**")) out.push(new TextRun({ text: p.slice(2, -2), bold: true }));
    else if (p.startsWith("`")) out.push(new TextRun({ text: p.slice(1, -1), font: "Consolas", size: 20 }));
    else out.push(new TextRun(p));
  });
  return out;
};
const P = (t, opts = {}) => new Paragraph({ children: runs(t), spacing: { after: 120 }, ...opts });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)], pageBreakBefore: true });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(t)] });
const B = (t, level = 0) => new Paragraph({ numbering: { reference: "bullets", level }, children: runs(t), spacing: { after: 60 } });
const N = (t, ref = "steps") => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(t), spacing: { after: 60 } });
const CODE = (lines) => lines.map((l, i) => new Paragraph({
  children: [new TextRun({ text: l, font: "Consolas", size: 18 })],
  shading: { type: ShadingType.CLEAR, fill: "F2F2F2", color: "auto" },
  spacing: { after: i === lines.length - 1 ? 160 : 0 },
  indent: { left: 200 },
}));

const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };
function T(header, rows, widths) {
  const total = widths.reduce((a, b) => a + b, 0);
  const ws = widths.map((w) => Math.round((w / total) * W));
  ws[ws.length - 1] += W - ws.reduce((a, b) => a + b, 0);
  const cell = (text, i, head) => new TableCell({
    width: { size: ws[i], type: WidthType.DXA },
    borders,
    shading: head ? { type: ShadingType.CLEAR, fill: ACCENT, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({
      children: head ? [new TextRun({ text, bold: true, color: "FFFFFF", size: 19 })]
        : runs(String(text)).map((r) => { r.root && 0; return r; }),
    })],
  });
  return new Table({
    width: { size: W, type: WidthType.DXA },
    columnWidths: ws,
    rows: [
      new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, i, true)) }),
      ...rows.map((r) => new TableRow({ children: r.map((c, i) => cell(c, i, false)) })),
    ],
  });
}
const IMG = (file, w, h, caption) => {
  const f = path.join(__dirname, "..", "results", file);
  if (!fs.existsSync(f)) return [];
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: "png", data: fs.readFileSync(f), transformation: { width: w, height: h } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: caption, italics: true, size: 18, color: "52514E" })] }),
  ];
};
const GAP = () => new Paragraph({ children: [], spacing: { after: 120 } });

// ---------- content ----------
const c = [];

// Title page
c.push(
  new Paragraph({ children: [], spacing: { before: 2400 } }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "A Zero-Trust Network with Automated Threat Detection and Response using Isolation Forest", bold: true, size: 40, color: ACCENT })], spacing: { after: 400 } }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Implementation Log and Progress Report", size: 30 })], spacing: { after: 800 } }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Esborn Kihiu, Adm No. 168863", size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "BSc Computer Networks and Cyber Security, Strathmore University", size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Supervisor: Mr. James Gikera", size: 24 })], spacing: { after: 600 } }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Last updated " + STAMP, italics: true, size: 22 })] }),
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ children: [new TextRun({ text: "Contents", bold: true, size: 32, color: ACCENT })], spacing: { after: 200 } }),
  new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  P("(If the table of contents is empty, right-click it in Word and choose Update Field.)", { children: [new TextRun({ text: "If the table of contents looks empty, right-click it in Word and choose Update Field.", italics: true, size: 18 })] }),
);

// 1. Summary
c.push(
  H1("1. Executive Summary"),
  P("This document records everything that has been built for the project from the first planning session up to 14 October 2026. It is meant both as a working log and as source material for Chapter 5 (Results) and the corrections needed in Chapters 1 to 4."),
  P("The project builds a working Zero Trust enterprise network in software and adds a machine-learning layer that watches the traffic, spots anomalies with the Isolation Forest algorithm, and responds automatically. Instead of Cisco Packet Tracer, the network runs in **containerlab** with real **Arista cEOS** switch software, **FreeRADIUS** for 802.1X authentication, a Linux edge firewall, a DMZ web server, a SIEM collector host and **Zabbix** monitoring. This gives a network that Python can actually log into, capture from and reconfigure, which Packet Tracer cannot offer."),
  H2("1.1 Status at a glance"),
  T(["Area", "Status"], [
    ["Phase 0: planning and platform", "Done"],
    ["Phase 1: 802.1X proof of concept", "Done and verified"],
    ["Phase 2: full lab (2A to 2D) and one-command rebuild", "Done and verified: 6/6 self-tests PASS, 3 users authenticated, 9 hosts in Zabbix"],
    ["SPAN mirror to the SIEM", "Done, part of lab-up.sh"],
    ["Log collector (zt_collector.py)", "Done; on 14 Oct upgraded with a fast pcap reader; 10/10 offline tests pass"],
    ["Traffic generator (zt_traffic.py)", "Rebuilt on 14 Oct; 6/6 offline tests pass; live DoS smoke test passed"],
    ["Baseline and attack datasets", "Done: 594 normal rows from 4 runs, 20 attack windows each for DoS, port scan, insider, off-hours and brute force"],
    ["Isolation Forest model", "Done: hybrid detector (IF + brute-force rule), 5-fold accuracy 99.0%, recall 100%, false positives 1.1%"],
    ["Brute-force attack generator", "Done: 10 to 80 failed logins per window; 5 runs collected"],
    ["Automated response engine", "In progress: block IP and alert-only done and tested live; quarantine and disable-account next"],
    ["Zabbix push monitoring of every node", "Done and verified: 9 nodes push 54 values per cycle, test alert raised a Problem"],
    ["Report corrections (Ch. 1 to 4)", "Not started (list in section 12)"],
    ["Backup", "Automatic: ~/Desktop/zt-project-backup is refreshed after every git commit"],
  ], [40, 60]),
  GAP(),
  P("Items marked **(other account)** in this document were done in an earlier chat on another account and come from its summary; where they have since been re-checked on the laptop this is stated."),
);

// 2. Project
c.push(
  H1("2. The Project"),
  H2("2.1 Aim"),
  P("To design and simulate a Zero Trust enterprise network with automated threat detection and response using the Isolation Forest machine learning algorithm."),
  H2("2.2 Specific objectives (Chapter 1.3.2)"),
  N("Investigate Zero Trust principles, identity-based access control and common enterprise network threats.", "obj"),
  N("Implement Isolation Forest anomaly detection with Python-based log collection.", "obj"),
  N("Design and build a segmented Zero Trust network with VLANs, ACLs, a DMZ, quarantine and automated response.", "obj"),
  N("Test and validate how well the system detects and responds to threats.", "obj"),
  H2("2.3 The three layers"),
  T(["Layer", "What it does", "How it is built"], [
    ["Zero Trust network", "Nobody gets on the network without authenticating; each user lands only in the segment their role needs.", "802.1X on the access switch, FreeRADIUS assigns the VLAN, ZT_POLICY ACL on the core, iptables on the edge, DMZ for public services."],
    ["Detection", "Learns what normal traffic looks like and scores each session for how unusual it is.", "SPAN mirror to the SIEM, Python collector extracts 8 features per host per 10 s window, scikit-learn Isolation Forest."],
    ["Automated response", "Acts on anomalies without waiting for a human.", "DoS: block source IP. Brute-force / port scan: quarantine to VLAN 99. Off-hours / unclassified: alert only. All actions logged and sent to Zabbix."],
  ], [18, 37, 45]),
  GAP(),
  H2("2.4 The eight model features (Chapter 4.2)"),
  T(["Feature", "Meaning", "Attack it reveals"], [
    ["packet_count", "Packets to or from the host in the window", "DoS, data exfiltration"],
    ["avg_packet_size", "Mean IP packet length", "Exfiltration (large), floods (small)"],
    ["bytes_transferred", "Total IP bytes in the window", "Insider bulk download"],
    ["connection_duration", "Mean flow duration", "Scans (very short), long sessions"],
    ["failed_logins", "RADIUS Access-Rejects for the host's MAC", "Brute-force"],
    ["unique_dst_ports", "Distinct destination ports the host opened", "Port scan"],
    ["requests_per_min", "New connections started by the host, per minute", "DoS, scans"],
    ["off_hours", "1 if the window falls outside 08:00 to 17:59", "Off-hours / insider sessions"],
  ], [24, 44, 32]),
  GAP(),
  H2("2.5 Attacks evaluated"),
  P("From proposal section 3.5.2 and the Chapter 4 black-box: **brute-force**, **denial of service**, **insider threat**, plus **port scan** and **off-hours sessions**. Results will be reported as detection accuracy, false positive rate and response time."),
);

// 3. Platform decisions
c.push(
  H1("3. Platform and Key Decisions"),
  P("The proposal named Cisco Packet Tracer, GNS3 and Cisco ISE. During Phase 0 the platform was changed. Every change keeps the same security principle while making the network something Python can actually work with."),
  T(["Decision", "Reason"], [
    ["Packet Tracer replaced by containerlab + Arista cEOS-lab 4.36.2F", "Packet Tracer has no real SSH from the host, so the Python detection and response pipeline would have nothing to connect to. cEOS is real switch software that runs as a container."],
    ["cEOS chosen over GNS3, vEOS and Nokia SR Linux", "Free (guest download), scriptable and the lightest option. SR Linux has no 802.1X; GNS3 would not remove the 802.1X uncertainty."],
    ["FreeRADIUS instead of Cisco ISE", "Open-source RADIUS server implementing the same AAA principles and dynamic VLAN assignment."],
    ["One core and one access switch", "The laptop has about 7.1 GiB of usable RAM; three cEOS nodes booting together froze it. The proposal does not require redundancy."],
    ["Edge router replaced by a Linux container", "iptables provides NAT and perimeter filtering with a fraction of the memory."],
    ["Combined ACL (ZT_POLICY) on core Ethernet1", "cEOS rejects ACLs on SVIs (\"Unavailable command\"). A port ACL inbound on the trunk was tested and is enforced."],
    ["Python for response, Zabbix for monitoring", "As specified by the student."],
    ["Off-hours simulated with --sim-hours", "The lab clock is real time; collecting a baseline at night would teach the model that night-time is normal."],
    ["Strict window labelling (90 % rule)", "A window counts as attack only if the attack covers at least 90 % of it; part-attack windows are dropped so they never appear as false alarms."],
    ["Headers-only capture and a custom pcap reader (14 Oct)", "With about 1.5 GB of free RAM, scapy could not safely load large captures. Capturing 128 bytes per packet and parsing with Python struct keeps memory low; the real packet length is still read from the IP header."],
  ], [38, 62]),
);

// 4. Architecture
c.push(
  H1("4. Architecture as Built"),
  H2("4.1 Nodes"),
  T(["Node", "Type", "Role"], [
    ["core", "Arista cEOS", "Layer 3: SVIs, inter-VLAN routing, ZT_POLICY ACL, default route to edge"],
    ["acc1", "Arista cEOS", "Layer 2 access: 802.1X ports, server ports, SPAN source"],
    ["edge", "Linux", "Gateway: iptables firewall, NAT to the internet, DMZ gateway"],
    ["web", "Linux", "DMZ web server (python http.server, port 80)"],
    ["radius", "Linux", "FreeRADIUS server, 10.10.10.5"],
    ["siem", "Linux", "Log collector and pipeline host, 10.10.10.20, receives the SPAN mirror"],
    ["admin-pc, staff-pc, guest-pc", "Linux", "802.1X supplicants (wpa_supplicant) for users bob, alice and guest1"],
    ["zbx-db, zbx-server, zbx-web", "Docker", "Zabbix 7.0 monitoring; web UI on http://localhost:8080"],
  ], [26, 16, 58]),
  GAP(),
  H2("4.2 Links"),
  T(["From", "To", "Purpose"], [
    ["core eth1", "acc1 eth1", "802.1Q trunk"],
    ["core eth3", "edge eth1", "Routed transit 10.10.0.0/30"],
    ["edge eth2", "web eth1", "DMZ 10.10.40.0/24"],
    ["acc1 eth2 / eth3 / eth4", "admin-pc / staff-pc / guest-pc", "802.1X access ports"],
    ["acc1 eth5", "radius", "AAA server port (VLAN 10)"],
    ["acc1 eth6", "siem", "Collector port and SPAN destination"],
  ], [30, 35, 35]),
  GAP(),
  H2("4.3 VLANs and addressing"),
  T(["VLAN", "Name", "Subnet", "Gateway", "Notes"], [
    ["10", "ADMIN", "10.10.10.0/24", "10.10.10.1", "radius .5, siem .20, acc1 SVI .11, admin-pc .50"],
    ["20", "STAFF", "10.10.20.0/24", "10.10.20.1", "staff-pc .50"],
    ["30", "GUEST", "10.10.30.0/24", "10.10.30.1", "guest-pc .50"],
    ["99", "QUARANTINE", "10.10.99.0/24", "10.10.99.1", "Default for unauthenticated ports"],
    ["999", "NATIVE_UNUSED", "none", "none", "Trunk native VLAN (VLAN-hopping hygiene)"],
    ["DMZ", "-", "10.10.40.0/24", "edge .1", "web server .10"],
    ["Transit", "-", "10.10.0.0/30", "-", "core .1, edge .2"],
  ], [10, 18, 20, 16, 36]),
  GAP(),
  P("The management network is 172.20.20.0/24. Its addresses change on each deploy, so the scripts read them from Docker instead of hard-coding them."),
  H2("4.4 Zero Trust controls"),
  B("**802.1X authentication** (PEAP/MSCHAPv2) on acc1 Ethernet2 to 4. FreeRADIUS returns the VLAN: bob to 10, alice to 20, guest1 to 30. A failed login leaves the port blocked."),
  B("**FreeRADIUS**: clients.conf allows 10.10.10.0/24; the users file maps each user to a Tunnel-Private-Group-Id. The fix `use_tunneled_reply = yes` is baked into the zt-node image."),
  B("**ZT_POLICY ACL** inbound on core Ethernet1: permits DHCP; quarantine may reach only RADIUS (UDP 1812) and the SIEM; denies quarantine to everything else; denies guest to the admin, staff and quarantine subnets; permits the rest. Hit counters are enabled and serve as evidence."),
  B("**Edge iptables**: FORWARD policy DROP; established traffic allowed; internal to internet allowed; internal to DMZ only TCP 80 to 10.10.40.10; DMZ to internal dropped; DMZ to internet allowed; NAT out of eth0."),
  B("**Switch hygiene**: unused native VLAN 999, allowed-VLAN lists on trunks, BPDU Guard and PortFast on client ports."),
  B("**Monitoring**: SNMP v2c (read-only) on both switches; Zabbix templates \"Arista by SNMP\" and \"ICMP Ping\"; hosts registered through the Zabbix API."),
  B("**SPAN**: acc1 Ethernet2 to 4 mirrored to Ethernet6 so the SIEM sees all admin, staff and guest traffic."),
);

// 5. Phase log
c.push(
  H1("5. Phase-by-Phase Implementation Log"),
  H2("Phase 0: Planning and platform choice"),
  P("Reviewed the Chapter 1 to 4 document, agreed a roadmap (65 to 80 hours in total), and chose containerlab, cEOS, FreeRADIUS, Zabbix and Python. Installed on Kali Linux (bare metal): Docker from the Kali packages (the get.docker.com script does not support Kali), containerlab through its installer, and a Python virtual environment with Netmiko and PyYAML. Downloaded cEOS-lab 4.36.2F from Arista (guest access is enough) and imported it as `ceos:4.36.2F`."),
  H2("Phase 1A: Environment and first connection"),
  P("Deployed one cEOS node, opened its CLI and connected from Python with Netmiko (device_type `arista_eos`). Lesson: Netmiko lands in user mode, so `conn.enable()` must be called before configuration."),
  H2("Phase 1B: The 802.1X day-one test"),
  P("Built one access switch, a FreeRADIUS server and one wpa_supplicant client to prove the riskiest assumption first."),
  B("Correct password: EAP success and the port moved to VLAN 20 (after enabling `use_tunneled_reply`)."),
  B("Wrong password: Access-Reject, port state FAILED, no VLAN."),
  P("Conclusion: real 802.1X with RADIUS-assigned VLANs works on cEOS, so no fallback design was needed."),
  H2("Phase 2A: Core switch, addressing and memory"),
  P("Wrote the topology file and core configuration (VLANs, SVIs, routing). The first deploy froze the laptop because three cEOS nodes booted at once on 7.1 GiB. Fixes: smaller topology, `--max-workers 1`, earlyoom, closing Chrome. Found that only one 8 GiB memory module is detected (slot 1 empty)."),
  H2("Phase 2B: Access switch and policy"),
  P("Configured acc1 and authenticated three users into VLANs 10, 20 and 30. Found that cEOS rejects ACLs on SVIs, so the policy was bound inbound on core Ethernet1 and confirmed to be enforced: before the policy all pings worked; afterwards guest to RADIUS and guest to staff were blocked while guest to web and staff to RADIUS were allowed, and the ACL counters increased. Fixed the PC default-route bug with `ip route replace`."),
  H2("Phase 2C: Edge firewall and DMZ"),
  P("Wrote edge-fw.sh and started a Python web server in the DMZ. Results: guest to web OK, staff to web HTTP 200, DMZ to RADIUS blocked, guest to internet OK after setting a DNS resolver (IPv6-only answers caused the first failure)."),
  H2("Phase 2D: Zabbix monitoring"),
  P("Started Zabbix in three containers (database 147 MB, server 50 MB, web 26 MB). SNMP on both switches answers. zbx_setup.py registers all nine hosts through the API and reports their status. Fixed a bug where the ICMP item search matched the wrong key and showed radius as DOWN."),
  H2("Phase 2 close: one-command rebuild"),
  P("zt-dev.clab.yml now describes the whole lab. lab-up.sh checks there is at least 4500 MB of free memory, deploys one node at a time, waits for switch SSH, applies all switch configs, logs the three PCs in, starts Zabbix, registers the hosts and runs six self-tests. lab-down.sh saves configs, removes Zabbix and destroys the lab. A full destroy and rebuild from the scripts passed."),
  H2("Phase 3 (part 1, other account)"),
  B("Confirmed capture tools (tcpdump, python3, curl) exist on every Linux node."),
  B("Added and verified the SPAN session on acc1: the SIEM sees guest to web traffic in both directions."),
  B("Found a stable Access-Reject signature in the RADIUS log naming the user and MAC (the log has no timestamps, so the collector reads it live)."),
  B("Built zt_collector.py: the eight features per host per 10-second window; tested offline and live; fixed a stray row for the switch address 10.10.10.11."),
  B("Built a traffic generator in a sandbox; it was never run in the lab and its files did not reach the laptop."),
  H2("Phase 3 (part 2, 14 October 2026)"),
  H3("Recovery and verification"),
  B("Moved the work into ~/Networkautomation/zt-project and made a full backup on the Desktop (zt-project-backup-2026-10-14), including the Chapter 4 document."),
  B("Set up automatic backups (backup.sh plus a git post-commit hook) and moved files from earlier phases into archive/ with a README; nothing deleted.", 0),
  B("Searched the whole home folder: zt_traffic.py and test_traffic.py were not on the laptop. The collector on disk was found to be the updated version (it has --sim-hours and the 10.10.10.11 fix) and its 9 offline checks all passed."),
  H3("Collector upgrade"),
  B("Replaced the scapy pcap reader with a fast reader built on Python's struct module, handling Ethernet, 802.1Q tags, TCP, UDP and ICMP."),
  B("Capture now keeps only the first 128 bytes of each packet (`tcpdump -s 128`). Features need lengths and ports, not payloads, and the true length comes from the IP header."),
  B("Split capture from feature extraction (`capture()` and `collect_batch()`) so the traffic generator can reuse it."),
  B("Added a 10th test comparing the new reader with scapy on a synthetic capture. All 10 tests pass."),
  H3("Traffic generator rebuilt (zt_traffic.py)"),
  P("A small standard-library agent is copied into each PC container and driven with docker exec. Every run captures through the collector, so the rows are exactly what the model will see. Normal traffic keeps running on all three PCs during every attack."),
  T(["Mode", "Attacker", "Behaviour", "Feature it raises"], [
    ["normal", "all PCs", "Page loads, occasional 200 kB downloads and pings, alternating busy and quiet minutes", "none"],
    ["dos", "guest-pc", "HTTP flood on the web server at a set rate (default 80 requests/s)", "packet_count, requests_per_min"],
    ["portscan", "guest-pc", "TCP connect scan of the web server, one new port at a set rate", "unique_dst_ports"],
    ["insider", "staff-pc", "Repeated download of a 20 MB file, throttled to a set byte rate", "bytes_transferred"],
    ["offhours", "staff-pc", "Normal behaviour but the attack windows are flagged as night-time", "off_hours"],
  ], [13, 13, 50, 24]),
  GAP(),
  P("Safety: the agent refuses any target outside 10.10.0.0/16, so it can never send traffic to the internet, the home network or the lab management network. test_traffic.py proves this along with the labelling rules (6 of 6 tests pass)."),
  H3("Live DoS smoke test"),
  T(["Window", "guest-pc (attacker)", "admin-pc and staff-pc"], [
    ["Before the attack", "50 packets, 30 requests/min, label 0", "10 to 25 packets, 6 to 24 requests/min"],
    ["During the attack", "about 8,000 packets, about 4,800 requests/min, label 1", "unchanged, label 0"],
    ["After the attack", "12 packets, 12 requests/min, label 0", "unchanged"],
  ], [22, 42, 36]),
  GAP(),
  P("24,397 packets were captured in 60 seconds; the two windows the attack only partly covered were dropped automatically. This meets the acceptance test: the attacker stands out by a factor of about 200 while the bystanders stay normal."),
  H3("Dataset collection and the MTU fault"),
  P("The first full collection (11:03 to 12:08) completed, but the summary showed the insider attack produced only about 31 packets per window instead of megabytes. Investigation found an MTU mismatch: the Linux nodes used 9500-byte jumbo frames while the cEOS switches route at 1500, so large HTTP replies were dropped at the core. Pings and small pages fit, which is why nothing had looked wrong before. All Linux lab interfaces were set to MTU 1500 in the topology; afterwards a 20 MB download ran at about 6 MB/s and an insider smoke test showed about 15 MB per window. The first datasets were moved to data/old_mtu_bug/ as evidence and everything was re-collected (12:25 to 13:30)."),
  H3("Final datasets"),
  T(["Class", "Rows", "Attack windows", "Median packets", "Median bytes", "Median ports", "Median req/min"], [
    ["normal (4 runs)", "594", "0", "22", "1,876", "1", "12"],
    ["DoS", "83", "20", "8,341", "836,670", "1", "4,632"],
    ["port scan", "72", "20", "376", "25,829", "296", "1,779"],
    ["insider", "75", "20", "12,215", "15,528,831", "1", "24"],
    ["off-hours", "69", "20", "14", "1,190", "1", "12"],
  ], [18, 9, 13, 15, 17, 13, 15]),
  GAP(),
  H3("Brute-force generator (step 3D)"),
  P("802.1X login frames are layer 2, so a password attack leaves only one trace on the IP side: the RADIUS requests the switch relays for that port, and the rejects that follow. A real supplicant retries only about every 20 seconds, too slowly to look like an attack. The generator therefore injects the relayed requests at the RADIUS server itself, with the switch's NAS address (10.10.10.11) and guest-pc's MAC as Calling-Station-Id, guessing passwords for bob, alice and admin. It cannot run on the SIEM because the SIEM's switch port is the SPAN destination, which is receive-only. The RADIUS secret is read from radius/clients.conf rather than written into the code."),
  P("A smoke test exposed a labelling flaw: FreeRADIUS delays each reject by one second, so rejects for the last attempts arrived after the attack had ended and the following window was labelled normal with 9 failed logins. An after-effect allowance (4 seconds for brute force) now drops such windows as transitions; a unit test covers it."),
  T(["Run", "Attempts per second", "Failed logins per attack window"], [
    ["bruteforce_01", "1", "9, 10, 10, 10"],
    ["bruteforce_02", "2", "17, 20, 20, 20"],
    ["bruteforce_03", "3", "25, 30, 30, 30"],
    ["bruteforce_04", "5", "42, 50, 49, 50"],
    ["bruteforce_05", "8", "67, 79, 80, 79"],
  ], [30, 30, 40]),
  GAP(),
  P("Across all datasets, no row labelled normal has a single failed login. zt_traffic.py also gained two commands for the live demo: background (normal traffic only) and attack (start one attack without capturing)."),
  GAP(),
  P("Rows in attack runs that are not attack windows are the other two PCs and the attacker before and after the attack; they are labelled normal. For comparison, the 99th percentile of normal windows is 540 packets, 430 kB, 1 destination port and 48 requests per minute, so every attack type is clearly separated on at least one feature, while the off-hours class differs only in its off_hours flag, which is by design."),
  P("collect_datasets.sh runs four 10-minute normal runs and five runs of each attack at five intensities, so the model is also tested on weak attacks, not only obvious ones."),
  T(["Dataset", "Runs", "Intensity per run", "Planned use"], [
    ["normal_01 to normal_04", "4 x 600 s", "-", "2 training, 1 tuning, 1 final test"],
    ["dos_01 to dos_05", "5 x 60 s", "40, 60, 80, 100, 120 requests/s", "Testing"],
    ["portscan_01 to portscan_05", "5 x 60 s", "10, 20, 30, 40, 50 ports/s", "Testing"],
    ["insider_01 to insider_05", "5 x 60 s", "0.5 to 2.5 MB/s", "Testing"],
    ["offhours_01 to offhours_05", "5 x 60 s", "normal traffic at night", "Testing"],
  ], [30, 15, 30, 25]),
);

// 5b. Model
c.push(
  H1("6. The Isolation Forest Model (step 3E)"),
  H2("6.1 How it works"),
  P("Isolation Forest builds many random trees. Each tree keeps splitting the data on a random feature at a random value until every window sits alone. Normal windows are alike, so it takes many splits to isolate one; an attack is unusual and is isolated in a few splits. The average number of splits becomes the anomaly score: the fewer the splits, the higher the score. In the code, AnomalyDetector (as in the Chapter 4 class diagram) wraps a StandardScaler and scikit-learn's IsolationForest (200 trees) behind fit() and score(); score = minus decision_function, so higher means more anomalous. A window is flagged when its score is above a threshold."),
  H2("6.2 Method"),
  B("**Unsupervised**: the model is never given labels. Labels are used only afterwards, to measure the result."),
  B("**Threshold** tuned on a separate normal run (normal_03): the 99th percentile of its scores, which targets about 1 % false alarms."),
  B("**5-fold leave-one-run-out**: in fold k, run k of every attack type is held out for testing and the model trains on two other runs of each type. Every run, including the weakest attacks, is tested by a model that never saw it. normal_04 is the held-out normal run, scored in every fold."),
  B("**Two training modes compared**: normal-only (novelty detection) and mixed (unlabelled traffic in which attacks are rare, about 9 % of windows), which is how Isolation Forest is normally used."),
  H2("6.3 Results"),
  T(["Training mode", "Accuracy", "Precision", "Recall", "F1", "False-positive rate", "ROC-AUC"], [
    ["Normal-only", "94.3%", "0.904", "0.470", "0.618", "0.5%", "0.807"],
    ["Mixed, IF only", "98.0%", "0.900", "0.900", "0.900", "1.1%", "0.990"],
    ["Hybrid: IF (mixed) + rule (chosen)", "99.0%", "0.909", "1.000", "0.952", "1.1%", "0.990*"],
  ], [22, 13, 13, 12, 10, 17, 13]),
  P("* ROC-AUC is computed from the Isolation Forest score alone; the rule is a yes/no decision and has no score."),
  GAP(),
  P("Totals over the 5 folds: 100 attack windows and 917 normal test windows (normal_04 plus the bystander and before/after windows of each held-out attack run)."),
  ...IMG("detection_by_type.png", 600, 285, "Figure: detection rate per attack type for the three detector designs"),
  ...IMG("score_distribution.png", 600, 288, "Figure: anomaly score of every test window with the tuned threshold (mixed training)"),
  ...IMG("confusion_matrix.png", 300, 257, "Figure: confusion matrix, hybrid detector, 5 folds"),
  H2("6.4 Findings"),
  B("**Normal-only training is blind to features that never vary in normal traffic.** failed_logins and off_hours are always 0 in normal windows and destination ports are almost always 1, so the trees never split on them: brute force and off-hours were detected 0 % of the time and port scans 40 %. This is a property of Isolation Forest, not a bug."),
  B("**Mixed training fixes this**: DoS, port scan, insider and off-hours are all detected 100 % on held-out runs with 1.1 % false alarms."),
  B("**Slow brute force is the hard case.** At 1 to 2 attempts per second (about 10 to 20 failed logins per window) every other feature looks normal, and the score only reaches the level of a busy normal window; catching these by lowering the threshold would raise false alarms to about 5 to 10 %. At 3 attempts per second half the windows are caught, and from 5 per second all of them."),
  H2("6.5 Design decision: hybrid detection"),
  P("To close the slow brute-force gap without raising false alarms, the student chose a hybrid design: the Isolation Forest stays the main detector, and one Zero Trust policy rule is added, 5 or more failed logins from one port in a 10-second window. The rule fires on 100 % of brute-force windows at every tested speed and on none of the normal windows (no normal window has a single failed login), so the false-positive rate stays at 1.1 %. Combining a learned model with a small number of explicit policy rules is common practice in security monitoring, and the results are reported both with and without the rule so the contribution of the model alone stays visible. In the code, detect() returns the model flag, the rule flag and which of them fired; the response engine records that reason with every alert."),
  B("The final model (models/zt_iforest.joblib) is trained the same way as evaluated, on runs 2 and 4 of each attack (unlabelled) plus normal_01 and normal_02; on the unseen runs it detects DoS, port scan, insider and off-hours 100 % and brute force 58 %, with 1.5 % false alarms on normal_04."),
);

c.push(
  H2("6.6 Response engine, part 1: block IP (step 3F)"),
  P("zt_respond.py follows the Chapter 4 class diagram: NetworkActions builds the exact CLI commands (pure functions, unit-tested), AlertBuilder builds the structured alert, and ResponseEngine applies the commands over SSH with Netmiko, remembers what it has already done, writes every incident to logs/incidents.jsonl and pushes the alert, the action and the detection-to-action time to Zabbix. A Zabbix outage never stops a response."),
  P("Block IP inserts one line per offender into ZT_POLICY on core Ethernet1, in the reserved range 71 to 79: after the guest rules and before the final permit. Infrastructure addresses (RADIUS, SIEM, switch, gateways) are refused, and a host already blocked is never acted on twice. SSH login to the switch takes about 0.75 s and the change itself about 0.10 s, so the live pipeline keeps the SSH session open."),
  T(["Live test (14 Oct)", "Result"], [
    ["Before", "guest-pc and staff-pc both reach the DMZ web server (HTTP 200)"],
    ["block 10.10.30.50", "Line 71 deny ip host 10.10.30.50 any added; 5 packets matched within a second"],
    ["After block", "guest-pc cut off (HTTP 000, its gateway unreachable); staff-pc unaffected (HTTP 200)"],
    ["Second block of the same IP", "Ignored (already blocked)"],
    ["unblock", "guest-pc back to HTTP 200"],
    ["block 10.10.10.5 (RADIUS)", "Refused: infrastructure address"],
  ], [35, 65]),
  GAP(),
  P("test_respond.py checks the commands, de-duplication, line reuse, state persistence, infrastructure protection and alert-only behaviour offline (6 checks, all pass)."),
);

// 6. Evidence
c.push(
  H1("7. Verified Evidence for Chapter 5"),
  P("Take a screenshot of each item for the report."),
  T(["Evidence", "Where to get it"], [
    ["show dot1x hosts: bob VLAN 10, alice 20, guest1 30, all SUCCESS", "acc1"],
    ["Wrong password gives Access-Reject and port FAILED", "acc1 and the radius log"],
    ["Ping matrix before and after policy, with ZT_POLICY counters", "core"],
    ["Edge iptables counters (DMZ to internal drops, DMZ web accepts)", "edge"],
    ["Six PASS self-test lines", "output of lab-up.sh"],
    ["Wrong password: Et4 FAILED with no VLAN, 100% ping loss; restore to SUCCESS after a port bounce (demo step 3b, tested 14 Oct)", "acc1, guest-pc"],
    ["SNMP walk of sysDescr and ifInOctets", "host"],
    ["Zabbix status: switches SNMP available, hosts ping UP", "python zbx_setup.py status"],
    ["SPAN capture showing mirrored traffic", "siem"],
    ["Collector and traffic generator test runs: ALL TESTS PASSED", "test_collector.py, test_traffic.py"],
    ["DoS smoke test table (section 5)", "data/smoke_dos.csv"],
  ], [65, 35]),
  GAP(),
  P("Not yet proven: the quarantine path (ZT_POLICY lines for VLAN 99 with counters) and everything to do with detection and response."),
);

// 7. Problems
c.push(
  H1("8. Problems Encountered and Fixes"),
  T(["Problem", "Cause", "Fix"], [
    ["Docker / containerlab install broke", "get.docker.com does not support Kali; leftover repo entry", "Removed docker.list; used Kali's docker.io and the containerlab installer"],
    ["Laptop froze on deploy", "Three cEOS nodes booting at once on 7.1 GiB", "--max-workers 1, two switches, close browser, earlyoom, memory gate in lab-up.sh"],
    ["earlyoom had no effect", "It needed free swap to be near zero", "EARLYOOM_ARGS=\"-r 60 -m 4 -s 100\""],
    ["Wrong-password test showed success", "sed -i on the host broke the bind mount", "Edit inside the container"],
    ["VLAN not assigned after login", "FreeRADIUS dropped tunnelled reply attributes", "use_tunneled_reply = yes"],
    ["ACL on SVI rejected", "cEOS software data plane", "ACL inbound on core Ethernet1"],
    ["Duplicate default route", "containerlab management route", "no ip route 0.0.0.0/0 172.20.20.1"],
    ["PC routes failed (File exists)", "Existing default route via eth0", "ip route replace default"],
    ["Guest curl returned 000", "DNS returned IPv6 only", "nameserver 1.1.1.1"],
    ["radius showed DOWN in Zabbix", "Script matched the icmppingloss key", "Exact key filter"],
    ["acc1 not configured by lab-up", "SSH not ready yet", "Wait for the SSH port before configuring"],
    ["Failed port stuck", "802.1X quiet period (60 s)", "Bounce the port or wait"],
    ["Phase 3 files missing on 14 Oct", "Created in a sandbox on another account", "Generator rebuilt and tested on the laptop"],
    ["Insider downloads never happened; 200 kB downloads stalled", "Linux nodes used MTU 9500 but cEOS routes at 1500, so large replies were dropped at the core", "All Linux lab interfaces set to MTU 1500 in zt-dev.clab.yml; first datasets kept in data/old_mtu_bug/ and re-collected"],
    ["Brute-force requests from the SIEM got no reply", "The SIEM's switch port is the SPAN destination, which is receive-only", "Inject the switch-relayed requests at the RADIUS server with the switch's NAS address"],
    ["Window after a brute force labelled normal with 9 failed logins", "FreeRADIUS delays rejects by 1 s, so late rejects spill past the attack end", "After-effect allowance drops those windows as transitions"],
    ["Little free RAM for captures", "Lab uses about 5.5 GB of 7.1 GB", "Headers-only capture, struct-based reader, Zabbix stopped during collection"],
  ], [28, 34, 38]),
);

// 8. Monitoring
c.push(
  H1("9. Monitoring with Zabbix"),
  H2("9.1 Viewing the dashboard"),
  N("Make sure Zabbix is running: `docker start zbx-db zbx-server zbx-web` (lab-up.sh starts it automatically).", "zbx"),
  N("Open http://localhost:8080 in a browser on the laptop.", "zbx"),
  N("Log in with the default Zabbix account (user Admin, password zabbix) and change the password afterwards under User settings.", "zbx"),
  N("Useful pages: Dashboards (overview), Monitoring > Hosts (all lab nodes and their status), Monitoring > Latest data (live values), Monitoring > Problems (alerts).", "zbx"),
  H2("9.2 What is monitored today"),
  B("Both switches through SNMP v2c (interface traffic, CPU, memory, uptime)."),
  B("All seven Linux nodes through ICMP ping (up or down only)."),
  H2("9.3 Every node pushes its own data (zt_zbx_push.py)"),
  P("SNMP and ping are pull-based and tell little about the Linux nodes. zt_zbx_push.py reads each container's own counters and sends them to Zabbix with the Zabbix sender protocol (TCP 10051) every 30 seconds. Zabbix converts the counters into per-second rates."),
  T(["Item", "Meaning"], [
    ["Data ports: packets in / out per second", "Traffic on the node's lab interfaces (management eth0 excluded)"],
    ["Data ports: bytes in / out per second", "Throughput on the lab interfaces"],
    ["Data ports: dropped packets per second", "Receive and transmit drops"],
    ["Container CPU usage", "CPU time used by the container, in percent"],
    ["Container memory in use", "Memory charged to the container (cgroup)"],
    ["Security alert (detection pipeline)", "Text alerts from the response engine; each one opens a Problem"],
  ], [45, 55]),
  GAP(),
  P("Triggers: high packet rate (over 1000 packets/s), container CPU above 80 % for 2 minutes, and security alert (stays open until an administrator closes it). A dashboard \"ZT Lab overview\" shows problems, host availability and graphs of traffic, CPU and memory for every node. lab-up.sh starts the push loop and lab-down.sh stops it."),
  H2("9.4 The two dashboard pages"),
  T(["Page", "Shows", "Used in the demo for"], [
    ["Network health", "Problems list, host availability, packets and bytes per second, CPU and memory for all nodes", "Proving the whole topology is monitored; traffic spikes during attacks"],
    ["Threat detection and response", "Anomaly score per PC with the threshold line, security alerts, last response action per PC, detection-to-action time", "Showing each attack being detected and answered automatically"],
  ], [20, 45, 35]),
  GAP(),
  P("The detection page was checked on 14 October with clearly labelled test values: the score graph drew the threshold line, and the action and timing widgets displayed the test entries. In Zabbix 7.0 the old Plain text widget is no longer available, so the Item history widget is used."),
  P("Verified on 14 October: all 9 nodes pushed 54 values per cycle with 0 failures, and a test alert for guest-pc appeared under Monitoring > Problems. Zabbix also reported that both cEOS switches use over 90 % of their memory allowance, which matches the RAM pressure seen throughout the project."),
);

// 9. Remaining
c.push(
  H1("10. Remaining Work"),
  H2("Phase 3 (detection and response)"),
  N("**Response engine** following the Chapter 4 activity diagram: DoS gives block source IP (deny line in ZT_POLICY above the permit, optionally iptables on edge); brute-force or port scan gives quarantine; off-hours or unclassified gives alert only; plus the abstract's disable-account action (reject the user in FreeRADIUS and bounce the port).", "rem"),
  N("**Quarantine on cEOS** - the riskiest piece: 802.1X assigns VLANs dynamically, so a plain access-VLAN change will not stick. Test the authentication-failure VLAN feature first; otherwise disable the account and bounce the port.", "rem"),
  N("**Alerts** - JSON alert and incident log, pushed to Zabbix.", "rem"),
  N("**Orchestrator** - one process that collects, scores, classifies, responds and timestamps each step to measure response time.", "rem"),
  H2("Phase 4 (validation and report)"),
  B("Run each attack end to end several times; capture ACL counters, logs, Zabbix alerts and timing."),
  B("Compute detection accuracy, false positive rate and response time per attack."),
  B("Write Chapter 5 with the evidence in section 7, the model results in section 6 and the limitations: simulated traffic only, cEOS-lab software data plane, SVI ACLs unsupported, simulated off-hours flag, 8 GB RAM, single access switch."),
);

// 10. Files
c.push(
  H1("11. Files and Commands"),
  P("Project folder: **~/Networkautomation/zt-project** (do not use ~/zt-project). Activate Python with `source venv/bin/activate` and never run the Python scripts with sudo."),
  T(["File", "Purpose"], [
    ["zt-dev.clab.yml", "Whole lab topology"],
    ["core.cfg, acc1.cfg, policy.cfg, snmp.cfg, fix_mgmt.cfg, span.cfg", "Switch configurations applied by lab-up.sh"],
    ["apply_config.py, save_configs.py", "Netmiko: push configs; save running configs to configs/"],
    ["edge-fw.sh", "Edge firewall and NAT"],
    ["radius/clients.conf, radius/users", "FreeRADIUS configuration"],
    ["client/*.conf", "wpa_supplicant logins for the three PCs"],
    ["Dockerfile", "Builds the zt-node:3 image used by every Linux node"],
    ["zabbix-up.sh, zbx_setup.py", "Start Zabbix; register hosts and report status"],
    ["lab-up.sh, lab-down.sh", "One-command rebuild and teardown"],
    ["zt_collector.py, test_collector.py", "Feature extraction and its 10 offline tests"],
    ["zt_traffic.py, test_traffic.py", "Traffic generator (normal, dos, portscan, insider, offhours, bruteforce; background and attack commands for the demo) and its 9 offline tests"],
    ["collect_datasets.sh", "Collects all Phase 3 datasets (about 65 minutes)"],
    ["data/", "Captured datasets (CSV)"],
    ["zt_zbx_push.py, test_zbx_push.py", "Every node pushes traffic, CPU and memory to Zabbix; security-alert channel; its 3 offline tests"],
    ["backup.sh", "Updates ~/Desktop/zt-project-backup; runs automatically after every git commit"],
    ["docs/build_log.js", "Generates this document (node docs/build_log.js)"],
    ["archive/", "Files from earlier phases kept for history (see archive/README.md)"],
    ["demo.md", "Step-by-step panel demonstration script with exact commands"],
    ["zt_model.py", "AnomalyDetector (Isolation Forest), hybrid detect() with the brute-force rule; evaluate, train and score commands"],
    ["zt_respond.py, test_respond.py", "Response engine (block IP, alert only, incident log, Zabbix) and its 6 offline tests"],
    ["results/", "metrics.json, per-window scores and the three Chapter 5 charts"],
    ["models/zt_iforest.joblib", "Trained model (rebuild any time with python zt_model.py train)"],
  ], [45, 55]),
  GAP(),
  H2("Daily routine"),
  ...CODE([
    "cd ~/Networkautomation/zt-project",
    "./lab-up.sh                      # about 5 minutes, close the browser first",
    "source venv/bin/activate",
    "python test_collector.py && python test_traffic.py",
    "python zt_traffic.py run --mode dos --seconds 60 --out data/try.csv",
    "./lab-down.sh",
    "git add -A && git commit -m \"what changed\"",
  ]),
  P("Lab-only credentials are stored in the configuration files. Remove them before publishing the repository anywhere."),
);

// 11. Report edits + risks
c.push(
  H1("12. Report Corrections Needed"),
  B("**Abstract**: describe the simulation as containerlab with Arista cEOS; use FreeRADIUS wording instead of Cisco ISE."),
  B("**2.3.2, 2.5 and Figure 2.1**: FreeRADIUS instead of Cisco ISE; remove TACACS+, the IoT VLAN and the wireless AP; one core switch; VLANs 10/20/30/99 and DMZ 10.10.40.0/24; add Zabbix."),
  B("**2.3.7**: feature list must match the eight features in Chapter 4."),
  B("**3.4.2**: tools are containerlab, Arista cEOS-lab, FreeRADIUS, Zabbix and Python, not Packet Tracer or GNS3."),
  B("**4.1, 4.3.x, 4.4.1, Figures 4.7 and 4.8**: replace the Packet Tracer and ISE build with the containerlab topology (containerlab graph can draw Figure 4.8); the edge router is a Linux container; QUARANTINE_ACL and GUEST_ACL are merged into ZT_POLICY on core Ethernet1; collection uses a SPAN mirror."),
  B("**1.4 Limitations**: add the reduced topology and the RAM limit."),
  H1("13. Risks and Open Questions"),
  B("**RAM**: only one 8 GiB module is detected. Check the BIOS or reseat it; a second 8 GB DDR4-2666 SODIMM would remove the main stability risk."),
  B("**Quarantine** on a dynamically assigned 802.1X port is untested and is the riskiest remaining piece."),
  B("**Zabbix history** is lost on every lab-down because the database lives inside the container."),
  B("**Time**: confirm the submission and demo dates with Mr. James Gikera and plan to finish Phase 3 with margin."),
);

const doc = new Document({
  creator: "Esborn Kihiu",
  title: "ZT Project Implementation Log",
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, color: ACCENT }, paragraph: { spacing: { before: 240, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, color: ACCENT }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, color: "404040" }, paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
      ...["steps", "obj", "zbx", "rem"].map((r) => ({
        reference: r, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }],
      })),
    ],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], size: 18 })] })] }) },
    children: c,
  }],
});

Packer.toBuffer(doc).then((b) => { fs.writeFileSync(OUT, b); console.log("wrote", OUT); });
