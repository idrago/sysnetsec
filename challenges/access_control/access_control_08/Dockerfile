FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive
USER root

# Minimal install with just what's needed
RUN apt-get update && \
    apt-get -y install --no-install-recommends \
        openssh-server \
        acl \
        postgresql && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -ms /bin/bash student && \
    echo "student:password" | chpasswd && \
    mkdir -p /run/sshd

COPY sshd_config /etc/ssh/sshd_config

# Proper PostgreSQL directory setup
RUN mkdir -p /var/lib/postgresql/15/main && \
    mkdir -p /var/run/postgresql && \
    chown -R postgres:postgres /var/lib/postgresql && \
    chown postgres:postgres /var/run/postgresql

COPY entrypoint.sh /
RUN chmod 700 /entrypoint.sh

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd && pgrep postgres || exit 1

RUN echo "flag{ac08_postgres_privesc}" > /root/flag.txt

CMD ["/entrypoint.sh"]