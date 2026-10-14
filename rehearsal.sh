#!/usr/bin/env bash
# Full demo rehearsal: Zabbix and its push loop running, end-to-end test of all five
# attacks (e2e_test.sh), memory sampled every 5 s, then a check through the Zabbix API
# that scores, alerts and actions arrived. Evidence: results/e2e_rehearsal_<time>/
# About 9 minutes. Keep other heavy programs closed while it runs.
cd "$(dirname "$0")" && source venv/bin/activate
OUT=results/e2e_rehearsal_$(date +%Y%m%d_%H%M)
mkdir -p "$OUT" logs
docker start zbx-db zbx-server zbx-web >/dev/null 2>&1
until python -c "import zbx_setup as z; z.login()" 2>/dev/null; do sleep 3; done
pgrep -f "python zt_zbx_push.py run" >/dev/null || { nohup python zt_zbx_push.py run --interval 30 > /tmp/zt_zbx_push.log 2>&1 & }
date +%s > "$OUT/start_epoch"
( while true; do echo "$(date +%T) $(free -m | awk '/Mem:/{print $7}')"; sleep 5; done ) > "$OUT/memory.log" &
SAMPLER=$!
./e2e_test.sh
kill $SAMPLER
cp logs/e2e_pipeline.log "$OUT/pipeline_output.log"
cp logs/e2e_steps.log "$OUT/attack_steps.log"
tail -n +$(( $(cat logs/.e2e_inc_start) + 1 )) logs/incidents.jsonl > "$OUT/incidents.jsonl"
python rehearsal_report.py "$OUT"
