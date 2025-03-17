FROM alpine:latest
USER root

RUN apk --no-cache add \
        openssh-server \
        openssh \
        net-tools \
        vim \
        sudo && \
    # Create required SSH directory
    mkdir -p /run/sshd && \
    # Setup SSH
    ssh-keygen -A && \
    # Create user with weak password
    adduser -D -s /bin/ash student && \
    echo "student:password" | chpasswd && \
    # Give unrestricted sudo access without password
    echo "student ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Copy SSH config (same as in original)
COPY sshd_config /etc/ssh/sshd_config

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd || exit 1

# Set the default command
CMD ["/usr/sbin/sshd", "-D"]
