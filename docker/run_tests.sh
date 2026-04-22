#!/bin/bash
# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

set -e

COMPONENT=$1
if [[ -z "${COMPONENT}" ]]; then
    echo "Need to write the component you want to test (e.g., turing) as first argument"
    exit 1
fi
if [[ "${COMPONENT}" != "turing" && "${COMPONENT}" != "mathrace_interaction/tests/unit" && "${COMPONENT}" != "mathrace_interaction/tests/functional" && "${COMPONENT}" != "mathrace_interaction/tests/integration" ]]; then
    echo "Invalid component ${COMPONENT}"
    exit 1
fi

EXEC_OR_RUN=$2
if [[ -z "${EXEC_OR_RUN}" ]]; then
    EXEC_OR_RUN="exec"
fi
if [[ "${EXEC_OR_RUN}" != "exec" && "${EXEC_OR_RUN}" != "run" ]]; then
    echo "Invalid run type ${EXEC_OR_RUN}"
    exit 1
fi

DATABASE_TYPE=$3
if [[ -z "${DATABASE_TYPE}" ]]; then
    DATABASE_TYPE="PostgreSQL"
fi
if [[ "${DATABASE_TYPE}" != "PostgreSQL" && "${DATABASE_TYPE}" != "SQLite3" ]]; then
    echo "Invalid database type ${DATABASE_TYPE}"
    exit 1
fi

if [[ "${COMPONENT}" == "turing" ]]; then
    RUN_TEST_COMMAND="\
        export DISPLAY=${DISPLAY} && \
        cd turing && \
        python3 manage.py test --noinput \
    "
elif [[ "${COMPONENT}" == "mathrace_interaction/tests/unit" || "${COMPONENT}" == "mathrace_interaction/tests/functional" || "${COMPONENT}" == "mathrace_interaction/tests/integration" ]]; then
    RUN_TEST_COMMAND="\
        cd mathrace_interaction && \
        python3 -m pytest ${COMPONENT#*/} \
    "
fi

if [[ "${DATABASE_TYPE}" == "PostgreSQL" ]]; then
    DATABASE_SETUP="\
        POSTGRES_DATABASE_NAME=\$(sed -n -e \"s/^RDS_DB_NAME=//p\" /root/turing/Turing/settings.ini) && \
        sudo -u postgres dropdb --if-exists test_\${POSTGRES_DATABASE_NAME} \
    "
elif [[ "${DATABASE_TYPE}" == "SQLite3" ]]; then
    DATABASE_SETUP="\
        sed -i \"s/RDS_DB_NAME/DISABLED_RDS_DB_NAME/\" /root/turing/Turing/settings.ini \
    "
fi

if [[ "${EXEC_OR_RUN}" == "exec" ]]; then
    if [[ "${DATABASE_TYPE}" == "PostgreSQL" ]]; then
        CONTAINER_ID_FILE=".container_id"
        CONTAINER_ID=$(cat "${CONTAINER_ID_FILE}")
        docker exec ${CONTAINER_ID} /bin/bash -c "${DATABASE_SETUP} && ${RUN_TEST_COMMAND}"
    elif [[ "${DATABASE_TYPE}" == "SQLite3" ]]; then
        echo "Cannot use docker exec and change the database type to SQLite3, because it would alter the existing container"
        exit 1
    fi
elif [[ "${EXEC_OR_RUN}" == "run" ]]; then
    docker run --rm ghcr.io/dmf-unicatt/turing-dmf:latest /bin/bash -c "${DATABASE_SETUP} && ${RUN_TEST_COMMAND}"
fi
