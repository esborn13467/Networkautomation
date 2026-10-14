#!/usr/bin/env bash
# End-to-end test: pipeline running, normal traffic on all PCs, each attack in turn with a reset in between.
# About 8 minutes. Output: logs/e2e_pipeline.log, logs/e2e_steps.log, new lines in logs/incidents.jsonl
cd ~/Networkautomation/zt-project && source venv/bin/activate
mkdir -p logs; wc -l < logs/incidents.jsonl > logs/.e2e_inc_start 2>/dev/null || echo 0 > logs/.e2e_inc_start
python zt_respond.py reset >/dev/null
python zt_traffic.py background --seconds 560 >/dev/null
python -u zt_pipeline.py > logs/e2e_pipeline.log 2>&1 &
PIPE=$!
step() { echo "$(date +%T) $*" >> logs/e2e_steps.log; }
: > logs/e2e_steps.log
sleep 30;  step "ATTACK dos";        python zt_traffic.py attack --mode dos --seconds 40 >/dev/null
sleep 60;  step "reset";             python zt_respond.py reset >> logs/e2e_steps.log 2>&1
sleep 20;  step "ATTACK portscan";   python zt_traffic.py attack --mode portscan --seconds 40 >/dev/null
sleep 60;  step "reset";             python zt_respond.py reset >> logs/e2e_steps.log 2>&1
sleep 20;  step "ATTACK bruteforce"; python zt_traffic.py attack --mode bruteforce --seconds 40 >/dev/null
sleep 60;  step "reset";             python zt_respond.py reset >> logs/e2e_steps.log 2>&1
sleep 20;  step "ATTACK insider";    python zt_traffic.py attack --mode insider --seconds 40 >/dev/null
sleep 60;  step "reset";             python zt_respond.py reset >> logs/e2e_steps.log 2>&1
sleep 20;  step "ATTACK offhours";   python zt_traffic.py attack --mode offhours --seconds 40 >/dev/null
sleep 60;  step "end"
kill -TERM $PIPE; sleep 3; python zt_traffic.py stop
step "DONE"
