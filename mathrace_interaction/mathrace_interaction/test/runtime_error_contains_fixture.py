# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Check that a RuntimeError is raised and contains the expected text."""

import typing

import pytest

from mathrace_interaction.typing import RuntimeErrorContainsFixtureType


@pytest.fixture
def runtime_error_contains_fixture() -> RuntimeErrorContainsFixtureType:
    """Check that a RuntimeError is raised and contains the expected text."""
    def _(call: typing.Callable[[], typing.Any], expected_error_text: str) -> None:
        """Check that a RuntimeError is raised and contains the expected text (internal implementation)."""
        with pytest.raises(RuntimeError) as excinfo:
            call()
        runtime_error_text = str(excinfo.value)
        assert expected_error_text in runtime_error_text, (
            f"Got the text '{runtime_error_text}' instead of '{expected_error_text}'")

    return _
