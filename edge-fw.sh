set -e
iptables -F; iptables -t nat -F
iptables -P FORWARD DROP
iptables -P INPUT ACCEPT
# replies to anything we started
iptables -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
# internal VLANs (via core on eth1) may go out to the internet on eth0
iptables -A FORWARD -i eth1 -o eth0 -j ACCEPT
# internal VLANs may reach the DMZ web server only on port 80
iptables -A FORWARD -i eth1 -o eth2 -p tcp -d 10.10.40.10 --dport 80 -j ACCEPT
# DMZ may not start connections to internal networks; DMZ may use the internet
iptables -A FORWARD -i eth2 -o eth1 -j DROP
iptables -A FORWARD -i eth2 -o eth0 -j ACCEPT
# NAT toward the internet side
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
iptables -L FORWARD -n -v --line-numbers
