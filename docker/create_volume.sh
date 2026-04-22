#!/bin/bash
# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

set -e

VOLUME_ID_FILE=".volume_id"
if [[ -f "${VOLUME_ID_FILE}" ]]; then
    echo "A database volume already exists!"
    exit 1
else
    VOLUME_ID=$(docker volume create turing-database-$(date +%s))
    echo ${VOLUME_ID} > ${VOLUME_ID_FILE}
fi
