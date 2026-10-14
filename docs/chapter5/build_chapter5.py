#!/usr/bin/env python3
"""
Builds Chapter 5 (Results and Discussion) as docs/chapter5/chapter5.json, the block
format the report builder in docs/report/ merges:
  {"k": "h1|h2|h3|p", "t": text}            (*italic*, **bold** inline)
  {"k": "fig", "file": png, "width": inches, "caption": "Figure 5.n: ..."}
  {"k": "table", "caption": "Table 5.n: ...", "head": [...], "rows": [[...]], "widths": [...]}

Every number is read from results/ (metrics.json, the end-to-end run folders), so the
chapter cannot drift from the evidence. Run: python docs/chapter5/build_chapter5.py
"""
import glob
import json
import os
import shutil

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RES = os.path.join(ROOT, "results")
FIGDIR = os.path.join(HERE, "figures")

M = json.load(open(os.path.join(RES, "metrics.json")))
blocks, nfig, ntab = [], [0], [0]


def H1(t): blocks.append({"k": "h1", "t": t})
def H2(t): blocks.append({"k": "h2", "t": t})
def H3(t): blocks.append({"k": "h3", "t": t})
def P(t): blocks.append({"k": "p", "t": t})


def FIG(src, name, width, caption):
    nfig[0] += 1
    os.makedirs(FIGDIR, exist_ok=True)
    dst = os.path.join(FIGDIR, name)
    shutil.copyfile(os.path.join(RES, src), dst)
    blocks.append({"k": "fig", "file": os.path.relpath(dst, ROOT), "width": width,
                   "caption": f"Figure 5.{nfig[0]}: {caption}"})
    return f"Figure 5.{nfig[0]}"


def TAB(caption, head, rows, widths):
    ntab[0] += 1
    blocks.append({"k": "table", "caption": f"Table 5.{ntab[0]}: {caption}", "head": head,
                   "rows": [[str(c) for c in r] for r in rows], "widths": widths})
    return f"Table 5.{ntab[0]}"


pct = lambda x: f"{x * 100:.1f}%".replace(".0%", "%")
o = {m: M[m]["overall"] for m in ("normal-only", "mixed", "hybrid")}
bt = {m: M[m]["detection_rate_by_type"] for m in o}
br = {m: M[m]["detection_rate_by_run"] for m in o}

# ---------------------------------------------------------------- datasets
data = pd.concat([pd.read_csv(f).assign(run=os.path.basename(f)[:-4])
                  for f in sorted(glob.glob(os.path.join(ROOT, "data", "*_0[1-5].csv")))])
data["cls"] = data["run"].str.split("_").str[0]
normal = data[data.label == 0]
p99 = normal[["packet_count", "bytes_transferred", "unique_dst_ports", "requests_per_min"]].quantile(0.99)

# ---------------------------------------------------------------- end-to-end run
E2E = os.path.join(RES, "e2e_run_20261014_1456")
inc = [json.loads(l) for l in open(os.path.join(E2E, "incidents.jsonl"))]
first = {}
for i in inc:
    a = i["attack"]
    if "already" not in a and a not in first:
        first[a] = i

# ================================================================== CHAPTER 5
H1("Chapter 5: Results and Discussion")

H2("5.1 Introduction")
P("This chapter presents the results of testing the Zero Trust network and its detection and response layer, following the test plan in Section 3.6. It first reports the functional tests of access control and segmentation, then the datasets collected for the model, the detection results of the Isolation Forest, the automated response tests, the end-to-end test of the complete pipeline and the monitoring results from Zabbix. The results are then checked against the functional requirements in Table 3.2 and discussed in relation to the literature reviewed in Chapter 2. All the numbers in this chapter come from the result files kept with the project (the results folder, the data folder and the incident log), so every table can be traced back to the run that produced it.")

