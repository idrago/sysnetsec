FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive
USER root

# Vuln 1: Weak password vulnerability
# Vuln 2: User-writable Python path in PYTHONPATH for root cron job
RUN apt-get update && \
    apt-get -y install --no-install-recommends \
        openssh-server \
        iptables \
        vim-tiny \
        net-tools \
        cron \
        acl \
        sudo \
        python3 && \
    rm -rf /var/lib/apt/lists/* && \
    # Create user with weak password (Vuln 1)
    useradd -ms /bin/bash student && \
    echo "student:password" | chpasswd && \
    # Critical vulnerability: Create user-writable Python path (Vuln 2)
    mkdir -p /usr/lib/python && \
    chown -R student:student /usr/lib/python && \
    # Create required SSH directory
    mkdir -p /run/sshd

COPY sshd_config /etc/ssh/sshd_config
COPY backup_script.py /root/backup_script.py

# Setup vulnerable cron job with custom PYTHONPATH
RUN echo "PYTHONPATH=/usr/lib/python" > /etc/cron.d/backup && \
    echo "* * * * * root /usr/bin/python3 /root/backup.py" >> /etc/cron.d/backup && \
    chmod 644 /etc/cron.d/backup

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd || exit 1

# Start both cron and SSH
CMD bash -c "cron && /usr/sbin/sshd -D"