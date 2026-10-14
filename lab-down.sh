#!/usr/bin/env bash
cd "$(dirname "$0")"
python save_configs.py 2>/dev/null
pkill -f zt_zbx_push.py 2>/dev/null
docker rm -f zbx-web zbx-server zbx-db >/dev/null 2>&1 || true
sudo containerlab destroy -t zt-dev.clab.yml --cleanup
