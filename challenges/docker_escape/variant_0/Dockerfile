FROM debian:bookworm-slim
USER root

# Variant 0: Docker socket escape
# The container has the Docker CLI installed; docker.sock is mounted from the host.
# This allows escaping via: docker run --rm -v /:/host alpine chroot /host

RUN apt-get update && apt-get install -y --no-install-recommends \
        openssh-server \
        openssh-client \
        net-tools \
        vim \
        sudo \
        procps \
        curl \
        ca-certificates \
        gnupg && \
    # Install Docker CLI
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/debian bookworm stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    # SSH setup
    mkdir -p /run/sshd && \
    # Create student user
    useradd -m -s /bin/bash student && \
    echo "student:password" | chpasswd && \
    echo "student ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

COPY sshd_config /etc/ssh/sshd_config

# Flag — readable only by root; student must escape to read it
RUN echo "flag{de00_docker_sock_escape}" > /root/flag.txt && chmod 400 /root/flag.txt

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd || exit 1

CMD ["/usr/sbin/sshd", "-D"]
