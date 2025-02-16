FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive
USER root

# Vuln 1: Weak password vulnerability
# Vuln 2: Student can write nginx configs that run as root
# Vuln 3: Auto-reload of nginx config allows for quick exploitation
RUN apt-get update && \
    apt-get -y install --no-install-recommends \
        openssh-server \
        iptables \
        vim-tiny \
        net-tools \
        cron \
        acl \
        sudo \
        nginx && \
    rm -rf /var/lib/apt/lists/* && \
    # Create user with weak password (Vuln 1)
    useradd -ms /bin/bash student && \
    echo "student:password" | chpasswd && \
    # Critical vulnerability: Give student write access to nginx configs (Vuln 2)
    chmod 775 /etc/nginx/conf.d && \
    chown root:student /etc/nginx/conf.d && \
    # Create required SSH directory
    mkdir -p /run/sshd

COPY sshd_config /etc/ssh/sshd_config

# Setup nginx configuration
RUN echo "user root;" > /etc/nginx/nginx.conf && \
    echo "include /etc/nginx/conf.d/*.conf;" >> /etc/nginx/nginx.conf && \
    echo "events { worker_connections 1024; }" >> /etc/nginx/nginx.conf && \
    # Create default site config
    echo "server { \n\
    listen 80; \n\
    location / { \n\
        root /var/www/html; \n\
    } \n\
}" > /etc/nginx/conf.d/default.conf && \
    # Vulnerability: Add auto-reload cron job (Vuln 3)
    echo "* * * * * root nginx -t && systemctl reload nginx" > /etc/cron.d/nginx-reload && \
    chmod 644 /etc/cron.d/nginx-reload

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd && pgrep nginx || exit 1

# Start all services
CMD service nginx start && cron && /usr/sbin/sshd -D