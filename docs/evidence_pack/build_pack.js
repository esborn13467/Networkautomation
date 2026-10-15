// Builds docs/evidence_pack/Chapter5_Evidence_Pack.docx: the Chapter 5 outline (headings and
// notes on what to cover), every screenshot with a factual caption, test-case tables in the
// guideline format, and the results data. It is source material: the chapter text is written
// by the student.   node docs/evidence_pack/build_pack.js
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, LevelFormat, Footer, PageNumber, ImageRun } =
  require(path.join(__dirname, "..", "node_modules", "docx"));

const ROOT = path.join(__dirname, "..", "..");
const SCREENS = path.join(ROOT, "results", "screens");
const OUT = path.join(__dirname, "Chapter5_Evidence_Pack.docx");
const M = JSON.parse(fs.readFileSync(path.join(ROOT, "results", "metrics.json")));
const FONT = "Calibri", W = 9360, ACCENT = "1F4E79";

const T = (text, o = {}) => new TextRun({ text, font: FONT, ...o });
const P = (text, o = {}) => new Paragraph({ spacing: { after: 120 }, children: [T(text, o)] });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [T(t)] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [T(t)] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [T(t)] });
const B = (t) => new Paragraph({ numbering: { reference: "b", level: 0 }, spacing: { after: 40 }, children: [T(t)] });
const NOTE = (t) => new Paragraph({ spacing: { before: 60, after: 120 },
  shading: { type: ShadingType.CLEAR, fill: "FFF4D6", color: "auto" },
  border: { left: { style: BorderStyle.SINGLE, size: 18, color: "E3A13B", space: 6 } }, children: [T(t)] });
const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
function TABLE(head, rows, widths) {
  const total = widths.reduce((a, b) => a + b, 0);
  const ws = widths.map((w) => Math.round(w / total * W)); ws[ws.length - 1] += W - ws.reduce((a, b) => a + b, 0);
  const cell = (t, i, h) => new TableCell({ width: { size: ws[i], type: WidthType.DXA },
    borders: { top: border, bottom: border, left: border, right: border },
    shading: h ? { type: ShadingType.CLEAR, fill: "DCE6F1", color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: [new Paragraph({ children: [T(String(t), { size: 19, bold: h })] })] });
  return [new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: ws,
    rows: [new TableRow({ tableHeader: true, children: head.map((t, i) => cell(t, i, true)) }),
      ...rows.map((r) => new TableRow({ children: r.map((t, i) => cell(t, i, false)) }))] }),
    new Paragraph({ children: [], spacing: { after: 160 } })];
}
const TESTS = (rows) => TABLE(["Test case", "Test steps", "Expected result", "Actual result", "Status"], rows, [1.2, 1.9, 1.5, 2.0, 0.6]);

let fig = 0;
function SHOT(file, caption, shows, section) {
  fig++;
  const f = path.join(file.includes("/") ? ROOT : SCREENS, file);
  const img = fs.readFileSync(f);
  const isWide = !file.includes("/");
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: "png", data: img,
      transformation: isWide ? { width: 600, height: 338 } : { width: 600, height: 288 } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
      children: [T(`Evidence ${fig}: ${caption}`, { bold: true, size: 20 })] }),
    new Paragraph({ spacing: { after: 40 }, children: [T("What it shows: ", { bold: true, size: 19 }), T(shows, { size: 19 })] }),
    new Paragraph({ spacing: { after: 240 }, children: [T("Use in: ", { bold: true, size: 19 }), T(section, { size: 19 }),
      T(`   (file: ${file.includes("/") ? file : "results/screens/" + file})`, { size: 17, color: "7F7F7F" })] }),
  ];
}
const pct = (x) => (x * 100).toFixed(1).replace(/\.0$/, "") + "%";
const o = (m) => M[m].overall;

