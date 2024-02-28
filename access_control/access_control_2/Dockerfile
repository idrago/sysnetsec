FROM debian:latest
ARG DEBIAN_FRONTEND=noninteractive

user root

RUN apt-get update \
    && apt-get -y install \
                        openssh-server \ 
                        iptables \
                        vim \
                        net-tools \
                        cron \
                        acl \
                        sudo \
    && rm -rf /var/lib/apt/lists/*

COPY sshd_config /etc/ssh/sshd_config

# hardcoded password from a dictionary
RUN useradd -ms /bin/bash student
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN echo "student:password" | chpasswd

# Vuln: ssh key from non-root user into root authorized_keys
RUN mkdir -p /home/student/.ssh \
    && mkdir -p /root/.ssh \ 
    && ssh-keygen -q -t rsa -N '' -f /home/student/.ssh/id_rsa \
    && cp /home/student/.ssh/id_rsa.pub /root/.ssh/authorized_keys \
    && chown -R student:student /home/student/.ssh \
    && chmod 700 /home/student/.ssh \
    && chmod 600 /home/student/.ssh/* \
    && chmod 600 /root/.ssh/* 
