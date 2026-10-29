# Archive

Files from earlier phases, kept for the project history. Nothing in the current lab uses them.

| File | Phase | What it was |
|---|---|---|
| test.clab.yml | 1A | One cEOS switch, first connection test |
| test_connection.py | 1A | First Netmiko SSH connection to a switch |
| phase1b.clab.yml, sw1.cfg | 1B | 802.1X proof of concept (one switch, RADIUS, one client) |
| zt.clab.yml | 2A | First full topology, replaced by zt-dev.clab.yml |
| zt-dev.clab.yml.bak | 2C | zt-dev topology before the web server and edge firewall were added |
| test_acl.cfg, clean_acl.cfg | 2B | Experiment proving ACLs work on ports but not on SVIs in cEOS |
| zt_collector.py.bak | 3 | Collector before the 14 Oct fast-pcap-reader upgrade |
| applypolicy.cfg, nopolicy.cfg | 2B | Manual toggles to attach or remove the ZT_POLICY ACL on the core while debugging; policy.cfg now does this in lab-up.sh |
| nospan.cfg | 3 | Manual toggle to remove the mirror session while debugging; span.cfg now sets it in lab-up.sh |
| zt-project-backup-20261013.tar.gz | 2 | Snapshot of the project folder taken on 13 Oct |
