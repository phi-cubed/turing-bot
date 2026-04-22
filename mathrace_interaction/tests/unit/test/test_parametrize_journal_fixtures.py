# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.test.parametrize_journal_fixtures."""

import sys
import typing

import _pytest
import pytest


def counter_incrementer(counter_variable: str) -> None:
    """Increment the counter store in a global variable."""
    current_value = getattr(sys.modules[__name__], counter_variable)
    setattr(sys.modules[__name__], counter_variable, current_value + 1)


def counter_checker(counter_variable: str, expected_value: int) -> typing.Callable[[], None]:
    """Ensure that a variable contains the expected value."""
    def _() -> None:
        """Ensure that a variable contains the expected value (internal implementation)."""
        assert getattr(sys.modules[__name__], counter_variable) == expected_value

    return _


def fixture_checker(
    counter_variable: str, expected_value: int
) -> typing.Callable[[_pytest.fixtures.SubRequest], None]:
    """Return a class fixture to check the counter at the end of the parametrization."""
    @pytest.fixture(scope="class")
    def _(request: _pytest.fixtures.SubRequest) -> None:
        """Return a class fixture to check the counter at the end of the parametrization (internal implementation)."""
        request.addfinalizer(counter_checker(counter_variable, expected_value))

    return _

journal_counter = 0
journal_version_counter = 0
journal_and_journal_version_counter = 0
journal_and_other_journal_counter = 0
journal_version_and_other_journal_version_counter = 0
journal_and_journal_version_and_other_journal_and_other_journal_version_counter = 0

journal_checker = fixture_checker("journal_counter", 10)
journal_version_checker = fixture_checker("journal_version_counter", 10)
journal_and_journal_version_checker = fixture_checker("journal_and_journal_version_counter", 10)
journal_and_other_journal_checker = fixture_checker("journal_and_other_journal_counter", 100)
journal_version_and_other_journal_version_checker = fixture_checker(
    "journal_version_and_other_journal_version_counter", 100)
journal_and_journal_version_and_other_journal_and_other_journal_version_checker = fixture_checker(
    "journal_and_journal_version_and_other_journal_and_other_journal_version_counter", 100)


def generate_journal_fixture_test(fixture_names: str) -> type:
    """Check the number of elements in a parametrization added as a fixture by pytest_generate_tests."""
    fixture_prefix = fixture_names.replace(",", "_and_")

    @pytest.mark.random_order(disabled=True)
    @pytest.mark.usefixtures(fixture_prefix + "_checker")
    class TestChecker:
        """
        Check the number of elements in a parametrization (internal implementation).

        The test is inside a class to ensure that the check is run only once after the last parametrization entry.
        """

        @pytest.mark.usefixtures(*fixture_names.split(","))
        def test_parametrized_fixture(self) -> None:
            """Check the number of elements in the provided parametrization."""
            counter_incrementer(fixture_prefix + "_counter")

    return TestChecker


class TestJournalChecker(generate_journal_fixture_test("journal")):  # type: ignore[misc]
    """Check the number of elements in the journal parametrization."""

class TestJournalVersionChecker(generate_journal_fixture_test("journal_version")):  # type: ignore[misc]
    """Check the number of elements in the journal_version parametrization."""


class TestJournalAndJournalVersionChecker(
    generate_journal_fixture_test("journal,journal_version")  # type: ignore[misc]
):
    """Check the number of elements in the (journal, journal_version) parametrization."""


class TestJournalAndOtherJournalChecker(
    generate_journal_fixture_test("journal,other_journal")  # type: ignore[misc]
):
    """Check the number of elements in the (journal, other_journal) parametrization."""


class TestJournalVersionAndOtherJournalVersionChecker(
    generate_journal_fixture_test("journal_version,other_journal_version")  # type: ignore[misc]
):
    """Check the number of elements in the (journal_version, other_journal_version) parametrization."""


class TestJournalAndJournalVersionAndOtherJournalAndOtherJournalVersionChecker(
    generate_journal_fixture_test("journal,journal_version,other_journal,other_journal_version")  # type: ignore[misc]
):
    """Check the number of elements in the 4-way journal and other_journal parametrization."""
