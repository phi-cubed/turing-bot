#!/bin/bash
# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

set -e

for JOURNAL in **/*.journal; do
    # A space is missing between colon and giusto/sbagliato in the answer submission comment
    if grep -q ":giusto" ${JOURNAL}; then
        sed -i "s/:giusto/: giusto/g" ${JOURNAL}
    fi
    if grep -q ":sbagliato" ${JOURNAL}; then
        sed -i "s/:sbagliato/: sbagliato/g" ${JOURNAL}
    fi
    # Protocol numbers start from zero rather than one
    if grep -q "PROT: squadra" ${JOURNAL}; then
        sed -i "s/PROT: squadra/PROT:0 squadra/g" ${JOURNAL}
    fi
    if grep -q "PROT:0 squadra" ${JOURNAL}; then
        gawk -i inplace '{for(i=1;i<=NF;i++)if($i ~ /^PROT/) sub($i,"PROT:"substr($i, 6, length($i))+1,$i)} 1' ${JOURNAL}
    fi
done
