FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive
USER root

# Vuln 1: Weak password vulnerability (dictionary attack)
# Vuln 2: Student user has read/write access to /etc/shadow
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
    # Give user rwx access to shadow file (Vuln 2)
    setfacl -m u:student:rwx /etc/shadow && \
    # Create required SSH directory
    mkdir -p /run/sshd

COPY sshd_config /etc/ssh/sshd_config

# Add a healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd || exit 1

RUN echo "flag{ac01_shadow_acl}" > /root/flag.txt && chmod 400 /root/flag.txt

# Set the default command
CMD ["/usr/sbin/sshd", "-D"]