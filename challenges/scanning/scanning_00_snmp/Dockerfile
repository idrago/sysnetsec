FROM debian:bookworm-slim
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get -y install snmpd \
    && rm -rf /var/lib/apt/lists/*

USER root

COPY snmpd.conf /etc/snmp/snmpd.conf
RUN chmod u+r /etc/snmp/snmpd.conf

# Start SNMP daemon
CMD ["snmpd", "-f", "-Lo", "-C", "-c", "/etc/snmp/snmpd.conf"]