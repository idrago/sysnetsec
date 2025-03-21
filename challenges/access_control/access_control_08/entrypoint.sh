#!/bin/bash
set -x

echo "Starting initialization..."
/usr/sbin/sshd
echo "SSH started"

# Initialize PostgreSQL if needed
if [ ! -e "/var/lib/postgresql/15/main/postgresql.conf" ]; then
    echo "Initializing PostgreSQL..."
    su postgres -c "/usr/lib/postgresql/15/bin/initdb -D /var/lib/postgresql/15/main"
    
    echo "Setting up minimal configuration..."
    su postgres -c "echo \"listen_addresses = 'localhost'\" >> /var/lib/postgresql/15/main/postgresql.conf"
    
    su postgres -c "echo \"local   all             postgres                              trust
local   all             student                              trust
host    all             all             127.0.0.1/32         trust\" > /var/lib/postgresql/15/main/pg_hba.conf"

    # Start PostgreSQL temporarily to create user and database
    su postgres -c "/usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/15/main start"
    sleep 3  # Give it a moment to start up
    
    # VULN: Create student user with superuser privileges
    su postgres -c "createuser -s student"
    su postgres -c "createdb -O student studentdb"
    
    # Stop PostgreSQL to restart it in the foreground
    su postgres -c "/usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/15/main stop"
fi

# VULN give permission to the postgres user to access /root folder
setfacl -m u:postgres:rx /root
chmod 444 /root/flag.txt

echo "Starting PostgreSQL..."
exec su postgres -c "/usr/lib/postgresql/15/bin/postgres -D /var/lib/postgresql/15/main"