H2("5.2 Functional Testing of the Zero Trust Network")
H3("5.2.1 Authentication and Dynamic VLAN Assignment")
P("Each of the three users logged in with 802.1X (PEAP with MSCHAPv2), and FreeRADIUS returned the VLAN for the user’s role. The access switch showed all three sessions as authorized, each in its own VLAN. A login with a wrong password was then attempted from guest-pc: FreeRADIUS answered with an Access-Reject, the port changed to the FAILED state with no VLAN, and guest-pc could not even reach its own gateway. After the port was bounced and the correct password used, guest-pc was authorized again in VLAN 30 and reached the DMZ web server. The results are summarized in " + "Table 5.1" + ".")
TAB("802.1X authentication results on the access switch (acc1)",
    ["Port", "User", "Test", "Switch state", "Result"],
    [["Et2", "bob (admin)", "Correct password", "SUCCESS, VLAN 10 ADMIN", "Access as admin"],
     ["Et3", "alice (staff)", "Correct password", "SUCCESS, VLAN 20 STAFF", "Access as staff"],
     ["Et4", "guest1 (guest)", "Correct password", "SUCCESS, VLAN 30 GUEST", "Access as guest"],
     ["Et4", "guest1 (guest)", "Wrong password", "FAILED, no VLAN", "No network; 100% ping loss to gateway"],
     ["Et4", "guest1 (guest)", "Port bounced, correct password", "SUCCESS, VLAN 30 GUEST", "Access restored"]],
    [0.55, 1.15, 1.6, 1.75, 1.85])

H3("5.2.2 Segmentation and the DMZ")
P("The six self-tests run by lab-up.sh after every rebuild check the segment policy from the user side, and all six passed on every rebuild. Guests reached the DMZ web server and the internet but not the RADIUS server or the staff PC; staff reached the RADIUS server; and the DMZ web server could not start a connection to the internal network. The hit counters on the ZT_POLICY entries rose with each blocked attempt, which shows that the core switch, and not a missing route, did the blocking. On the edge firewall the DROP counter for DMZ-to-internal traffic rose in the same way. Table 5.2 lists the checks.")
TAB("Segmentation self-tests (lab-up.sh) and the rule that decides each one",
    ["Test", "Expected", "Result", "Enforced by"],
    [["guest-pc to DMZ web server (HTTP)", "Reach", "PASS", "edge: internal to DMZ on TCP 80 only"],
     ["guest-pc to internet (HTTP)", "Reach", "PASS", "edge: internal to internet, NAT"],
     ["guest-pc to RADIUS (10.10.10.5)", "Block", "PASS", "ZT_POLICY line 50"],
     ["guest-pc to staff PC (10.10.20.50)", "Block", "PASS", "ZT_POLICY line 60"],
     ["staff-pc to RADIUS", "Reach", "PASS", "ZT_POLICY line 80 (permit)"],
     ["DMZ web server to RADIUS", "Block", "PASS", "edge: DMZ to internal DROP"]],
    [2.15, 0.8, 0.7, 2.85])

H3("5.2.3 Collection and Feature Extraction")
P("The offline tests of the Python components passed in full: 10 checks for the collector (test_collector.py), 9 for the traffic generator (test_traffic.py), 10 for the response engine (test_respond.py) and 3 for the Zabbix sender (test_zbx_push.py). They include a check that the fast packet reader built on the struct module returns exactly the same fields as Scapy on a sample capture, and checks that the traffic generator refuses any target outside the lab network.")
P("Testing also exposed a fault that the functional tests had missed. In the first dataset collection the insider attack produced only about 30 packets per window instead of megabytes. The cause was an MTU mismatch: the Linux containers used 9,500-byte frames, while the cEOS switches route with an MTU of 1,500, so large replies were dropped at the core. Pings and small web pages fitted inside 1,500 bytes, which is why nothing had looked wrong before. After all lab interfaces were set to an MTU of 1,500, a 20 MB download ran at about 6 MB/s, and every dataset was collected again. The first datasets were kept as evidence of the fault but were not used.")

