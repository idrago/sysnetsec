FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive
USER root

# Vuln 1: Weak password vulnerability
# Vuln 2: World-writable root-owned script executed by root cron
RUN apt-get update && \
    apt-get -y install --no-install-recommends \
        openssh-server \
        iptables \
        vim-tiny \
        net-tools \
        cron \
        acl \
        sudo && \
    rm -rf /var/lib/apt/lists/* && \
    # Create user with weak password (Vuln 1)
    useradd -ms /bin/bash student && \
    echo "student:password" | chpasswd && \
    # Create required SSH directory
    mkdir -p /run/sshd

COPY sshd_config /etc/ssh/sshd_config

# Setup vulnerable cron job (Vuln 2)
COPY secret.sh /etc/secret.sh
RUN chown root:root /etc/secret.sh && \
    # Critical vulnerability: world-writable script executed by root cron
    chmod 777 /etc/secret.sh && \
    # Add script to root's crontab
    echo "* * * * * root /etc/secret.sh" >> /etc/cron.d/secret && \
    # Set proper permissions for cron job file
    chmod 644 /etc/cron.d/secret

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd || exit 1

# Set the default command
CMD bash -c "cron && /usr/sbin/sshd -D"