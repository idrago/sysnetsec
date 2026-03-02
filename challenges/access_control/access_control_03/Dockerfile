FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive
USER root

# Vuln 1: Weak password vulnerability
# Vuln 2: World-writable root-owned script executed by root cron
RUN apt-get update && \
    apt-get -y install --no-install-recommends \
        openssh-server \
        vim-tiny \
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
COPY cache.sh /etc/cache.sh
RUN chown root:root /etc/cache.sh && \
    # Critical vulnerability: world-writable script executed by root cron
    chmod 777 /etc/cache.sh && \
    # Add script to root's crontab
    echo "* * * * * root /etc/cache.sh" >> /etc/cron.d/cache && \
    # Set proper permissions for cron job file
    chmod 644 /etc/cron.d/cache

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd || exit 1

RUN echo "flag{ac03_cron_writeable_script}" > /root/flag.txt && chmod 400 /root/flag.txt

# Set the default command
CMD bash -c "cron && /usr/sbin/sshd -D"