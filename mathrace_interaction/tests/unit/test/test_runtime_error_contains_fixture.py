# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.test.runtime_error_contains_fixture."""

import _pytest
import pytest

import mathrace_interaction.typing


def raise_runtime_error(error_text: str) -> None:
    """Raise a runtime error with the provided text."""
    raise RuntimeError(error_text)


def test_runtime_error_contains_with_correct_error(
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test the runtime_error_contains fixture when the function to be called actually raises the correct error."""
    runtime_error_contains(
        lambda: raise_runtime_error("test_runtime_error_contains_with_error raised"),
        "test_runtime_error_contains_with_error raised")


def test_runtime_error_contains_with_wrong_error(
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test the runtime_error_contains fixture when the function to be called actually raises the wrong error."""
    with pytest.raises(AssertionError) as excinfo:
        runtime_error_contains(
            lambda: raise_runtime_error("test_runtime_error_contains_with_wrong_error raised"),
            "test_runtime_error_contains_with_wrong_error NOT raised")
    assertion_error_text = str(excinfo.value)
    assert assertion_error_text == (
        "Got the text 'test_runtime_error_contains_with_wrong_error raised' instead of "
        "'test_runtime_error_contains_with_wrong_error NOT raised'")


def test_runtime_error_contains_without_error(
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test the runtime_error_contains fixture when the function to be called raises no error."""
    with pytest.raises(_pytest.outcomes.Failed) as excinfo:
        runtime_error_contains(lambda: None, "test_runtime_error_contains_without_error raised")
    pytest_error_text = str(excinfo.value)
    assert pytest_error_text == "DID NOT RAISE <class 'RuntimeError'>"