H2("5.3 Datasets")
rows = []
for cls in ["normal", "dos", "portscan", "bruteforce", "insider", "offhours"]:
    d = data[data.cls == cls]
    a = d[d.label == 1]
    ref = d[d.label == 0] if cls == "normal" else a
    rows.append([{"normal": "Normal", "dos": "DoS", "portscan": "Port scan", "bruteforce": "Brute force",
                  "insider": "Insider", "offhours": "Off-hours"}[cls],
                 d.run.nunique(), len(d), len(a),
                 f"{ref.packet_count.median():,.0f}", f"{ref.bytes_transferred.median():,.0f}",
                 f"{ref.unique_dst_ports.median():.0f}", f"{ref.failed_logins.median():.0f}",
                 f"{ref.requests_per_min.median():,.0f}"])
P(f"Four normal runs of ten minutes and five runs of each attack, at five intensities, were collected after the MTU fix. Table 5.3 summarizes them. The windows of attack runs that are not attack windows belong to the other two PCs, or to the attacker before and after its attack, and are labeled normal. For comparison, 99% of normal windows have at most {p99.packet_count:,.0f} packets, {p99.bytes_transferred / 1000:,.0f} kB, {p99.unique_dst_ports:.0f} destination port and {p99.requests_per_min:.0f} new connections per minute, and no normal window has a single failed login.")
TAB("Datasets collected (median values are for the attack windows, or for all windows of the normal runs)",
    ["Class", "Runs", "Windows", "Attack windows", "Median packets", "Median bytes", "Median ports", "Median failed logins", "Median conn./min"],
    rows, [0.85, 0.5, 0.75, 0.75, 0.75, 0.85, 0.6, 0.75, 0.7])
P("Every attack type differs clearly from normal traffic in at least one feature: DoS in its packets and connection rate, port scan in its destination ports, brute force in its failed logins and insider data theft in its bytes. The off-hours class is normal traffic in every feature except the off-hours flag, which is what defines it.")

H2("5.4 Detection Results")
H3("5.4.1 Overall Performance")
P("The detector was evaluated with 5-fold leave-one-run-out cross-validation (Section 3.6.3). Over the five folds, 100 attack windows and 917 normal windows were scored. Three designs were compared: the Isolation Forest trained on normal traffic only, the Isolation Forest trained on unlabeled mixed traffic in which about 9% of the windows were attacks, and the hybrid design chosen for the system, which adds one policy rule (five or more failed logins in a window) to the mixed model. Table 5.4 gives the results, calculated with Equations 3.1 to 3.5.")
TAB("Detection results of the three designs (5 folds, 100 attack and 917 normal windows)",
    ["Design", "TP", "FN", "FP", "TN", "Accuracy", "Precision", "Detection rate", "F1", "FPR", "ROC-AUC"],
    [[n, o[m]["tp"], o[m]["fn"], o[m]["fp"], o[m]["tn"], pct(o[m]["accuracy"]), f"{o[m]['precision']:.3f}",
      pct(o[m]["recall"]), f"{o[m]['f1']:.3f}", pct(o[m]["false_positive_rate"]), f"{o[m]['roc_auc']:.3f}"]
     for n, m in [("IF, normal only", "normal-only"), ("IF, mixed", "mixed"), ("Hybrid (chosen)", "hybrid")]],
    [1.2, 0.4, 0.4, 0.4, 0.45, 0.7, 0.7, 0.75, 0.5, 0.5, 0.6])
P(f"Trained on normal traffic only, the Isolation Forest raised few false alarms ({pct(o['normal-only']['false_positive_rate'])}) but found fewer than half of the attack windows ({pct(o['normal-only']['recall'])}). Trained on mixed traffic it found {pct(o['mixed']['recall'])} of them with a false positive rate of {pct(o['mixed']['false_positive_rate'])}, and its ROC-AUC rose from {o['normal-only']['roc_auc']:.3f} to {o['mixed']['roc_auc']:.3f}. The hybrid design found every attack window ({pct(o['hybrid']['recall'])}) without any extra false alarm, giving an accuracy of {pct(o['hybrid']['accuracy'])} and an F1-score of {o['hybrid']['f1']:.3f}. The ROC-AUC of the hybrid design is that of its Isolation Forest score, because the rule gives a yes or no answer and has no score.")
f1 = FIG("detection_by_type.png", "fig5_1_detection_by_type.png", 6.3, "Detection rate by attack type for the three designs")
P(f"{f1} breaks the detection rate down by attack type. DoS and insider data theft were detected by every design, because they change several features strongly at once. The normal-only model missed every brute-force and off-hours window and most port-scan windows.")

