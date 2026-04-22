#!/bin/bash
# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

set -e

# Installed postgres version. May change when upgrading debian from 13 to a newer release.
POSTGRES_VERSION=17

# Data directories
POSTGRES_CLUSTER_DATA_DIRECTORY=/mnt/postgres_data
SECRETS_DATA_DIRECTORY=/mnt/secrets
TURING_DATA_DIRECTORY=/mnt/turing_data
TURING_ROOT_DIRECTORY=/root/turing

# Create data directories, if they do not exist
mkdir -p ${POSTGRES_CLUSTER_DATA_DIRECTORY}
mkdir -p ${SECRETS_DATA_DIRECTORY}
mkdir -p ${TURING_DATA_DIRECTORY}

# Generate a django secret key
DJANGO_SECRET_KEY_FILE="${SECRETS_DATA_DIRECTORY}/.django_secret_key"
if [[ ! -f "${DJANGO_SECRET_KEY_FILE}" ]]; then
    echo "Generating a django secret key"
    DJANGO_SECRET_KEY=$(cat /dev/urandom | tr -dc 'abcdefghijklmnopqrstuvwxyz0123456789!@#$^&*-_=+' | head -c 50; echo)
    echo ${DJANGO_SECRET_KEY} > ${DJANGO_SECRET_KEY_FILE}
else
    echo "Reusing existing django secret key"
    DJANGO_SECRET_KEY=$(cat "${DJANGO_SECRET_KEY_FILE}")
fi

