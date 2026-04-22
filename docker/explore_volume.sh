#!/bin/bash
# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

set -e

VOLUME_ID_FILE=".volume_id"
VOLUME_ID=$(cat "${VOLUME_ID_FILE}")

docker run -it --rm -v ${VOLUME_ID}:/mnt --workdir=/mnt debian:13
