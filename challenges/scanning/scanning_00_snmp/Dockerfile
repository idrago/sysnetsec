FROM debian:bookworm-slim
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get -y install snmpd \
    && rm -rf /var/lib/apt/lists/*

USER root

COPY snmpd.conf /etc/snmp/snmpd.conf
RUN chmod u+r /etc/snmp/snmpd.conf

# Flag — exposed in the SNMP sysLocation OID; students retrieve it via snmpwalk
# Update snmpd.conf to embed the flag in syslocation
RUN sed -i 's|syslocation.*|syslocation "flag{scan00_snmp_community_public}"|' /etc/snmp/snmpd.conf

# Start SNMP daemon
CMD ["snmpd", "-f", "-Lo", "-C", "-c", "/etc/snmp/snmpd.conf"]