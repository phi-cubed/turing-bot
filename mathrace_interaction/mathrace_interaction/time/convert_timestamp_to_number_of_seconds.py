# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Convert a timestamp of the form hh:mm:ss.msec to an integer number of seconds."""

def convert_timestamp_to_number_of_seconds(timestamp_str: str) -> int:
    """Convert a timestamp of the form hh:mm:ss.msec to an integer number of seconds."""
    return int(sum(x * float(t) for x, t in zip([1, 60, 3600], reversed(timestamp_str.split(":")))))
