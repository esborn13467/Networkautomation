FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    freeradius freeradius-utils openssl wpasupplicant iproute2 \
    iputils-ping tcpdump procps && rm -rf /var/lib/apt/lists/*
CMD ["sleep", "infinity"]
RUN sed -i 's/use_tunneled_reply = no/use_tunneled_reply = yes/' /etc/freeradius/3.0/mods-available/eap
RUN apt-get update && apt-get install -y --no-install-recommends \
    iptables curl python3 && rm -rf /var/lib/apt/lists/*
