# FROM alpine:latest
# USER root
#
# RUN apk --no-cache add \
#         openssh-server \
#         openssh \
#         net-tools \
#         vim \
#         sudo && \
#     # Create required SSH directory
#     mkdir -p /run/sshd && \
#     # Setup SSH
#     ssh-keygen -A && \
#     # Create user with weak password
#     adduser -D -s /bin/ash student && \
#     echo "student:password" | chpasswd && \
#     # Give unrestricted sudo access without password
#     echo "student ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# # Copy SSH config (same as in original)
# COPY sshd_config /etc/ssh/sshd_config

# # Add healthcheck
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD pgrep sshd || exit 1

# # Set the default command
# CMD ["/usr/sbin/sshd", "-D"]


FROM debian:bookworm-slim
USER root

# Update and install required packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        openssh-server \
        openssh-client \
        net-tools \
        vim \
        sudo \
        procps && \
    # Clean up apt cache to reduce image size
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    # Create required SSH directory
    mkdir -p /run/sshd && \
    # Setup SSH (not needed in Debian as keys are auto-generated on first start)
    # Create user with weak password
    useradd -m -s /bin/bash student && \
    echo "student:password" | chpasswd && \
    # Give unrestricted sudo access without password
    echo "student ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Copy SSH config
COPY sshd_config /etc/ssh/sshd_config

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep sshd || exit 1

# Set the default command
CMD ["/usr/sbin/sshd", "-D"]