const body = [
  new Paragraph({ spacing: { before: 2000 }, alignment: AlignmentType.CENTER,
    children: [T("Chapter 5 Evidence Pack", { bold: true, size: 52, color: ACCENT })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 },
    children: [T("Outline, screenshots, test-case tables and results data for Chapter 5: System Implementation", { size: 26 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 1000 },
    children: [T("Esborn Kihiu · evidence captured on the lab on 15 October 2026, 23:40 to 23:55", { italics: true, size: 22 })] }),
  NOTE("This pack is source material, not chapter text. The outline lists what each section should cover and which evidence supports it; the screenshots are real full-screen captures from the lab; the tables record what the lab actually did. Write the chapter paragraphs yourself, in your own words, and follow Strathmore's rules on acknowledging AI assistance."),

  H1("1. Outline of Chapter 5 (guideline structure)"),
  P("Headings follow the guideline report's Chapter 5. Under each heading: what to cover, and the evidence in this pack that supports it."),
  H2("5.1 Introduction"),
  B("Purpose of the chapter: how the system was built and how it was tested against the requirements (Table 3.2)."),
  B("What the reader will find: modules, environment, test cases, detection results, discussion."),
  H2("5.2 System Implementation"),
  H3("5.2.1 Key modules of the system"),
  B("Table of modules and their purpose: Table A in section 3 of this pack."),
  H3("5.2.2 Development environment"),
  B("Hardware: one laptop, Kali Linux (kernel 7.1.5), 7.1 GiB usable memory."),
  B("Software and versions: Docker; Containerlab 0.81.0; Arista cEOS-lab 4.36.2F; FreeRADIUS 3.2.1; Python 3.14 with scikit-learn 1.8.0, pandas 2.3.3, Netmiko; Zabbix 7.0 (server, web, PostgreSQL)."),
  B("How the lab is built: zt-dev.clab.yml lists devices and links; lab-up.sh checks memory, deploys one node at a time, waits for the switches, applies configs over SSH, logs users in with 802.1X, starts and registers Zabbix, runs six self-tests."),
  B("Evidence 1 (lab containers)."),
  H3("5.2.3 Access control module (802.1X and RADIUS)"),
  B("802.1X on acc1 ports Et2 to Et4 (and Et7 for a new desk); PEAP/MSCHAPv2 from wpa_supplicant; FreeRADIUS at 10.10.10.5 returns the VLAN (Tunnel-Private-Group-Id): bob 10, alice 20, guest1 30."),
  B("Ports stay closed until a login succeeds; the VLAN follows the user's identity, not the port."),
  B("Evidence 2 (logged-in users by VLAN)."),
  H3("5.2.4 Segmentation and policy module"),
  B("ZT_POLICY on core Ethernet1 inbound (Table 4.2); why on the trunk port (cEOS-lab has no ACLs on VLAN interfaces); lines 71 to 79 reserved for automatic blocks."),
  B("Edge iptables: default DROP, NAT to the internet, inside to DMZ only TCP 80, DMZ never starts connections inward."),
  B("Evidence 6 (rule counters), Evidence 7 (DMZ isolation)."),
  H3("5.2.5 Traffic collection and feature extraction module"),
  B("SPAN on acc1: Et2, Et3, Et4 copied to Et6 (SIEM); tcpdump streamed to the pipeline; failed logins read from the RADIUS log."),
  B("Eight features per PC per 10-second window (Table 4.3)."),
  B("Evidence 3 (mirror session)."),
  H3("5.2.6 Anomaly detection module"),
  B("Isolation Forest (200 trees, StandardScaler) trained on unlabelled traffic with rare attacks; threshold = 99th percentile of a separate normal run (-0.019); plus the rule: 5 or more failed logins in a window."),
  B("Evidence 21 (score distribution chart)."),
  H3("5.2.7 Automated response module"),
  B("Classification order and actions (Table 4.4): DoS = block IP (ZT_POLICY deny line); port scan and brute force = quarantine (RADIUS rule, VLAN 99, port bounce); insider = disable account; off-hours or unclassified = alert only. Infrastructure addresses protected; actions logged and reversible."),
  B("Evidence 9 (block line 71), Evidence 11 (quarantine)."),
  H3("5.2.8 Monitoring and alerting module"),
  B("Every node pushes its traffic, CPU and memory every 30 s; the pipeline pushes scores, alerts and actions; two dashboard pages; email alert action configured (sending not yet working, see Table F)."),
  B("Evidence 18 (network health), Evidence 19 (threat detection)."),
  H2("5.3 System Testing and Results"),
  H3("5.3.1 Authentication and access control testing"),
  B("Table B (test cases TC1 to TC4); Evidence 2 and 4."),
  H3("5.3.2 Segmentation and lateral movement testing"),
  B("Table C (TC5 to TC9); Evidence 5, 6, 7."),
  H3("5.3.3 Unit testing of the software components"),
  B("Table D (offline test suites); Evidence 17."),
  H3("5.3.4 Anomaly detection testing"),
  B("Datasets (Table G), method (5-fold leave-one-run-out), results of the three designs (Table H), per intensity, classification accuracy; Evidence 21 to 23."),
  H3("5.3.5 Automated response testing"),
  B("Table E (TC10 to TC15) with Evidence 8 to 16; timings (Table I)."),
  H3("5.3.6 Monitoring and performance testing"),
  B("Table F; Evidence 18 to 20; memory limits (lowest free memory 1,272 MB in the rehearsal; the out-of-memory incident when a browser was also open)."),
  H2("5.4 Discussion of the results"),
  B("Points to discuss: normal-only training could not see features that never vary (0% brute force and off-hours); mixed training fixed it; slow brute force needed the rule; alert-only design kept false alarms harmless; comparison with the literature in Chapter 2; limitations (simulated traffic, simulated night-time, small lab, 8 GB RAM, same-VLAN traffic not filtered)."),
  B("Validation against FR1 to FR8 (Table 3.2)."),

  H1("2. Screenshots"),
  P("Full-screen captures taken on the lab laptop with shot.sh, screens.sh and zabbix_shots.sh. Each terminal capture shows the command at the top and its real output."),
  ...SHOT("01_lab_nodes.png", "Lab containers running", "All ten lab containers up after lab-up.sh (two switches, edge, web, RADIUS, SIEM and four PCs).", "5.2.2"),
  ...SHOT("02_dot1x_hosts.png", "802.1X sessions on the access switch", "bob SUCCESS in VLAN 10 ADMIN, alice in 20 STAFF, guest1 in 30 GUEST.", "5.2.3, Table B TC1"),
  ...SHOT("03_span_session.png", "Port mirroring to the SIEM", "Monitor session 1: sources Et2, Et3, Et4 (both directions), destination Et6.", "5.2.5"),
  ...SHOT("04_wrong_password.png", "Login with a wrong password", "guest1 FAILED on Et4 with no VLAN; ping to its own gateway 10.10.30.1: 100% packet loss.", "5.3.1, Table B TC2"),
  ...SHOT("05_lateral_movement.png", "Lateral movement attempt from the guest PC", "Pings from guest-pc to the admin PC (10.10.10.50) and the staff PC (10.10.20.50) fail; the DMZ web page is returned.", "5.3.2, Table C TC5 to TC7"),
  ...SHOT("06_zt_policy_counters.png", "ZT_POLICY counters after the attempt", "Line 50 (guest to admin) and line 60 (guest to staff) each matched 2 packets.", "5.2.4, 5.3.2"),
  ...SHOT("07_dmz_isolation.png", "DMZ cannot reach the inside", "Ping from the web server to RADIUS fails; the edge FORWARD chain shows the DROP rule for DMZ to inside counting packets.", "5.2.4, Table C TC8"),
  ...SHOT("08_detector_dos.png", "Detector during the DoS attack", "guest-pc score above the threshold, flagged by the model; dos -> BLOCKED 10.10.30.50, 1.2 s after the window closed.", "5.3.5, Table E TC10"),
  ...SHOT("09_dos_blocked.png", "Block applied on the core switch", "New line 71 deny ip host 10.10.30.50 any matched 290 packets; guest-pc BLOCKED, staff-pc still gets the web page. (The long command at the top wrapped and is partly cut; the full command is in screens.sh.)", "5.2.7, Table E TC10"),
  ...SHOT("10_detector_portscan.png", "Detector during the port scan", "portscan -> QUARANTINED guest-pc, 1.9 s after the window closed.", "Table E TC11"),
  ...SHOT("11_portscan_quarantined.png", "Guest PC in quarantine", "guest1 SUCCESS in VLAN 99 QUARANTINE, address 10.10.99.30, no web access.", "5.2.7, Table E TC11"),
  ...SHOT("12_detector_bruteforce.png", "Detector during the brute-force attack", "Flagged by the failed-login rule; bruteforce -> QUARANTINED guest-pc, 1.9 s.", "Table E TC12"),
  ...SHOT("13_detector_insider.png", "Detector during the insider data theft", "insider -> DISABLED account alice, 1.9 s.", "Table E TC13"),
  ...SHOT("14_insider_disabled.png", "Account disabled", "alice FAILED on Et3 with no VLAN; staff-pc ping to its gateway: 100% packet loss.", "Table E TC13"),
  ...SHOT("15_detector_offhours.png", "Detector during the off-hours session", "offhours -> ALERT ONLY, 1.1 s; the full history of the run is visible in this window.", "Table E TC14"),
  ...SHOT("16_offhours_no_block.png", "Off-hours user not cut off", "staff-pc still reaches the DMZ web server after the alert.", "Table E TC14"),
  ...SHOT("17_offline_tests.png", "Offline test suites", "All four suites end with ALL TESTS PASSED.", "5.3.3, Table D"),
  ...SHOT("18_zabbix_health.png", "Zabbix network health page (Firefox)", "Security alerts list, host availability, packets and bytes per second with the attack spikes.", "5.2.8, Table F"),
  ...SHOT("19_zabbix_detection.png", "Zabbix threat detection and response page (Firefox)", "Anomaly scores per PC crossing the threshold line during the attacks; security alerts; last response action per host (blocked, quarantined, disabled, alert only).", "5.2.8, Table F"),
  ...SHOT("20_zabbix_problems.png", "Zabbix problems list (Firefox)", "The security alerts raised by the pipeline, with times and hosts.", "5.3.6, Table F"),
  ...SHOT("results/score_distribution.png", "Anomaly score of every test window (chart)", "Normal windows below the threshold; attack windows above it; brute force on both sides.", "5.2.6, 5.3.4"),
  ...SHOT("results/detection_by_type.png", "Detection rate by attack type for three designs (chart)", "Normal-only, mixed and hybrid designs per attack type.", "5.3.4"),
  ...SHOT("results/confusion_matrix.png", "Confusion matrix of the hybrid detector (chart)", "907 TN, 10 FP, 0 FN, 100 TP over five folds.", "5.3.4"),

  H1("3. Tables (records of what the lab did)"),
  H2("Table A: Modules of the system"),
  ...TABLE(["Module", "Purpose", "Implemented in"], [
    ["Lab environment", "Builds and rebuilds the network", "zt-dev.clab.yml, lab-up.sh, lab-down.sh"],
    ["Access control", "802.1X login, VLAN by identity", "acc1.cfg, FreeRADIUS"],
    ["Segmentation and policy", "Limits traffic between VLANs; isolates the DMZ", "ZT_POLICY (core), edge-fw.sh"],
    ["Traffic collection", "Copies user traffic; 8 features per PC per 10 s", "SPAN on acc1, zt_collector.py"],
    ["Anomaly detection", "Isolation Forest plus failed-login rule", "zt_model.py"],
    ["Automated response", "Block, quarantine, disable or alert", "zt_respond.py"],
    ["Pipeline", "Runs collection, scoring and response continuously", "zt_pipeline.py"],
    ["Monitoring and alerting", "Node health, scores, alerts, actions; email action", "Zabbix 7.0, zt_zbx_push.py, zbx_email_setup.py"]], [1.4, 2.4, 2.2]),
  H2("Table B: Authentication and access control test cases"),
  ...TESTS([
    ["TC1 Valid 802.1X login", "Lab built; PCs log in; show dot1x hosts", "Each user authenticated in the VLAN of the role", "bob VLAN 10, alice 20, guest1 30, all SUCCESS (Evidence 2)", "Passed"],
    ["TC2 Wrong password", "guest-pc logs in with a wrong password", "Port stays closed, no network", "Et4 FAILED, no VLAN; 100% loss to gateway (Evidence 4)", "Passed"],
    ["TC3 Re-authentication after reconnect", "Unplug staff-pc; plug back in", "Session removed; new login required", "alice removed on unplug; SUCCESS again on replug; RADIUS accept count 3 to 4 (guide Exercise 3, tested 15 Oct)", "Passed"],
    ["TC4 New user onboarding", "Plug in new-pc as carol with no account; create account; reload RADIUS; reconnect", "Rejected without account; staff VLAN after", "FAILED with Access-Reject; then carol SUCCESS VLAN 20 STAFF (guide Exercise 6, tested 15 Oct)", "Passed"]]),
  H2("Table C: Segmentation and lateral movement test cases"),
  ...TESTS([
    ["TC5 Guest to admin PC", "Ping 10.10.10.50 from guest-pc", "Blocked", "100% loss; ZT_POLICY line 50 matched 2 packets (Evidence 5, 6)", "Passed"],
    ["TC6 Guest to staff PC", "Ping 10.10.20.50 from guest-pc", "Blocked", "100% loss; line 60 matched 2 packets (Evidence 5, 6)", "Passed"],
    ["TC7 Guest to DMZ web", "curl http://10.10.40.10 from guest-pc", "Allowed", "Page returned: ZT-DMZ-web-server (Evidence 5)", "Passed"],
    ["TC8 DMZ to inside", "Ping RADIUS from the web server", "Blocked by the edge", "100% loss; edge DROP rule counted the packets (Evidence 7)", "Passed"],
    ["TC9 Lab self-tests", "Run lab-up.sh", "Six connectivity checks pass", "6 of 6 PASS on every rebuild", "Passed"]]),
  H2("Table D: Unit test suites"),
  ...TABLE(["Suite", "What it checks", "Checks", "Result"], [
    ["test_collector.py", "RADIUS log parsing, features, windowing, pcap reader", "10", "All passed"],
    ["test_traffic.py", "Labelling rules, after-effect, lab-only targets, secret handling", "9", "All passed"],
    ["test_respond.py", "Switch commands, de-duplication, protection, quarantine and disable logic", "10", "All passed"],
    ["test_zbx_push.py", "Node counters, CPU calculation, Zabbix sender protocol", "3", "All passed"]], [1.6, 3.4, 0.7, 1.0]),
  H2("Table E: Automated response test cases (evidence run, 15 Oct 23:45 to 23:51)"),
  ...TESTS([
    ["TC10 DoS", "attack --mode dos (40 s) from guest-pc, detector running", "Flagged; source IP blocked", "Flagged by the model; BLOCKED 10.10.30.50 in 1.2 s; line 71 matched 290 packets; staff unaffected (Evidence 8, 9)", "Passed"],
    ["TC11 Port scan", "attack --mode portscan (40 s)", "Flagged; host quarantined", "QUARANTINED guest-pc in 1.9 s; VLAN 99, 10.10.99.30, no web access (Evidence 10, 11)", "Passed"],
    ["TC12 Brute force", "attack --mode bruteforce (40 s)", "Flagged; host quarantined", "Flagged by the failed-login rule; QUARANTINED guest-pc in 1.9 s (Evidence 12)", "Passed"],
    ["TC13 Insider data theft", "attack --mode insider (40 s) on staff-pc", "Flagged; account disabled", "DISABLED account alice in 1.9 s; Et3 FAILED (Evidence 13, 14)", "Passed"],
    ["TC14 Off-hours session", "attack --mode offhours (40 s) on staff-pc", "Alert only; no access change", "ALERT ONLY in 1.1 s; staff-pc still reaches the web (Evidence 15, 16)", "Passed"],
    ["TC15 Normal users", "Normal traffic on all PCs throughout", "No block, quarantine or disable of a normal user", "2 alert-only false alarms (admin-pc 23:47:58, staff-pc 23:49:18); no access changed", "Passed"]]),
  H2("Table F: Monitoring test cases"),
  ...TESTS([
    ["TC16 Node metrics", "lab-up.sh; push loop every 30 s", "All nodes report", "9 nodes, 63 values per cycle, 0 failed; all hosts available (Evidence 18)", "Passed"],
    ["TC17 Scores, alerts, actions", "Run attacks with the pipeline", "Scores, alerts and actions visible", "Score spikes above threshold, alerts and last actions shown (Evidence 19, 20); rehearsal: 113 scores and 6 actions received", "Passed"],
    ["TC18 Email alerts", "Security alert with email action configured", "Email to the administrator", "Not delivered: Gmail rejected the login (App Password not yet set up)", "Pending"]]),
  H2("Table G: Datasets"),
  ...TABLE(["Class", "Runs", "Attack windows", "Notes"], [
    ["Normal", "4 x 10 min", "0", "594 normal windows"],
    ["DoS", "5 x 60 s", "20", "40 to 120 requests/s"],
    ["Port scan", "5 x 60 s", "20", "10 to 50 ports/s"],
    ["Brute force", "5 x 60 s", "20", "1 to 8 attempts/s"],
    ["Insider", "5 x 60 s", "20", "0.5 to 2.5 MB/s"],
    ["Off-hours", "5 x 60 s", "20", "normal traffic marked as night"]], [1.4, 1.2, 1.2, 2.4]),
  H2("Table H: Detection results (5-fold, 100 attack and 917 normal windows)"),
  ...TABLE(["Design", "TP", "FN", "FP", "TN", "Accuracy", "Precision", "Detection rate", "F1", "FPR", "ROC-AUC"],
    [["IF, normal only", "normal-only"], ["IF, mixed", "mixed"], ["Hybrid (chosen)", "hybrid"]].map(([n, k]) => [n, o(k).tp, o(k).fn, o(k).fp, o(k).tn,
      pct(o(k).accuracy), o(k).precision.toFixed(3), pct(o(k).recall), o(k).f1.toFixed(3), pct(o(k).false_positive_rate), o(k).roc_auc.toFixed(3)]),
    [1.3, 0.45, 0.45, 0.45, 0.5, 0.7, 0.7, 0.75, 0.55, 0.55, 0.65]),
  P("Attack-type classification: " + pct(M.classification.accuracy) + " of 100 attack windows named correctly."),
  H2("Table I: Response timings (end of window to action applied)"),
  ...TABLE(["Attack", "Evidence run (15 Oct)", "Rehearsal with Zabbix (14 Oct)"], [
    ["DoS", "1.2 s", "1.2 s"], ["Port scan", "1.9 s", "1.9 s"], ["Brute force", "1.9 s", "1.9 s"],
    ["Insider", "1.9 s", "1.9 s"], ["Off-hours", "1.1 s", "1.1 s"]], [2, 2, 2]),

  H1("4. Appendix candidates (guideline report has these)"),
  B("Appendix A: Turnitin similarity report (you add it)."),
  B("Appendix B: Gantt chart: needs your real project dates (proposal, literature review, design, implementation, testing, report)."),
  B("Appendix C: Incident log extract of the evidence run: results/screens/incidents_screens_run.jsonl."),
  B("Appendix D: Extra screenshots not used in the chapter."),
];

const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", run: { size: 34, bold: true, color: ACCENT }, paragraph: { spacing: { before: 200, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", run: { size: 26, bold: true, color: ACCENT }, paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", run: { size: 23, bold: true, color: "404040" }, paragraph: { spacing: { before: 160, after: 60 }, outlineLevel: 2 } }] },
  numbering: { config: [{ reference: "b", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], size: 18 })] })] }) },
    children: body }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(OUT, b); console.log("wrote", OUT, `(${fig} screenshots)`); });
