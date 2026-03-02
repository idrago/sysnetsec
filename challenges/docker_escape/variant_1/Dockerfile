FROM debian:bookworm-slim
USER root

# Variant 1: Capabilities escape (SYS_ADMIN + SYS_MODULE)
# The container runs with SYS_ADMIN and SYS_MODULE capabilities added via compose.
# SYS_ADMIN allows mount operations; SYS_MODULE allows loading kernel modules.
# Either can be used to escape container isolation.

RUN apt-get update && apt-get install -y --no-install-recommends \
        openssh-server \
        openssh-client \
        net-tools \
        vim \
        sudo \
        procps \
        kmod \
        libcap2-bin && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    mkdir -p /run/sshd && \
    useradd -m -s /bin/bash student && \
    echo "student:password" | chpasswd && \
    echo "student ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

COPY sshd_config /etc/ssh/sshd_config

# Flag — readable only by root
RUN echo "flag{de01_cap_sys_admin_escape}" > /root/flag.txt && chmod 400 /root/flag.txt

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd || exit 1

CMD ["/usr/sbin/sshd", "-D"]
