# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.filter.journal_event_filterer_by_timestamp."""

import io
import tempfile

import pytest

import mathrace_interaction.filter
import mathrace_interaction.typing


@pytest.fixture
def expected_filtered_by_timestamp_journal(journal: io.StringIO) -> io.StringIO:
    """Manually retain all lines before the one that contains squadra 3, quesito 4: sbagliato."""
    expected_filtered_by_timestamp_journal_lines: list[str] = []
    for line in journal.readlines():
        expected_filtered_by_timestamp_journal_lines.append(line.strip("\n"))
        if "squadra 3, quesito 4: sbagliato" in line:
            break
    assert len(expected_filtered_by_timestamp_journal_lines) > 0
    # Manually add the file finalization line
    expected_filtered_by_timestamp_journal_lines.append("--- 999 fine simulatore")
    # The same journal stream is shared by the test and the expected_filtered_by_timestamp_journal fixture:
    # since the stream was consumed reset it to the beginning before it gets used by the test
    journal.seek(0)
    # Wrap into a stream and return
    return io.StringIO("\n".join(expected_filtered_by_timestamp_journal_lines))


@pytest.mark.parametrize("timestamp_upper_bound", ["450", "7:30", "450.1"])
def test_journal_event_filterer_by_timestamp(
    journal: io.StringIO, timestamp_upper_bound: str, expected_filtered_by_timestamp_journal: io.StringIO
) -> None:
    """Test journal_event_filterer_by_timestamp."""
    assert mathrace_interaction.filter.journal_event_filterer_by_timestamp(
        journal, timestamp_upper_bound) == expected_filtered_by_timestamp_journal.read()


@pytest.mark.parametrize("input_file_option,timestamp_upper_bound_option,output_file_option", [
    ("-i", "-t", "-o"), ("--input-file", "--timestamp-upper-bound", "--output-file")])
@pytest.mark.parametrize("timestamp_upper_bound", ["450", "7:30", "450.1"])
def test_journal_event_filterer_by_timestamp_entrypoint(
    journal: io.StringIO, timestamp_upper_bound: str, expected_filtered_by_timestamp_journal: io.StringIO,
    run_entrypoint: mathrace_interaction.typing.RunEntrypointFixtureType, input_file_option: str,
    timestamp_upper_bound_option: str, output_file_option: str
) -> None:
    """Test running journal_event_filterer_by_timestamp as entrypoint."""
    with tempfile.NamedTemporaryFile() as input_journal_file, tempfile.NamedTemporaryFile() as output_journal_file:
        with open(input_journal_file.name, "w") as input_journal_stream:
            input_journal_stream.write(journal.read())
        stdout, stderr = run_entrypoint(
            "mathrace_interaction.filter.journal_event_filterer_by_timestamp", [
                input_file_option, input_journal_file.name, timestamp_upper_bound_option, timestamp_upper_bound,
                output_file_option, output_journal_file.name
            ]
        )
        assert stdout == ""
        assert stderr == ""
        with open(output_journal_file.name) as output_journal_stream:
            filtered_journal = output_journal_stream.read()
        assert expected_filtered_by_timestamp_journal.read() == filtered_journal
        # The same journal stream is shared by the test and the expected_filtered_by_timestamp_journal fixture:
        # since the stream was consumed reset it to the beginning before it gets used by the fixture on the next
        # value of the parametrization
        journal.seek(0)
