FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive
USER root

# Vuln 1: Weak password vulnerability
# Vuln 2: Custom SUID binary potentially vulnerable to buffer overflow/command injection
RUN apt-get update && \
    apt-get -y install --no-install-recommends \
        openssh-server \
        iptables \
        vim-tiny \
        net-tools \
        cron \
        acl \
        build-essential \
        sudo && \
    rm -rf /var/lib/apt/lists/* && \
    # Create user with weak password (Vuln 1)
    useradd -ms /bin/bash student && \
    echo "student:password" | chpasswd && \
    # Create required SSH directory
    mkdir -p /run/sshd

COPY sshd_config /etc/ssh/sshd_config

# Compile and set up vulnerable SUID binary (Vuln 2)
COPY updater.c /tmp/updater.c
RUN gcc -o /etc/updater /tmp/updater.c && \
    rm -rf /tmp/updater.c && \
    # Critical vulnerability: Set SUID bit on custom binary
    chmod u+rxs /etc/updater

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd || exit 1

# Set the default command
CMD ["/usr/sbin/sshd", "-D"]