FROM debian:bookworm-slim
ARG DEBIAN_FRONTEND=noninteractive
USER root

# Vuln 1: Weak password vulnerability
# Vuln 2: Student can write nginx configs that run as root
# Vuln 3: Auto-reload of nginx config allows for quick exploitation
RUN apt-get update && \
    apt-get -y install --no-install-recommends \
        openssh-server \
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
    chmod 777 /etc/nginx/conf.d && \
    chown root:root /etc/nginx/conf.d && \
    # Create required SSH directory
    mkdir -p /run/sshd && \
    # Create and set permissions for nginx logs
    mkdir -p /var/log/nginx && \
    touch /var/log/nginx/access.log /var/log/nginx/error.log && \
    chown -R root:root /var/log/nginx && \
    chmod 755 /var/log/nginx && \
    chmod 644 /var/log/nginx/access.log /var/log/nginx/error.log

COPY sshd_config /etc/ssh/sshd_config

# Setup nginx configuration
RUN echo "user root;\n\
events {\n\
    worker_connections 1024;\n\
}\n\
http {\n\
    include /etc/nginx/mime.types;\n\
    default_type application/octet-stream;\n\
    sendfile on;\n\
    keepalive_timeout 65;\n\
    access_log /var/log/nginx/access.log;\n\
    error_log /var/log/nginx/error.log;\n\
    include /etc/nginx/conf.d/*.conf;\n\
}" > /etc/nginx/nginx.conf && \
    # Create default site config
    echo "server { \n\
    listen 80; \n\
    location / { \n\
        root /var/www/html; \n\
    } \n\
}" > /etc/nginx/conf.d/default.conf && \
    # Vulnerability: Add auto-reload cron job (Vuln 3)
    echo "* * * * * root /usr/sbin/nginx -t && /usr/sbin/nginx -s reload\n" > /etc/cron.d/nginx-reload && \
        chmod 644 /etc/cron.d/nginx-reload

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd && pgrep nginx || exit 1

# Create required directory for nginx
RUN mkdir -p /var/www/html && \
    chown -R root:root /var/www/html && \
    chmod -R 755 /var/www/html && \
    echo "Welcome to the server" > /var/www/html/index.html

# Start all services
CMD nginx -t && service nginx start && service cron start && /usr/sbin/sshd -D