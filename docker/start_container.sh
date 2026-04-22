#!/bin/bash
# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

set -e

CONTAINER_ID_FILE=".container_id"
CONTAINER_ID=$(cat "${CONTAINER_ID_FILE}")
if [ "$( docker container inspect -f '{{.State.Running}}' ${CONTAINER_ID} )" == "true" ]; then
    echo "The container is already running!"
    echo "If you want to attach a terminal to it, please run ./attach_terminal.sh"
    exit 1
else
    START_TIME=$(date +%s)
    docker start ${CONTAINER_ID}
    # Entrypoint outputs are not reported to stdout, but logged: fetch them and print them to stdout, after waiting
    # a reasonable amount of time for the entrypoint to be done
    ARCH=$(dpkg --print-architecture)
    if [[ ${ARCH} == "armhf" ]]; then
        # armhf is slower than standard archs, so wait a bit more time before giving up
        MAX_TRY=30
        SLEEP=3
    else
        MAX_TRY=10
        SLEEP=1
    fi
    for TRY in $(seq 1 ${MAX_TRY}); do
        DOCKER_LOG=$(docker logs --since "${START_TIME}" --timestamps ${CONTAINER_ID})
        if [[ "${DOCKER_LOG}" == *"Starting the server"* ]]; then
            echo "${DOCKER_LOG}"
            break
        else
            if [[ ${TRY} != ${MAX_TRY} ]]; then
                sleep ${SLEEP}
            else
                echo "${DOCKER_LOG}"
                echo "Server did not start after ${MAX_TRY} seconds. Log output may be incomplete."
            fi
        fi
    done
fi
