#!/usr/bin/env bash
# Collects the Phase 3 datasets: 4 x 10-minute normal runs, then 5 runs of each attack
# at five different intensities. About 65 minutes. Output: data/*.csv, log in data/collect.log
cd "$(dirname "$0")"
source venv/bin/activate
docker stop zbx-web zbx-server zbx-db >/dev/null 2>&1   # free RAM while capturing

for i in 1 2 3 4; do
  echo "=== normal run $i/4 (600 s)"
  python zt_traffic.py run --mode normal --seconds 600 --out data/normal_0$i.csv | grep ' packets -> '
done

declare -A RATES=(
  [dos]="40 60 80 100 120"
  [portscan]="10 20 30 40 50"
  [insider]="500000 1000000 1500000 2000000 2500000"
  [offhours]="0 0 0 0 0"
)
for mode in dos portscan insider offhours; do
  i=0
  for rate in ${RATES[$mode]}; do
    i=$((i+1))
    echo "=== $mode run $i/5 (rate $rate)"
    args="--mode $mode --seconds 60 --attack-start 10 --attack-len 40 --out data/${mode}_0$i.csv"
    [ "$rate" != 0 ] && args="$args --rate $rate"
    python zt_traffic.py run $args | grep ' packets -> '
  done
done
echo "=== DONE $(date)"
