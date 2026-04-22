# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.time.convert_timestamp_to_number_of_seconds."""

import mathrace_interaction.time


def test_convert_timestamp_to_number_of_seconds() -> None:
    """Test convert_timestamp_to_number_of_seconds in a few cases."""
    assert mathrace_interaction.time.convert_timestamp_to_number_of_seconds("1") == 1
    assert mathrace_interaction.time.convert_timestamp_to_number_of_seconds("1:2") == 62
    assert mathrace_interaction.time.convert_timestamp_to_number_of_seconds("1:2:3") == 3723
    assert mathrace_interaction.time.convert_timestamp_to_number_of_seconds(
        "1:2:3.45678") == 3723  # decimals are discarded
