#!/bin/bash
# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

set -e

VOLUME_ID_FILE=".volume_id"
VOLUME_ID=$(cat "${VOLUME_ID_FILE}")

NETWORK_PROPERTIES_DIRECTORY=".network_properties"
if [[ -d "${NETWORK_PROPERTIES_DIRECTORY}" ]]; then
    for NETWORK_PROPERTY_FILE in "driver" "subnet" "opt" "ip" "mac-address" "port"; do
        if [[ ! -f "${NETWORK_PROPERTIES_DIRECTORY}/${NETWORK_PROPERTY_FILE}" ]]; then
            echo "The file ${NETWORK_PROPERTIES_DIRECTORY}/${NETWORK_PROPERTY_FILE} is missing"
            exit 1
        fi
    done
    NETWORK_ID_FILE=".network_id"
    if [[ ! -f "${NETWORK_ID_FILE}" ]]; then
        NETWORK_DRIVER=$(cat "${NETWORK_PROPERTIES_DIRECTORY}/driver")
        NETWORK_SUBNET=$(cat "${NETWORK_PROPERTIES_DIRECTORY}/subnet")
        NETWORK_OPT=$(cat "${NETWORK_PROPERTIES_DIRECTORY}/opt")
        NETWORK_ID=$(docker network create --driver=${NETWORK_DRIVER} --subnet=${NETWORK_SUBNET} --opt="${NETWORK_OPT}" turing-dmf-network-$(date +%s))
        echo ${NETWORK_ID} > ${NETWORK_ID_FILE}
    else
        NETWORK_ID=$(cat "${NETWORK_ID_FILE}")
    fi
    NETWORK_IP=$(cat "${NETWORK_PROPERTIES_DIRECTORY}/ip")
    NETWORK_MAC_ADDRESS=$(cat "${NETWORK_PROPERTIES_DIRECTORY}/mac-address")
    NETWORK_PORT=$(cat "${NETWORK_PROPERTIES_DIRECTORY}/port")
    NETWORK_PROPERTIES="--net ${NETWORK_ID} --ip ${NETWORK_IP} --mac-address ${NETWORK_MAC_ADDRESS} -p ${NETWORK_PORT}:80"
else
    NETWORK_PROPERTIES="-p 80:80"
fi

CONTAINER_ID_FILE=".container_id"
if [[ -f "${CONTAINER_ID_FILE}" ]]; then
    echo "A container already exists!"
    echo "If you want to start it, please run ./start_container.sh"
    exit 1
else
    CONTAINER_ID=$(docker create ${NETWORK_PROPERTIES} -v /tmp/shared-turing-dmf:/shared/host-tmp -v $(dirname ${PWD}):/shared/git-repo -v ${VOLUME_ID}:/mnt -e DOCKERHOSTNAME=$(cat /etc/hostname) -e TZ=$(timedatectl show --va -p Timezone) -e TERM=${TERM} ghcr.io/dmf-unicatt/turing-dmf:latest)
    echo ${CONTAINER_ID} > ${CONTAINER_ID_FILE}
fi
