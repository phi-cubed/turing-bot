# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.filter.strip_comments_and_unhandled_events_from_journal."""

import io
import random
import sys
import tempfile

import pytest

import mathrace_interaction.filter
import mathrace_interaction.typing


@pytest.fixture
def random_journal(journal: io.StringIO, journal_version: str) -> io.StringIO:
    """Add some random comments and unhandled lines to the test journal."""
    lines = [line.strip("\n") for line in journal.readlines()]
    # The same journal stream is shared by random_journal and expected_stripped_journal fixtures:
    # since the stream was consumed reset it to the beginning before it gets used by the other fixture
    journal.seek(0)
    # Determine the journal reader class corresponding to the provided version
    journal_reader_class = getattr(
        sys.modules["mathrace_interaction.journal_reader"], f"JournalReader{journal_version.capitalize()}")
    # Prepare a list of lines which are ignored by the reader
    blacklist = [
        "# a comment",
        f"timestamp {journal_reader_class.JOLLY_TIMEOUT} timeout jolly",
        f"timestamp {journal_reader_class.TIMER_UPDATE} aggiorna punteggio esercizi, orologio: timestamp",
        f"timestamp {journal_reader_class.RACE_SUSPENDED} gara sospesa",
        f"timestamp {journal_reader_class.RACE_RESUMED} gara ripresa"
    ]
    if hasattr(journal_reader_class, "TIMER_UPDATE_OTHER_TIMER"):
        blacklist.append(
            f"timestamp {journal_reader_class.TIMER_UPDATE_OTHER_TIMER} avanzamento estrapolato orologio: timestamp")
    # Determine the indices of the lines that contains the race start and race end events
    for race_start_line in range(len(lines)):
        if f"{journal_reader_class.RACE_START} inizio gara" in lines[race_start_line]:
            break
    assert race_start_line > 0
    assert race_start_line < len(lines) - 1
    for race_end_line in range(len(lines)):
        if f"{journal_reader_class.RACE_END} termine gara" in lines[race_end_line]:
            break
    assert race_end_line > race_start_line
    assert race_end_line < len(lines) - 1
    new_lines = lines[:race_start_line + 1]
    for line_id in range(race_start_line + 1, race_end_line):
        new_lines.append(lines[line_id])
        new_lines.append(blacklist[random.randrange(0, len(blacklist))])
    new_lines.extend(lines[race_end_line:])
    # Wrap into a stream and return
    return io.StringIO("\n".join(new_lines))



@pytest.fixture
def expected_stripped_journal(journal: io.StringIO) -> io.StringIO:
    """Manually strip comments, timer and jolly timeout lines from the test journal."""
    expected_stripped_journal_content = "\n".join([
        line.strip("\n") for line in journal.readlines()
        if (
            not line.startswith("#") and
            "aggiorna punteggio esercizi" not in line and
            "avanzamento estrapolato orologio" not in line and
            "timeout jolly" not in line
        )
    ])
    # The same journal stream is shared by random_journal and expected_stripped_journal fixtures:
    # since the stream was consumed reset it to the beginning before it gets used by the other fixture
    journal.seek(0)
    # Wrap into a stream and return
    return io.StringIO(expected_stripped_journal_content)


def test_strip_comments_and_unhandled_events_from_journal(
    random_journal: io.StringIO, expected_stripped_journal: io.StringIO
) -> None:
    """Test strip_comments_and_unhandled_events_from_journal."""
    assert mathrace_interaction.filter.strip_comments_and_unhandled_events_from_journal(
        random_journal) == expected_stripped_journal.read()


@pytest.mark.parametrize("input_file_option,output_file_option", [("-i", "-o"), ("--input-file", "--output-file")])
def test_strip_comments_and_unhandled_events_from_journal_entrypoint(
    random_journal: io.StringIO, expected_stripped_journal: io.StringIO,
    run_entrypoint: mathrace_interaction.typing.RunEntrypointFixtureType,
    input_file_option: str, output_file_option: str
) -> None:
    """Test running strip_comments_and_unhandled_events_from_journal as entrypoint."""
    with tempfile.NamedTemporaryFile() as input_journal_file, tempfile.NamedTemporaryFile() as output_journal_file:
        with open(input_journal_file.name, "w") as input_journal_stream:
            input_journal_stream.write(random_journal.read())
        stdout, stderr = run_entrypoint(
            "mathrace_interaction.filter.strip_comments_and_unhandled_events_from_journal", [
                input_file_option, input_journal_file.name, output_file_option, output_journal_file.name
            ]
        )
        assert stdout == ""
        assert stderr == ""
        with open(output_journal_file.name) as output_journal_stream:
            stripped_journal = output_journal_stream.read()
        assert expected_stripped_journal.read() == stripped_journal
