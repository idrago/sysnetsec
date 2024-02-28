FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive

user root

RUN apt-get update \
    && apt-get -y install \
                        openssh-server \ 
                        iptables \
                        vim \
                        net-tools \
                        cron \
                        build-essential \
                        acl \
                        zsh \
                        sudo \
    && rm -rf /var/lib/apt/lists/*

COPY sshd_config /etc/ssh/sshd_config

# hardcoded password from a dictionary
RUN useradd -ms /bin/bash student
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN echo "student:password" | chpasswd

# Vuln: make has setuid bit set
RUN chmod u+s $(which make)
#RUN ln -sf /bin/zsh /bin/sh
