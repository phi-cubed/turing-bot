# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.determine_journal_version."""

import io
import tempfile

import pytest

import mathrace_interaction
import mathrace_interaction.typing


def test_determine_journal_version(journal: io.StringIO, journal_version: str) -> None:
    """Test that test_determine_journal_version correctly recognizes the version of sample journals."""
    assert mathrace_interaction.determine_journal_version(journal) == journal_version


@pytest.mark.parametrize("input_file_option", ["-i", "--input-file"])
def test_determine_journal_version_entrypoint(
    journal: io.StringIO, journal_version: str, run_entrypoint: mathrace_interaction.typing.RunEntrypointFixtureType,
    input_file_option: str
) -> None:
    """Test running test_determine_journal_version as entrypoint."""
    with tempfile.NamedTemporaryFile() as journal_file:
        with open(journal_file.name, "w") as journal_stream:
            journal_stream.write(journal.read())
        stdout, stderr = run_entrypoint(
            "mathrace_interaction.determine_journal_version", [input_file_option, journal_file.name])
        assert stdout == journal_version
        assert stderr == ""
        # The same journal stream is shared on the parametrization on command line options: since the stream
        # was consumed reset it to the beginning before passing to the next parametrized item
        journal.seek(0)


def test_determine_journal_version_error_on_empty_file(
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that test_determine_journal_version raises an error with an empty file."""
    wrong_journal = io.StringIO("")
    runtime_error_contains(
        lambda: mathrace_interaction.determine_journal_version(wrong_journal),
        "The provided journal is empty")


def test_determine_journal_version_error_on_mixed_race_start_codes(
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that test_determine_journal_version raises an error when multiple race start codes are present."""
    wrong_journal = io.StringIO("""\
0 002 inizio gara
0 200 inizio gara
""")
    runtime_error_contains(
        lambda: mathrace_interaction.determine_journal_version(wrong_journal),
        "More than one race start event detected, with different event codes")


def test_determine_journal_version_error_wrong_race_start_codes(
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that test_determine_journal_version raises an error when wrong race start codes are present."""
    wrong_journal = io.StringIO("""\
0 222 inizio gara
""")
    runtime_error_contains(
        lambda: mathrace_interaction.determine_journal_version(wrong_journal),
        "The file contains race events, but not race start was detected")
