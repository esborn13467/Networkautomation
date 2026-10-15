#!/usr/bin/env bash
# Real terminal screenshots of the lab for the report (uses shot.sh). About 15 minutes.
# The detector runs in its own visible terminal window; it is screenshotted after each attack.
# Output: results/screens/*.png. Resets the lab at the end.
cd "$(dirname "$0")" && source venv/bin/activate
# solid terminal background for the screenshots (the desktop theme makes terminals see-through);
# the user's own setting is put back when the script ends, however it ends
OLD_MODE=$(xfconf-query -c xfce4-terminal -p /background-mode 2>/dev/null)
xfconf-query -c xfce4-terminal -p /background-mode -s TERMINAL_BACKGROUND_SOLID
trap '[ -n "$OLD_MODE" ] && xfconf-query -c xfce4-terminal -p /background-mode -s "$OLD_MODE"' EXIT
S() { ./shot.sh "$@"; }
SW() { echo "docker exec clab-zt-$1 Cli -p 15 -c '$2'"; }

python zt_respond.py reset >/dev/null 2>&1
S 01_lab_nodes "docker ps --filter name=clab-zt --format 'table {{.Names}}\t{{.Status}}'" 4
S 02_dot1x_hosts "$(SW acc1 'show dot1x hosts')" 6
S 03_span_session "$(SW acc1 'show monitor session')" 6

# wrong password on guest-pc
docker exec clab-zt-guest-pc pkill wpa_supplicant
docker exec clab-zt-guest-pc sh -c "sed 's/password=.*/password=\"WRONG\"/' /etc/wpa.conf > /tmp/bad.conf"
docker exec clab-zt-guest-pc wpa_supplicant -D wired -i eth1 -c /tmp/bad.conf -B >/dev/null; sleep 10
S 04_wrong_password "$(SW acc1 'show dot1x hosts'); docker exec clab-zt-guest-pc ping -c 2 -W 2 10.10.30.1" 10
docker exec clab-zt-guest-pc pkill wpa_supplicant; python apply_config.py clab-zt-acc1 bounce4.cfg >/dev/null
docker exec clab-zt-guest-pc wpa_supplicant -D wired -i eth1 -c /etc/wpa.conf -B >/dev/null; sleep 10

# lateral movement from the guest PC, then the rule counters
docker exec clab-zt-core Cli -p 15 -c "clear ip access-lists counters ZT_POLICY"
S 05_lateral_movement "docker exec clab-zt-guest-pc ping -c 2 -W 2 10.10.10.50; docker exec clab-zt-guest-pc ping -c 2 -W 2 10.10.20.50; docker exec clab-zt-guest-pc curl -s -m 4 http://10.10.40.10" 14
S 06_zt_policy_counters "$(SW core 'show ip access-lists ZT_POLICY')" 6
S 07_dmz_isolation "docker exec clab-zt-web ping -c 2 -W 2 10.10.10.5; docker exec clab-zt-edge iptables -L FORWARD -n -v" 10

# detector in its own window, normal traffic, then the five attacks
python zt_traffic.py background --seconds 900 >/dev/null
PT="zt-shot-pipeline-$$"
setsid -f xfce4-terminal --disable-server --title="$PT" --fullscreen --font="DejaVu Sans Mono 15" --working-directory="$PWD" \
  -x bash -c "printf '\$ python zt_pipeline.py\n'; source venv/bin/activate; python zt_pipeline.py; sleep 3600" >/dev/null 2>&1
sleep 3; PW=$(xdotool search --name "$PT" | head -1)
pipe_shot() { xdotool windowactivate "$PW" 2>/dev/null; sleep 1; import -window root "results/screens/$1.png"; echo "saved $1"; }
sleep 45
python zt_traffic.py attack --mode dos --seconds 40 >/dev/null; sleep 28
pipe_shot 08_detector_dos
S 09_dos_blocked "$(SW core 'show ip access-lists ZT_POLICY'); docker exec clab-zt-guest-pc curl -s -m 4 http://10.10.40.10 || echo BLOCKED; docker exec clab-zt-staff-pc curl -s -m 4 http://10.10.40.10" 12
sleep 10; python zt_respond.py reset >/dev/null; sleep 20
python zt_traffic.py attack --mode portscan --seconds 40 >/dev/null; sleep 28
pipe_shot 10_detector_portscan
S 11_portscan_quarantined "$(SW acc1 'show dot1x hosts'); docker exec clab-zt-guest-pc ip -4 -br addr show eth1; docker exec clab-zt-guest-pc curl -s -m 3 http://10.10.40.10 || echo 'no access'" 12
sleep 10; python zt_respond.py reset >/dev/null; sleep 20
python zt_traffic.py attack --mode bruteforce --seconds 40 >/dev/null; sleep 28
pipe_shot 12_detector_bruteforce
sleep 10; python zt_respond.py reset >/dev/null; sleep 20
python zt_traffic.py attack --mode insider --seconds 40 >/dev/null; sleep 28
pipe_shot 13_detector_insider
S 14_insider_disabled "$(SW acc1 'show dot1x hosts'); docker exec clab-zt-staff-pc ping -c 2 -W 2 10.10.20.1" 10
sleep 10; python zt_respond.py reset >/dev/null; sleep 20
python zt_traffic.py attack --mode offhours --seconds 40 >/dev/null; sleep 35
pipe_shot 15_detector_offhours
S 16_offhours_no_block "docker exec clab-zt-staff-pc curl -s -m 4 http://10.10.40.10" 5

# stop the detector cleanly (Ctrl+C in its window), stop traffic, reset
xdotool windowactivate "$PW" key --window "$PW" ctrl+c; sleep 4; xdotool windowclose "$PW" 2>/dev/null
python zt_traffic.py stop; python zt_respond.py reset >/dev/null
S 17_offline_tests "for t in test_collector test_traffic test_respond test_zbx_push; do echo \"== \$t\"; python \$t.py 2>/dev/null | grep -E '^PASS|ALL TESTS'; done" 25
echo "SCREENS DONE"