# Generate a postgres password
POSTGRES_PASSWORD_FILE="${SECRETS_DATA_DIRECTORY}/.postgres_password"
if [[ ! -f "${POSTGRES_PASSWORD_FILE}" ]]; then
    echo "Generating a postgres password"
    POSTGRES_PASSWORD=$(cat /dev/urandom | tr -dc 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' | head -c 50; echo)
    POSTGRES_PASSWORD=${POSTGRES_PASSWORD} sh -c "echo '${POSTGRES_PASSWORD}\n${POSTGRES_PASSWORD}' | passwd postgres"
    echo ${POSTGRES_PASSWORD} > ${POSTGRES_PASSWORD_FILE}
else
    echo "Reusing existing postgres password"
    POSTGRES_PASSWORD=$(cat "${POSTGRES_PASSWORD_FILE}")
fi

# Hardcode postgres database name
POSTGRES_DATABASE_NAME="turing-dmf-db"
if [[ "${POSTGRES_DATABASE_NAME}" != *"-db" ]]; then
    echo "Expected database name ${POSTGRES_DATABASE_NAME} to end with -db"
    exit 1
fi

# Hardcode postgres cluster name
POSTGRES_CLUSTER_NAME=${POSTGRES_DATABASE_NAME/-db/-cluster}
if [[ "${POSTGRES_CLUSTER_NAME}" != *"-cluster" ]]; then
    echo "Expected cluster name ${POSTGRES_CLUSTER_NAME} to end with -cluster"
    exit 1
fi

# Create a new postgres cluster with data directory that matches the volume mounted in create_container.sh,
# if not already done previously
# Note that the marker file .postgres_cluster_created cannot be put in ${POSTGRES_CLUSTER_DATA_DIRECTORY},
# because the cluster needs to be re-created in every container. This is safe upon container destruction because
# postgres data direcory will not be cleared out when creating the cluster in a new container.
POSTGRES_CLUSTER_CREATED_FILE=${TURING_ROOT_DIRECTORY}/.postgres_cluster_created
if [[ ! -f ${POSTGRES_CLUSTER_CREATED_FILE} ]]; then
    echo "Creating a new postgres cluster"
    pg_dropcluster ${POSTGRES_VERSION} main
    pg_createcluster ${POSTGRES_VERSION} --datadir=${POSTGRES_CLUSTER_DATA_DIRECTORY} ${POSTGRES_CLUSTER_NAME} -- -E UTF8 --locale=C.utf8 --lc-messages=C
    cp /etc/postgresql/${POSTGRES_VERSION}/${POSTGRES_CLUSTER_NAME}/*.conf ${POSTGRES_CLUSTER_DATA_DIRECTORY}/
    touch ${POSTGRES_CLUSTER_CREATED_FILE}
else
    echo "Reusing existing postgres cluster"
fi

# Start postgresql service
echo "Starting postgresql service"
service postgresql start

# Initialize an empty postgres database, if not already done previously
POSTGRES_DATABASE_INITIALIZED_FILE=${POSTGRES_CLUSTER_DATA_DIRECTORY}/.postgres_database_initialized
if [[ ! -f ${POSTGRES_DATABASE_INITIALIZED_FILE} ]]; then
    echo "Initializing an empty postgres database"
    sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD '${POSTGRES_PASSWORD}';"
    sudo -u postgres createdb ${POSTGRES_DATABASE_NAME}
    touch ${POSTGRES_DATABASE_INITIALIZED_FILE}
else
    echo "Reusing existing postgres database"
fi

# Prepare turing settings file
TURING_SETTINGS_INITIALIZED_FILE=${TURING_DATA_DIRECTORY}/.settings_initialized
if [[ ! -f ${TURING_SETTINGS_INITIALIZED_FILE} ]]; then
    echo "Initializing turing settings file"
    cat <<EOF > ${TURING_DATA_DIRECTORY}/settings.ini
[settings]
SECRET_KEY=${DJANGO_SECRET_KEY}
DEBUG=False
DEV_MODE=False
ALLOWED_HOSTS=*
INTERNAL_IPS=127.0.0.1
RDS_DB_NAME=${POSTGRES_DATABASE_NAME}
RDS_USERNAME=postgres
RDS_PASSWORD=${POSTGRES_PASSWORD}
RDS_HOSTNAME=localhost
EOF
    touch ${TURING_SETTINGS_INITIALIZED_FILE}
else
    echo "Reusing existing turing settings file"
fi
if [[ ! -f ${TURING_ROOT_DIRECTORY}/Turing/settings.ini ]]; then
    echo "Creating link to turing settings file"
    ln -s ${TURING_DATA_DIRECTORY}/settings.ini ${TURING_ROOT_DIRECTORY}/Turing/settings.ini
else
    echo "Not linking again turing settings file"
fi

# Ask turing to initialize the django database migrations, if not already done previously
DJANGO_DATABASE_MIGRATIONS_FILE=${TURING_ROOT_DIRECTORY}/.django_database_migrations
if [[ ! -f ${DJANGO_DATABASE_MIGRATIONS_FILE} ]]; then
    echo "Initializing django database migrations"
    cd ${TURING_ROOT_DIRECTORY}
    python3 manage.py makemigrations
    python3 manage.py makemigrations engine
    python3 manage.py migrate
    touch ${DJANGO_DATABASE_MIGRATIONS_FILE}
else
    echo "Not initializing again django database migrations"
fi

# Ask turing to collect static files, if not already done previously
DJANGO_COLLECT_STATIC_FILE=${TURING_ROOT_DIRECTORY}/.django_collect_static
if [[ ! -f ${DJANGO_COLLECT_STATIC_FILE} ]]; then
    echo "Collecting django static files"
    cd ${TURING_ROOT_DIRECTORY}
    python3 manage.py collectstatic
    touch ${DJANGO_COLLECT_STATIC_FILE}
else
    echo "Not collecting again django static files"
fi

# Add a default administrator user to the django database, if not already done previously
DJANGO_ADMIN_INITIALIZED_FILE=${POSTGRES_CLUSTER_DATA_DIRECTORY}/.django_admin_initialized
if [[ ! -f ${DJANGO_ADMIN_INITIALIZED_FILE} ]]; then
    export DJANGO_SUPERUSER_USERNAME=admin
    export DJANGO_SUPERUSER_PASSWORD="Admin2026!"
    export DJANGO_SUPERUSER_EMAIL="admin@admin.it"
    echo "Initializing the default django administrator user with username ${DJANGO_SUPERUSER_USERNAME} and password ${DJANGO_SUPERUSER_PASSWORD}"
    cd ${TURING_ROOT_DIRECTORY}
    python3 manage.py createsuperuser --no-input
    touch ${DJANGO_ADMIN_INITIALIZED_FILE}
    DJANGO_SUPERUSER_PASSWORD_FILE=${SECRETS_DATA_DIRECTORY}/.django_superuser_initial_password
    echo ${DJANGO_SUPERUSER_PASSWORD} > ${DJANGO_SUPERUSER_PASSWORD_FILE}
else
    echo "Not initializing again default django administrator"
fi

# Start the server
if [[ $# -eq 0 ]]; then
    echo "Starting the server"
    cd ${TURING_ROOT_DIRECTORY}
    python3 manage.py runserver 0.0.0.0:80
else
    echo "NOT starting the server because a custom command $@ was provided"
    cd /root
    exec "$@"
fi