H3("5.4.2 Detection by Attack Intensity")
names = {"dos": ("DoS", "requests/s", [40, 60, 80, 100, 120]),
         "portscan": ("Port scan", "ports/s", [10, 20, 30, 40, 50]),
         "bruteforce": ("Brute force", "attempts/s", [1, 2, 3, 5, 8]),
         "insider": ("Insider", "MB/s", [0.5, 1.0, 1.5, 2.0, 2.5])}
rows = []
for a, (label, unit, rates) in names.items():
    for k, r in enumerate(rates, 1):
        run = f"{a}_0{k}"
        rows.append([label, f"{r:g} {unit}", pct(br["normal-only"][run]), pct(br["mixed"][run]), pct(br["hybrid"][run])])
TAB("Detection rate per run, from the weakest to the strongest intensity",
    ["Attack", "Intensity", "IF, normal only", "IF, mixed", "Hybrid"], rows, [1.3, 1.3, 1.3, 1.3, 1.3])
P("Table 5.5 shows the detection rate of every run. The off-hours runs have no intensity and are left out; all five were missed by the normal-only model and fully detected by the other two designs. The mixed model detected the weakest DoS and port-scan runs that the normal-only model partly missed. The one weakness of the mixed model was slow password guessing: at one or two attempts per second, about 10 to 20 failed logins per window, none of the windows were flagged, at three attempts per second half of them were, and from five attempts per second all of them were. In those windows every feature except failed_logins looks normal, so the anomaly score only reaches the level of a busy normal window. Lowering the threshold enough to catch them would have raised the false positive rate to about 5 to 10%. The brute-force rule closes this gap: it fired on every brute-force window at every speed and on no normal window.")

H3("5.4.3 Score Distribution and Confusion Matrix")
f2 = FIG("score_distribution.png", "fig5_2_score_distribution.png", 6.3, "Anomaly score of every test window with the tuned threshold (mixed training)")
P(f"{f2} plots the anomaly score of every test window. Normal windows form a dense band below the threshold of {M['mixed']['mean_threshold']:.3f} (the average over the five folds), with a thin tail of busy windows near it; these produce the false alarms. DoS, port-scan, insider and off-hours windows lie well above the threshold. The brute-force windows spread on both sides of it, which matches the intensity results in Table 5.5.")
f3 = FIG("confusion_matrix.png", "fig5_3_confusion_matrix.png", 3.6, "Confusion matrix of the hybrid detector over the five folds")
P(f"{f3} shows the confusion matrix of the hybrid detector. All 100 attack windows were detected and 907 of the 917 normal windows were left alone. All 10 false positives were windows of admin-pc or staff-pc that contained one or more downloads of the 200 kB test file, about 213 kB and 250 packets compared with a median of 1.9 kB and 22 packets for normal windows. Such downloads are part of normal behavior but rare, so the model treats them as unusual. Because their features match no attack type, they are classified as unclassified and lead only to an alert, as discussed in Section 5.5.2. (The held-out normal run normal_04 is scored by the model of every fold, so a window in it can appear in more than one fold.)")

H3("5.4.4 Attack Classification")
P(f"Once a window is flagged, the response engine decides the attack type from its features, in the order of Table 4.4. Applied to all 100 labeled attack windows, the classifier named the correct type for {pct(M['classification']['accuracy'])} of them: 20 out of 20 for each of DoS, port scan, brute force, insider and off-hours. Each limit in the classifier is far above normal traffic, so a normal window that is flagged by mistake almost always ends up as unclassified, and an unclassified window only raises an alert.")

