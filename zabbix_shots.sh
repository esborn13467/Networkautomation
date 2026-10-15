#!/usr/bin/env bash
# Whole-screen screenshots of the Zabbix web interface in Firefox, for the report.
# Run after screens.sh, so the graphs and alerts of the attacks are in Zabbix's last hour.
# Uses a separate Firefox profile and the lab's local Zabbix login (Admin / zabbix).
# Output: results/screens/18_zabbix_health.png, 19_zabbix_detection.png, 20_zabbix_problems.png
cd "$(dirname "$0")" && source venv/bin/activate
OUT=results/screens; mkdir -p "$OUT"
DASH=$(python -c "import zbx_setup as z; z.login(); print(z.api('dashboard.get', {'filter': {'name': ['ZT Lab overview']}, 'output': ['dashboardid']})[0]['dashboardid'])")
BASE="http://localhost:8080"
PROFILE=$(mktemp -d)                                  # clean profile, removed at the end
setsid -f firefox --no-remote --profile "$PROFILE" --new-window "$BASE/index.php" >/dev/null 2>&1
for i in $(seq 1 40); do WID=$(xdotool search --onlyvisible --class firefox 2>/dev/null | tail -1); [ -n "$WID" ] && break; sleep 0.5; done
[ -z "$WID" ] && { echo "Firefox did not open"; exit 1; }
sleep 8; xdotool windowmove "$WID" 0 0; xdotool windowsize "$WID" 100% 100%; sleep 1   # whole screen
xdotool windowactivate --sync "$WID"; sleep 1
xdotool key ctrl+minus; xdotool key ctrl+minus; sleep 1   # zoom out so whole dashboards fit
# log in to the local Zabbix (the username field has focus on the login page)
xdotool type --delay 60 "Admin"; xdotool key Tab; xdotool type --delay 60 "zabbix"; xdotool key Return; sleep 6
go() { xdotool windowactivate --sync "$WID"; xdotool key ctrl+l; sleep 0.5; xdotool type --delay 20 "$1"; xdotool key Return; sleep "${2:-12}"; }
shot() { import -window root "$OUT/$1.png"; echo "saved $OUT/$1.png"; }
go "$BASE/zabbix.php?action=dashboard.view&dashboardid=$DASH&page=1&from=now-30m&to=now"; shot 18_zabbix_health
go "$BASE/zabbix.php?action=dashboard.view&dashboardid=$DASH&page=2&from=now-30m&to=now"; shot 19_zabbix_detection
go "$BASE/zabbix.php?action=problem.view&filter_name=Security&filter_show=3&filter_set=1" 8; shot 20_zabbix_problems
xdotool key ctrl+0; xdotool windowclose "$WID" 2>/dev/null; sleep 2
pkill -f -- "--profile $PROFILE" 2>/dev/null
echo "ZABBIX SHOTS DONE"
