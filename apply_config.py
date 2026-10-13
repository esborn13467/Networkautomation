import sys
from netmiko import ConnectHandler

host, cfg = sys.argv[1], sys.argv[2]
dev = {"device_type": "arista_eos", "host": host,
       "username": "admin", "password": "admin"}
with ConnectHandler(**dev) as conn:
    conn.enable()
    out = conn.send_config_set(open(cfg).read().splitlines())
    print(out)
    conn.save_config()
