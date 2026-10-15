#!/usr/bin/env python3
"""
zbx_email_setup.py - Zabbix emails every security alert to the administrator

Sets up, through the Zabbix API:
  1. media type "ZT Gmail": Gmail SMTP (smtp.gmail.com:587, STARTTLS) as SENDER
  2. the Admin user's email: RECIPIENT
  3. action "ZT security alerts by email": every problem whose name starts with
     "Security alert" (block, quarantine, disabled account, off-hours alert) is emailed,
     and so is its recovery

The Gmail App Password is never stored in the project. It is read from a private file
that only the user creates and can read:
    ~/.config/zt-zabbix/smtp_password      (chmod 600; spaces in the password are ignored)

lab-up.sh runs this after every rebuild, because Zabbix's database starts empty each time.

Usage:
  python zbx_email_setup.py          # configure (skips quietly if the password file is missing)
  python zbx_email_setup.py test     # raise a test security alert on guest-pc -> email
"""
import os
import sys
import time

import zbx_setup as zs

SENDER = "esbornchiira8@gmail.com"
RECIPIENT = "esborn.kihiu@strathmore.edu"
PASSWORD_FILE = os.path.expanduser("~/.config/zt-zabbix/smtp_password")
MEDIA = "ZT Gmail"
ACTION = "ZT security alerts by email"

SUBJECT = "[ZT Lab] {EVENT.NAME}"
BODY = """Zero Trust lab: security alert

Host:     {HOST.NAME}
Alert:    {EVENT.NAME}
Severity: {EVENT.SEVERITY}
Time:     {EVENT.DATE} {EVENT.TIME}
Event ID: {EVENT.ID}

Open Zabbix: http://localhost:8080  (Dashboards > ZT Lab overview > Threat detection and response)"""
RECOVERY_SUBJECT = "[ZT Lab] Resolved: {EVENT.NAME}"
RECOVERY_BODY = """Zero Trust lab: alert resolved

Host:     {HOST.NAME}
Alert:    {EVENT.NAME}
Resolved: {EVENT.RECOVERY.DATE} {EVENT.RECOVERY.TIME}
Duration: {EVENT.DURATION}"""


def read_password():
    try:
        st = os.stat(PASSWORD_FILE)
    except FileNotFoundError:
        return None
    if st.st_mode & 0o077:
        sys.exit(f"{PASSWORD_FILE} can be read by others; fix it with: chmod 600 {PASSWORD_FILE}")
    with open(PASSWORD_FILE) as f:
        return "".join(f.read().split())          # Google shows app passwords with spaces


def setup():
    password = read_password()
    if not password:
        print(f"   email alerts skipped: no {PASSWORD_FILE}")
        return
    zs.login()

    media = {
        "name": MEDIA, "type": 0, "status": 0,
        "smtp_server": "smtp.gmail.com", "smtp_port": 587, "smtp_helo": "gmail.com",
        "smtp_email": SENDER, "smtp_security": 1, "smtp_verify_peer": 1, "smtp_verify_host": 1,
        "smtp_authentication": 1, "username": SENDER, "passwd": password, "content_type": 0,
        "message_templates": [
            {"eventsource": 0, "recovery": 0, "subject": SUBJECT, "message": BODY},
            {"eventsource": 0, "recovery": 1, "subject": RECOVERY_SUBJECT, "message": RECOVERY_BODY},
        ],
    }
    old = zs.api("mediatype.get", {"filter": {"name": [MEDIA]}, "output": ["mediatypeid"]})
    if old:
        media["mediatypeid"] = old[0]["mediatypeid"]
        zs.api("mediatype.update", media)
        mtid = media["mediatypeid"]
    else:
        mtid = zs.api("mediatype.create", media)["mediatypeids"][0]

    admin = zs.api("user.get", {"filter": {"username": ["Admin"]}, "output": ["userid"],
                                "selectMedias": ["mediatypeid", "sendto", "active", "severity", "period"]})[0]
    medias = [m for m in admin["medias"] if m["mediatypeid"] != mtid]
    medias.append({"mediatypeid": mtid, "sendto": [RECIPIENT], "active": 0, "severity": 63,
                   "period": "1-7,00:00-24:00"})
    zs.api("user.update", {"userid": admin["userid"], "medias": medias})

    old = zs.api("action.get", {"filter": {"name": [ACTION]}, "output": ["actionid"]})
    if old:
        zs.api("action.delete", [old[0]["actionid"]])
    message = {"operationtype": 0, "opmessage_usr": [{"userid": admin["userid"]}],
               "opmessage": {"default_msg": 1, "mediatypeid": mtid}}
    zs.api("action.create", {
        "name": ACTION, "eventsource": 0, "status": 0, "esc_period": "1h",
        "filter": {"evaltype": 0, "conditions": [
            {"conditiontype": 3, "operator": 2, "value": "Security alert"}]},   # event name contains
        "operations": [message],
        "recovery_operations": [{"operationtype": 0, "opmessage_usr": [{"userid": admin["userid"]}],
                                 "opmessage": {"default_msg": 1, "mediatypeid": mtid}}],
    })
    print(f"   email alerts on: {SENDER} -> {RECIPIENT}")


def test():
    import zt_zbx_push as zbx
    print(zbx.send_alert("guest-pc", f"TEST email alert {time.strftime('%H:%M:%S')} (no action taken)"))
    print(f"Test alert raised on zt-guest-pc. The email should reach {RECIPIENT} within about a minute.")
    print("Check delivery in Zabbix: Reports > Action log. Close the test problem under Monitoring > Problems.")


if __name__ == "__main__":
    test() if len(sys.argv) > 1 and sys.argv[1] == "test" else setup()
