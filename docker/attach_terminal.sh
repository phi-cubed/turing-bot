#!/bin/bash
# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

set -e

CONTAINER_ID_FILE=".container_id"
CONTAINER_ID=$(cat "${CONTAINER_ID_FILE}")
docker exec -it ${CONTAINER_ID} /bin/bash
