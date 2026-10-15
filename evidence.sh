#!/usr/bin/env bash
# Collects real outputs from the running lab as evidence for the report (Chapter 5):
# Zero Trust checks, then the five attacks with the live pipeline running.
# Each output is saved with the exact command and the time it ran. About 10 minutes.
# Output: results/evidence_<time>/NN_name.txt (+ pipeline.log). Resets the lab at the end.
cd "$(dirname "$0")" && source venv/bin/activate
OUT=results/evidence_$(date +%Y%m%d_%H%M); mkdir -p "$OUT"; N=0
cap() {  # cap <name> <command...>: run on the host and save "$ command" + output
  N=$((N+1)); local f="$OUT/$(printf %02d $N)_$1.txt"; shift
  { echo "# $(date '+%Y-%m-%d %H:%M:%S')"; echo "\$ $*"; bash -c "$*" 2>&1; } > "$f"
  echo "saved $f"
}
SW() { echo "docker exec clab-zt-$1 Cli -p 15 -c \"$2\""; }

python zt_respond.py reset >/dev/null 2>&1
cap lab_nodes "docker ps --filter name=clab-zt --format 'table {{.Names}}\t{{.Status}}'"
cap dot1x_hosts "$(SW acc1 'show dot1x hosts')"
cap span_session "$(SW acc1 'show monitor session')"
cap interfaces "$(SW acc1 'show interfaces status')"

# wrong password on guest-pc, then restore
docker exec clab-zt-guest-pc pkill wpa_supplicant
docker exec clab-zt-guest-pc sh -c "sed 's/password=.*/password=\"WRONG\"/' /etc/wpa.conf > /tmp/bad.conf"
docker exec clab-zt-guest-pc wpa_supplicant -D wired -i eth1 -c /tmp/bad.conf -B >/dev/null; sleep 10
cap wrong_password "$(SW acc1 'show dot1x hosts') ; docker exec clab-zt-guest-pc ping -c 2 -W 2 10.10.30.1"
docker exec clab-zt-guest-pc pkill wpa_supplicant; python apply_config.py clab-zt-acc1 bounce4.cfg >/dev/null
docker exec clab-zt-guest-pc wpa_supplicant -D wired -i eth1 -c /etc/wpa.conf -B >/dev/null; sleep 10

# lateral movement from the guest PC
docker exec clab-zt-core Cli -p 15 -c "clear ip access-lists counters ZT_POLICY"
cap lateral_movement "docker exec clab-zt-guest-pc ping -c 2 -W 2 10.10.10.50; docker exec clab-zt-guest-pc ping -c 2 -W 2 10.10.20.50; docker exec clab-zt-guest-pc ping -c 2 -W 2 10.10.10.5; docker exec clab-zt-guest-pc curl -s -m 4 http://10.10.40.10"
cap zt_policy_counters "$(SW core 'show ip access-lists ZT_POLICY')"
cap dmz_to_inside "docker exec clab-zt-web ping -c 2 -W 2 10.10.10.5; docker exec clab-zt-edge iptables -L FORWARD -n -v"

# live pipeline with normal traffic, then the five attacks
python zt_traffic.py background --seconds 700 >/dev/null
python -u zt_pipeline.py > "$OUT/pipeline.log" 2>&1 &
PIPE=$!
sleep 40
python zt_traffic.py attack --mode dos --seconds 40 >/dev/null; sleep 30
cap dos_blocked "$(SW core 'show ip access-lists ZT_POLICY') ; docker exec clab-zt-guest-pc curl -s -m 4 http://10.10.40.10 || echo BLOCKED; docker exec clab-zt-staff-pc curl -s -m 4 http://10.10.40.10"
sleep 15; python zt_respond.py reset >/dev/null; sleep 20
docker exec clab-zt-core Cli -p 15 -c "clear ip access-lists counters ZT_POLICY"
python zt_traffic.py attack --mode portscan --seconds 40 >/dev/null; sleep 30
docker exec clab-zt-guest-pc sh -c 'ping -c 2 -W 1 10.10.10.20; ping -c 2 -W 1 10.10.20.50' >/dev/null 2>&1
cap portscan_quarantined "$(SW acc1 'show dot1x hosts') ; docker exec clab-zt-guest-pc ip -4 -br addr show eth1; docker exec clab-zt-guest-pc curl -s -m 3 http://10.10.40.10 || echo 'no access'; $(SW core 'show ip access-lists ZT_POLICY')"
sleep 15; python zt_respond.py reset >/dev/null; sleep 20
python zt_traffic.py attack --mode bruteforce --seconds 40 >/dev/null; sleep 30
cap bruteforce_quarantined "$(SW acc1 'show dot1x hosts') ; docker exec clab-zt-radius grep -c 'Sent Access-Reject' /tmp/radius.log"
sleep 15; python zt_respond.py reset >/dev/null; sleep 20
python zt_traffic.py attack --mode insider --seconds 40 >/dev/null; sleep 30
cap insider_disabled "$(SW acc1 'show dot1x hosts') ; docker exec clab-zt-staff-pc ping -c 2 -W 2 10.10.20.1"
sleep 15; python zt_respond.py reset >/dev/null; sleep 20
python zt_traffic.py attack --mode offhours --seconds 40 >/dev/null; sleep 40
cap offhours_alert "docker exec clab-zt-staff-pc curl -s -m 4 http://10.10.40.10"
sleep 10
kill -TERM $PIPE; sleep 3; python zt_traffic.py stop
cap incidents "tail -n 12 logs/incidents.jsonl"
cap offline_tests "for t in test_collector test_traffic test_respond test_zbx_push; do echo \"== \$t\"; python \$t.py 2>/dev/null | grep -E '^PASS|ALL TESTS'; done"
python zt_respond.py reset >/dev/null 2>&1
echo "EVIDENCE DONE $OUT"
