FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive
USER root

# Vuln 1: Weak password vulnerability
# Vuln 2: Student's SSH public key is placed in root's authorized_keys
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
    # Setup SSH keys with privilege escalation vulnerability (Vuln 2)
    mkdir -p /home/student/.ssh && \
    mkdir -p /root/.ssh && \
    ssh-keygen -q -t rsa -N '' -f /home/student/.ssh/id_rsa && \
    # Critical vulnerability: copying student's public key to root's authorized_keys
    cp /home/student/.ssh/id_rsa.pub /root/.ssh/authorized_keys && \
    # Set proper SSH directory permissions
    chown -R student:student /home/student/.ssh && \
    chmod 700 /home/student/.ssh && \
    chmod 600 /home/student/.ssh/* && \
    chmod 600 /root/.ssh/* && \
    # Create required SSH directory
    mkdir -p /run/sshd

COPY sshd_config /etc/ssh/sshd_config

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd || exit 1

# Set the default command
CMD ["/usr/sbin/sshd", "-D"]