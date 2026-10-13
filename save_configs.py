from netmiko import ConnectHandler

NODES = {"core": "clab-zt-core", "acc1": "clab-zt-acc1"}

for name, host in NODES.items():
    try:
        with ConnectHandler(device_type="arista_eos", host=host,
                            username="admin", password="admin") as conn:
            conn.enable()
            cfg = conn.send_command("show running-config")
            with open(f"configs/{name}-running.cfg", "w") as f:
                f.write(cfg + "\n")
            print(f"saved configs/{name}-running.cfg ({len(cfg.splitlines())} lines)")
    except Exception as e:
        print(f"{name}: FAILED ({e})")
