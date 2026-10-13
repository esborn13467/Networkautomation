#!/usr/bin/env bash
cd "$(dirname "$0")"
source venv/bin/activate
sudo -v || exit 1

avail=$(free -m | awk '/^Mem:/{print $7}')
if [ "$avail" -lt 4500 ]; then
  echo "Only ${avail} MB available (need 4500). Close the browser and heavy apps, then rerun."; exit 1
fi

echo "== 1/6 deploying lab (one node at a time)"
sudo containerlab deploy -t zt-dev.clab.yml --max-workers 1 || exit 1

echo "== 2/6 waiting for switches"
for sw in core acc1; do
  echo -n "   $sw "
  until docker exec clab-zt-$sw Cli -p 15 -c "show version" >/dev/null 2>&1; do echo -n .; sleep 5; done
  echo " up"
done

echo "== 3/6 configuring switches (errors only are shown)"
apply() { echo "   $1 <- $2"; python apply_config.py "clab-zt-$1" "$2" | grep '^%' || true; }
apply core core.cfg
apply core fix_mgmt.cfg
apply core snmp.cfg
apply core policy.cfg
apply acc1 acc1.cfg
apply acc1 snmp.cfg

echo "== 4/6 logging in the three PCs (802.1X)"
for pc in admin-pc staff-pc guest-pc; do
  docker exec clab-zt-$pc wpa_supplicant -D wired -i eth1 -c /etc/wpa.conf -B -f /tmp/wpa.log >/dev/null
done
sleep 25
addr() { docker exec clab-zt-$1 sh -c "ip addr add $2 dev eth1 2>/dev/null; ip route replace default via $3"; }
addr admin-pc 10.10.10.50/24 10.10.10.1
addr staff-pc 10.10.20.50/24 10.10.20.1
addr guest-pc 10.10.30.50/24 10.10.30.1

echo "== 5/6 starting Zabbix and registering hosts"
docker rm -f zbx-web zbx-server zbx-db >/dev/null 2>&1 || true
bash zabbix-up.sh >/dev/null
echo -n "   waiting for Zabbix API "
for i in $(seq 1 60); do
  python zbx_setup.py status >/dev/null 2>&1 && break
  echo -n .; sleep 5
done
echo
python zbx_setup.py

echo "== 6/6 self-test"
t() { d="$1"; want="$2"; shift 2
  if "$@" >/dev/null 2>&1; then got=reach; else got=block; fi
  if [ "$got" = "$want" ]; then echo "   PASS  $d"; else echo "   FAIL  $d (got $got)"; fi; }
t "guest -> web (DMZ)"     reach docker exec clab-zt-guest-pc curl -s -m 4 http://10.10.40.10
t "guest -> internet"      reach docker exec clab-zt-guest-pc curl -s -m 5 -o /dev/null http://example.com
t "guest -> RADIUS"        block docker exec clab-zt-guest-pc ping -c 1 -W 2 10.10.10.5
t "guest -> staff PC"      block docker exec clab-zt-guest-pc ping -c 1 -W 2 10.10.20.50
t "staff -> RADIUS"        reach docker exec clab-zt-staff-pc ping -c 1 -W 2 10.10.10.5
t "web (DMZ) -> RADIUS"    block docker exec clab-zt-web ping -c 1 -W 2 10.10.10.5
docker exec clab-zt-acc1 Cli -p 15 -c "show dot1x hosts"
free -h | head -2
