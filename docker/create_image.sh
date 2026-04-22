#!/bin/bash
# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

set -e

# Do not run any further if we are not connected to the internet
wget -q --spider https://www.google.com

# Build image
docker build --pull -t ghcr.io/dmf-unicatt/turing-dmf:latest -f Dockerfile ..
