FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive
USER root

# Vuln 1: Weak password vulnerability
# Vuln 2: SUID bit set on find command, allowing privilege escalation
RUN apt-get update && \
    apt-get -y install --no-install-recommends \
        openssh-server \
        vim-tiny \
        acl \
        sudo && \
    rm -rf /var/lib/apt/lists/* && \
    # Create user with weak password (Vuln 1)
    useradd -ms /bin/bash student && \
    echo "student:password" | chpasswd && \
    # Critical vulnerability: Set SUID bit on find command (Vuln 2)
    chmod u+s /usr/bin/find && \
    # Create required SSH directory
    mkdir -p /run/sshd

COPY sshd_config /etc/ssh/sshd_config

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd || exit 1

# Set the default command
CMD ["/usr/sbin/sshd", "-D"]