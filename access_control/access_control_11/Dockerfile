FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive
USER root

# Vuln 1: Weak password vulnerability
# Vuln 2: PostgreSQL superuser access and trust authentication
# Vuln 3: No authentication required for local connections
RUN apt-get update && \
    apt-get -y install --no-install-recommends \
        openssh-server \
        iptables \
        vim-tiny \
        net-tools \
        cron \
        acl \
        sudo \
        postgresql && \
    rm -rf /var/lib/apt/lists/* && \
    # Create user with weak password (Vuln 1)
    useradd -ms /bin/bash student && \
    echo "student:password" | chpasswd && \
    # Create required SSH directory
    mkdir -p /run/sshd

COPY sshd_config /etc/ssh/sshd_config

# Configure PostgreSQL with vulnerable settings
USER postgres
RUN /etc/init.d/postgresql start && \
    # Critical vulnerability: Create superuser account (Vuln 2)
    psql -c "CREATE USER student WITH PASSWORD 'dbpass' SUPERUSER CREATEDB CREATEROLE;" && \
    psql -c "CREATE DATABASE studentdb OWNER student;"

# Configure dangerous trust authentication
USER root
RUN echo "# Critical vulnerability: Trust authentication for all local connections (Vuln 3)\n\
local   all             postgres                              trust\n\
local   all             student                               trust\n\
host    all             all             127.0.0.1/32          trust" > /etc/postgresql/13/main/pg_hba.conf

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd && pgrep postgres || exit 1

# Start both PostgreSQL and SSH
CMD service postgresql start && /usr/sbin/sshd -D