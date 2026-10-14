from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoTimeoutException,
    NetmikoAuthenticationException,
)

device = {
    "device_type": "arista_eos",
    "host": "172.20.20.2",      # management IP from the deploy table
    "username": "admin",
    "password": "admin",        # lab only; we move this to an env var later
}

try:
    with ConnectHandler(**device) as conn:
        print("Connected. Prompt:", conn.find_prompt())
        print(conn.send_command("show version"))
except NetmikoAuthenticationException:
    print("Login failed: check username/password.")
except NetmikoTimeoutException:
    print("Timed out: switch still booting, or the IP is wrong.")
except Exception as e:
    print(f"Unexpected error: {e}")