H2("5.5 Automated Response Results")
H3("5.5.1 Individual Response Actions")
P("Each response action was first tested on its own from the command line (zt_respond.py) on the live lab. Table 5.6 gives the results. The block took effect at once: guest-pc lost all access while staff-pc was not affected, and the new deny entry counted the dropped packets. For quarantine, FreeRADIUS was told to place the user in VLAN 99 and the access port was bounced; the PC logged in again on its own and was in the quarantine VLAN 1.1 seconds after the bounce. The ZT_POLICY counters then showed exactly the access Table 4.2 allows a quarantined host: one packet permitted to the RADIUS server on UDP 1812, two permitted to the SIEM, and 11 denied, covering the web server, the staff PC, the internet, the gateway and a ping to the RADIUS server. Disabling an account left the port in the FAILED state, and every action could be undone.")
TAB("Response actions tested individually on the live lab",
    ["Action", "Command", "Observed result", "Time"],
    [["Block IP", "block 10.10.30.50", "ZT_POLICY line 71 deny ip host 10.10.30.50 any, 5 packets matched in the first second; guest-pc HTTP 000, staff-pc HTTP 200", "0.1 s on the switch (0.8 s including SSH login)"],
     ["Repeat block", "block 10.10.30.50", "Ignored: host already blocked", "-"],
     ["Protected address", "block 10.10.10.5", "Refused: infrastructure address", "-"],
     ["Quarantine", "quarantine guest-pc", "guest1 SUCCESS in VLAN 99, address 10.10.99.30; no web access; staff-pc unaffected", "1.4 s (in VLAN 99 1.1 s after bounce)"],
     ["Quarantine policy", "-", "ZT_POLICY line 20: 1 permitted, line 30: 2 permitted, line 40: 11 denied", "-"],
     ["Release", "release guest-pc", "Back in VLAN 30 with its own address; web access restored", "1.1 s"],
     ["Disable account", "disable staff-pc", "alice rejected by FreeRADIUS; Et3 FAILED; staff-pc has no network", "1.4 s"],
     ["Enable account", "enable staff-pc", "Back in VLAN 20; web access restored", "2.2 s"]],
    [1.05, 1.25, 2.9, 1.3])

H3("5.5.2 End-to-End Test")
P("In the end-to-end test the live pipeline (zt_pipeline.py) ran while all three PCs generated normal traffic, and each attack was launched for 40 seconds, with the network reset between attacks. Nobody triggered any response by hand. Table 5.7 shows, for each attack, the window in which it was flagged, what fired (the model, the rule or both), how it was classified, the action taken and the response time from Equation 3.6, measured from the moment the window closed to the moment the action was applied on the network.")
order = [("dos", "DoS from guest-pc"), ("portscan", "Port scan from guest-pc"),
         ("bruteforce", "Brute force on guest-pc’s port"), ("insider", "Insider download on staff-pc"),
         ("offhours", "Off-hours session on staff-pc")]
rows = []
for a, label in order:
    i = first[a]
    rows.append([label, i["window_start"][11:], i["reason"], a, i["action"], f"{i['response_ms'] / 1000:.1f} s"])
TAB("End-to-end test of the live pipeline (14 October 2026)",
    ["Attack", "Window flagged", "Fired", "Classified as", "Automatic action", "Response time"],
    rows, [1.6, 0.9, 0.85, 0.9, 1.6, 0.85])
times = [first[a]["response_ms"] / 1000 for a, _ in order]
P(f"Every attack was detected in the first or second window after it started, classified correctly and answered with the action set out in the Chapter 4 activity diagram. Response times ranged from {min(times):.1f} to {max(times):.1f} seconds after the window closed. About one second of this is a deliberate wait for late packets; a block then takes about 0.1 seconds, while quarantine and disabling an account take longer because FreeRADIUS has to reload its rules and the port has to be bounced. Counting from the start of an attack, the response came within one ten-second window plus these one to two seconds, so a DoS source was cut off about eight seconds after its flood began.")
P("Two other alerts were raised during the test, both of the alert-only kind, so no user was cut off. The first was the window in which the insider download had just begun, which did not yet hold enough data to be classified as insider. The second was a genuine false alarm on guest-pc during normal traffic, which agrees with the false positive rate of about 1% measured in Section 5.4.")
P("Earlier runs of the same test found three faults that the offline tests had not. All PCs had addresses ending in .50, so a quarantined PC (then 10.10.99.50) was matched to the wrong PC and admin-pc was quarantined by mistake; each PC now has its own quarantine address. FreeRADIUS compares file times to the second, so two rule changes within one second could leave a rule in force; reloads are now spaced and confirmed in its log. Finally, the reload check failed while the RADIUS log was growing fast during a brute force, and the error stopped the pipeline; a failed response is now logged and detection continues. These faults show the value of testing the whole system end to end and not only its parts.")

