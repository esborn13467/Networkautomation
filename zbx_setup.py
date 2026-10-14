import json, os, subprocess, sys, urllib.request

URL = os.environ.get("ZBX_URL", "http://localhost:8080/api_jsonrpc.php")
USER = os.environ.get("ZBX_USER", "Admin")
PASSWORD = os.environ.get("ZBX_PASSWORD", "zabbix")   # set ZBX_PASSWORD if you changed it
COMMUNITY = "ztlab"
SNMP_HOSTS = ["core", "acc1"]
ICMP_HOSTS = ["radius", "siem", "edge", "web", "admin-pc", "staff-pc", "guest-pc"]
TOKEN = None

def api(method, params):
    headers = {"Content-Type": "application/json-rpc"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    body = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    with urllib.request.urlopen(urllib.request.Request(URL, body, headers), timeout=20) as r:
        out = json.load(r)
    if "error" in out:
        raise RuntimeError(f"{method}: {out['error'].get('data') or out['error']}")
    return out["result"]

def container_ip(name):
    fmt = '{{(index .NetworkSettings.Networks "clab").IPAddress}}'
    return subprocess.check_output(["docker", "inspect", "-f", fmt, f"clab-zt-{name}"], text=True).strip()

def templates(names):
    return api("template.get", {"output": ["templateid", "host"], "filter": {"host": names}})

def recreate(name, iface, tmpls, gid, macros=None):
    old = api("host.get", {"filter": {"host": [name]}, "output": ["hostid"]})
    if old:
        api("host.delete", [old[0]["hostid"]])
    params = {"host": name, "groups": [{"groupid": gid}], "interfaces": [iface],
              "templates": [{"templateid": t["templateid"]} for t in tmpls]}
    if macros:
        params["macros"] = macros
    api("host.create", params)
    print("created", name, iface["ip"])

def setup():
    gs = api("hostgroup.get", {"filter": {"name": ["ZT-Lab"]}})
    gid = gs[0]["groupid"] if gs else api("hostgroup.create", {"name": "ZT-Lab"})["groupids"][0]
    snmp_t = templates(["Arista by SNMP"]) or templates(["Network Generic Device by SNMP"])
    icmp_t = templates(["ICMP Ping"])
    if not snmp_t or not icmp_t:
        sys.exit("A template is missing in this Zabbix. Tell me and I will adjust.")
    print("using SNMP template:", snmp_t[0]["host"])
    for n in SNMP_HOSTS:
        iface = {"type": 2, "main": 1, "useip": 1, "ip": container_ip(n), "dns": "", "port": "161",
                 "details": {"version": 2, "bulk": 1, "community": "{$SNMP_COMMUNITY}"}}
        recreate(f"zt-{n}", iface, snmp_t, gid, [{"macro": "{$SNMP_COMMUNITY}", "value": COMMUNITY}])
    for n in ICMP_HOSTS:
        iface = {"type": 1, "main": 1, "useip": 1, "ip": container_ip(n), "dns": "", "port": "10050"}
        recreate(f"zt-{n}", iface, icmp_t, gid)
    zs = api("host.get", {"filter": {"host": ["Zabbix server"]}, "output": ["hostid"]})
    if zs:
        api("host.update", {"hostid": zs[0]["hostid"], "status": 1})
        print("disabled the built-in 'Zabbix server' host")

def status():
    for n in SNMP_HOSTS + ICMP_HOSTS:
        h = api("host.get", {"filter": {"host": [f"zt-{n}"]}, "output": ["hostid"],
                             "selectInterfaces": ["type", "available"]})
        if not h:
            print(f"{n:10} not registered"); continue
        if n in SNMP_HOSTS:
            a = h[0]["interfaces"][0]["available"]
            print(f"{n:10} SNMP", {"0": "unknown (wait a minute)", "1": "AVAILABLE", "2": "UNAVAILABLE"}[a])
        else:
            it = api("item.get", {"hostids": h[0]["hostid"], "filter": {"key_": "icmpping"},
                                  "output": ["lastvalue"]})
            v = it[0]["lastvalue"] if it else "no item yet"
            print(f"{n:10} ping", {"1": "UP", "0": "DOWN"}.get(v, v))

def login():
    global TOKEN
    TOKEN = api("user.login", {"username": USER, "password": PASSWORD})

if __name__ == "__main__":
    login()
    status() if len(sys.argv) > 1 and sys.argv[1] == "status" else setup()
