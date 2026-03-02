FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive
USER root

# Vuln 1: Basic setup with a hardcoded dictionary password
# Vuln 2: User has full sudo rights without password
RUN apt-get update && \
    apt-get -y install --no-install-recommends \
        openssh-server \
        net-tools \
        vim-tiny \
        sudo && \
    rm -rf /var/lib/apt/lists/* && \
    # Create user with weak password
    useradd -ms /bin/bash student && \
    echo "student:password" | chpasswd && \
    # Give unrestricted sudo access without password
    echo "student ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers && \
    # Create required SSH directory
    mkdir -p /run/sshd

COPY sshd_config /etc/ssh/sshd_config

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd || exit 1

RUN echo "flag{ac00_sudo_nopasswd}" > /root/flag.txt && chmod 400 /root/flag.txt

# Set the default command
CMD ["/usr/sbin/sshd", "-D"]