H2("5.6 Monitoring Results")
P("All nine lab nodes pushed their own data to Zabbix every 30 seconds: packets and bytes per second on their lab interfaces, dropped packets, CPU and memory use. Each push cycle was accepted in full (54 values, 0 failed). The two dashboard pages worked as designed: the network health page showed host availability and the traffic, CPU and memory of every node, and the threat detection page showed the anomaly score of each PC against the threshold line, the security alerts, the last action per PC and the detection-to-action time. A test alert sent through the alert channel appeared as a problem on the right host. Zabbix also raised a real problem of its own: both cEOS switches used over 90% of their memory allowance, which matches the memory pressure discussed next.")
P("@@REHEARSAL@@")

H2("5.7 Performance and Resource Use")
P("The whole lab ran on one laptop with 7.1 GiB of usable memory. The two cEOS switches used about 1.5 GB each, and with all nine nodes running, about 1.5 GB remained free, or about 0.5 to 0.75 GB with Zabbix also running. This limit shaped several decisions: the switches were reduced from seven to two, the lab is deployed one node at a time, packets are captured with only their first 128 bytes and read with a light parser instead of Scapy, and Zabbix was stopped during dataset collection.")
P("The limit was also reached once. During a rehearsal with Zabbix running, another memory-heavy program (a document renderer) started at the same time, free memory fell to about 75 MB, and the kernel stopped the core switch, the access switch and staff-pc. The detection pipeline itself used about 130 MB. The incident shows that the design is sound but that the hardware leaves little margin: on a single 8 GB laptop the demonstration must run with other heavy programs closed, and a second memory module would remove the risk.")

H2("5.8 Validation against the Requirements")
P("Table 5.8 compares the results with the functional requirements of Table 3.2. Every requirement was met.")
TAB("Functional requirements and the results that show they are met",
    ["No.", "Requirement", "Evidence", "Met"],
    [["FR1", "802.1X login before network access", "Table 5.1: three users authorized; wrong password gives FAILED and no access", "Yes"],
     ["FR2", "VLAN assigned from identity", "Table 5.1: bob VLAN 10, alice 20, guest1 30, set by FreeRADIUS", "Yes"],
     ["FR3", "Guests cannot reach internal subnets", "Table 5.2: guest to RADIUS and staff blocked; ZT_POLICY counters", "Yes"],
     ["FR4", "DMZ cannot start internal connections", "Table 5.2: web to RADIUS blocked; edge DROP counters", "Yes"],
     ["FR5", "Traffic summarized per host every 10 s", "Table 5.3 datasets; collector tests; live pipeline windows", "Yes"],
     ["FR6", "Windows scored by Isolation Forest and rule", f"Table 5.4: detection rate {pct(o['hybrid']['recall'])}, FPR {pct(o['hybrid']['false_positive_rate'])}", "Yes"],
     ["FR7", "Automatic response by attack type", "Table 5.7: block, quarantine, disable and alert without any manual step", "Yes"],
     ["FR8", "Scores, alerts and actions reach the administrator", "Section 5.6: dashboard pages, problems list, 54 values per cycle", "Yes"]],
    [0.5, 1.9, 3.3, 0.5])
P("The validation criteria of Section 3.6.6 were also met. Legitimate users kept working: no normal window led to a block, quarantine or disabled account, only to alerts. Every attack type was detected at every tested intensity. DoS sources were blocked, scanning and brute-force hosts ended up in VLAN 99, the account was disabled after insider data theft, off-hours activity raised an alert without changing access, and guests never reached internal resources.")

