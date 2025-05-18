FROM debian:bookworm-slim
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get -y install --no-install-recommends \
        openssh-server \
        net-tools \
        tcpdump \
        iptables \
        vim-tiny \
        sudo && \
    rm -rf /var/lib/apt/lists/* 

COPY firewall.sh /etc/firewall.sh
RUN chmod u+x /etc/firewall.sh

CMD ["bash", "-c", "/etc/firewall.sh && tail -f /dev/null"]