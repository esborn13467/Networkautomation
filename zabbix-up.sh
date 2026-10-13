set -e
NET=clab
docker run -d --name zbx-db --network $NET --restart unless-stopped \
  -e POSTGRES_USER=zabbix -e POSTGRES_PASSWORD=zbxpass -e POSTGRES_DB=zabbix \
  postgres:16-alpine
sleep 10
docker run -d --name zbx-server --network $NET --restart unless-stopped \
  -e DB_SERVER_HOST=zbx-db -e POSTGRES_USER=zabbix -e POSTGRES_PASSWORD=zbxpass -e POSTGRES_DB=zabbix \
  -e ZBX_CACHESIZE=16M -e ZBX_HISTORYCACHESIZE=8M -e ZBX_VALUECACHESIZE=8M -e ZBX_TRENDCACHESIZE=4M \
  -e ZBX_STARTPOLLERS=3 \
  zabbix/zabbix-server-pgsql:alpine-7.0-latest
docker run -d --name zbx-web --network $NET --restart unless-stopped -p 8080:8080 \
  -e ZBX_SERVER_HOST=zbx-server -e DB_SERVER_HOST=zbx-db \
  -e POSTGRES_USER=zabbix -e POSTGRES_PASSWORD=zbxpass -e POSTGRES_DB=zabbix \
  -e PHP_TZ=Africa/Nairobi \
  zabbix/zabbix-web-nginx-pgsql:alpine-7.0-latest