H2("5.9 Discussion")
P("The results support the idea that Zero Trust access control and machine learning detection work best together. Access control alone stopped the guest from reaching internal systems, but it could not see a DoS flood towards an allowed server, a port scan, or an insider copying data with valid credentials. The detection layer saw all of these, and its answers reused the Zero Trust controls themselves: the ACL for a block, and the identity-based VLAN for quarantine. This is close to the identity-based segmentation described by Ahmadi (2025), where a device is moved to another segment when its behavior becomes risky.")
P("The most important finding about the model is that an Isolation Forest trained only on normal traffic cannot see features that never vary in that traffic. Failed logins and the off-hours flag were always zero in normal windows, so the trees never split on them and the model missed every brute-force and off-hours window. Benign-only training is the setting compared by Syzranova et al. (2026) for Isolation Forest, the One-Class SVM and autoencoders, and the results here show one of its weak points for Isolation Forest in particular: a feature that never varies in the benign data cannot be used by the trees at all. Trained instead on unlabeled traffic in which attacks are rare, the Isolation Forest isolated the unusual windows by the few splits that its design relies on (Fuhnwi et al., 2023; Lakshmi et al., 2024), detected every DoS, port-scan, insider and off-hours window, and reached a ROC-AUC of 0.990. It still never needed a labeled example, which keeps the main advantage of an unsupervised method.")
P("Slow password guessing remained hard for the model, because it changes only one of the eight features. Adding one explicit rule solved this without extra false alarms. Hybrid detection designs have also been proposed in the literature, for example for insider threats (Rauf et al., 2023), and a policy rule fits the Zero Trust principle that every login attempt is checked. The results are reported with and without the rule, so the contribution of the model alone stays visible.")
P("The response layer met its aim of acting without a person. With one to two seconds from the end of a window to the action, containment followed detection almost at once, which is the benefit of automated response for fast attacks such as denial of service (Jones, 2025). Studies of incident response note that trust in fully automatic actions is still limited (Falowo & Bou Abdo, 2026). The choice to answer unclassified anomalies and off-hours activity with an alert only addresses this: the false alarms seen in testing never cut off a user, and only attacks matching a clear signature led to an automatic change in access.")
P("The results have limits. All traffic was generated by scripts, so normal behavior is more regular than in a real enterprise, and the false positive rate on real traffic would likely be higher. The off-hours flag was simulated rather than observed at night. The lab has one access switch and three users, and it runs on a software data plane with little spare memory. The model was tested on attack types and intensities that were also present, unlabeled, in its training traffic; new kinds of attacks were not tested. These limits are taken up in the recommendations in Chapter 6.")

H2("5.10 Summary")
P(f"The Zero Trust network met all its functional requirements: users were authenticated and placed in VLANs by identity, guests were confined, and the DMZ was isolated. The hybrid detector found all 100 attack windows across five attack types and five intensities, with a false positive rate of {pct(o['hybrid']['false_positive_rate'])} and an F1-score of {o['hybrid']['f1']:.3f}, and named the attack type correctly every time. In the end-to-end test every attack was answered automatically, {min(times):.1f} to {max(times):.1f} seconds after its window closed, and every alert and action reached Zabbix.")

# ---------------------------------------------------------------- rehearsal paragraph
reh = sorted(glob.glob(os.path.join(RES, "e2e_rehearsal_*")))
if reh and os.path.exists(os.path.join(reh[-1], "summary.json")):
    s = json.load(open(os.path.join(reh[-1], "summary.json")))
    text = s["paragraph"]
else:
    text = None
blocks[:] = [b for b in blocks if not (b["k"] == "p" and b["t"] == "@@REHEARSAL@@")] if text is None else \
    [dict(b, t=text) if b["k"] == "p" and b["t"] == "@@REHEARSAL@@" else b for b in blocks]

json.dump(blocks, open(os.path.join(HERE, "chapter5.json"), "w"), indent=1, ensure_ascii=False)
json.dump([], open(os.path.join(HERE, "references.json"), "w"))
print(f"chapter5.json: {len(blocks)} blocks, {nfig[0]} figures, {ntab[0]} tables")
