# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.filter.live_journal."""

import io

import pytest

import mathrace_interaction.filter
import mathrace_interaction.typing


def strip_file_end_line(content: str) -> str:
    """Drop the file end line from the content of a journal."""
    return content.replace("\n--- 999 fine simulatore", "")


def test_live_journal_one_new_event_per_read(journal: io.StringIO) -> None:
    """Test live_journal in the case where the number of reads is equal to the number of handled race events."""
    # Strip the journal of comments and unhandled events
    stripped_journal = mathrace_interaction.filter.strip_comments_and_unhandled_events_from_journal(journal)
    # Count the number of lines starting with ---, and the rest of the lines
    num_race_setup_lines = sum([line.startswith("---") for line in stripped_journal.split("\n")])
    num_race_setup_lines -= 1  # discard the line with setup code 999
    num_race_events = sum([not line.startswith("---") for line in stripped_journal.split("\n")])
    assert num_race_events == 12
    # Read the live journal
    num_reads = num_race_events + 1  # the first read will read a file with no race events
    live_journal = mathrace_interaction.filter.LiveJournal(io.StringIO(stripped_journal), num_reads)
    previous_read_without_end_line = ""
    for i in range(num_reads):
        current_read = live_journal.open().read()
        # Race start line must be included in the live journal, except for the very first read which includes
        # the entire race definition
        if i > 0:
            assert "inizio gara" in current_read
        else:
            assert "inizio gara" not in current_read
        # File end line must be included in the live journal
        current_read_without_end_line = strip_file_end_line(current_read)
        assert current_read != current_read_without_end_line
        # The current read must have added something on top of the previous one
        assert previous_read_without_end_line in current_read_without_end_line
        # The current read must have added a single new line, except for the very first read which includes
        # the entire race definition
        diff_read_without_end_line = current_read_without_end_line.replace(previous_read_without_end_line, "")
        diff_read_num_new_lines = diff_read_without_end_line.count("\n")
        if i > 0:
            # no need to add 1: we are actually counting the \n that was added at the end of the final line
            # present in the previous read, rather than a \n in the newly added line
            assert diff_read_num_new_lines == 1
        else:
            # need to add 1 because the final line does not have a \n
            assert diff_read_num_new_lines + 1 == num_race_setup_lines
        # Prepare for the next iteration
        previous_read_without_end_line = current_read_without_end_line
    # By the end, the file must have been read fully
    assert strip_file_end_line(stripped_journal) == previous_read_without_end_line


def test_live_journal_one_new_event_every_two_reads(journal: io.StringIO) -> None:
    """Test live_journal in the case where the number of reads is equal to twice the number of handled race events."""
    # Strip the journal of comments and unhandled events
    stripped_journal = mathrace_interaction.filter.strip_comments_and_unhandled_events_from_journal(journal)
    num_race_events = 12
    live_journal = mathrace_interaction.filter.LiveJournal(io.StringIO(stripped_journal), 2 * num_race_events + 1)
    # Carry out the initial read outside of the for loop, since it pulls in the entire race setup
    # rather than race events.
    previous_read_without_end_line = strip_file_end_line(live_journal.open().read())
    for i in range(num_race_events):
        # Read the file for the first time in the for loop body
        current_read = live_journal.open().read()
        current_read_without_end_line = strip_file_end_line(current_read)
        # The first read must have not added anything, because there were no new events in the meantime
        assert previous_read_without_end_line == current_read_without_end_line
        # Read the file for the second time in the for loop body
        current_read = live_journal.open().read()
        current_read_without_end_line = strip_file_end_line(current_read)
        # The second read must have added something on top of the previous one
        assert previous_read_without_end_line in current_read_without_end_line
        # The second read must have added a single new line
        diff_read_without_end_line = current_read_without_end_line.replace(previous_read_without_end_line, "")
        assert diff_read_without_end_line.count("\n") == 1
        # Prepare for the next iteration
        previous_read_without_end_line = current_read_without_end_line
    # By the end, the file must have been read fully
    assert strip_file_end_line(mathrace_interaction.filter.strip_comments_and_unhandled_events_from_journal(
        journal)) == previous_read_without_end_line

@pytest.mark.parametrize("max_open_calls", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])
def test_live_journal_several_new_events_every_read(journal: io.StringIO, max_open_calls: int) -> None:
    """Test live_journal in the case where the every read introduces several new events."""
    stripped_journal = mathrace_interaction.filter.strip_comments_and_unhandled_events_from_journal(journal)
    num_race_events = 12
    live_journal = mathrace_interaction.filter.LiveJournal(io.StringIO(stripped_journal), max_open_calls)
    # Determine the range of expected new events for every read
    if max_open_calls > 1:
        num_new_events_per_read_int = num_race_events // (max_open_calls - 1)
        if num_race_events % (max_open_calls - 1) == 0:
            num_new_events_per_read_list = [num_new_events_per_read_int]
        else:
            num_new_events_per_read_list = [num_new_events_per_read_int, num_new_events_per_read_int + 1]
    else:
        num_new_events_per_read_list = [num_race_events]
    # Carry out the initial read outside of the for loop, since it pulls in the entire race setup
    # rather than race events.
    previous_read_without_end_line = strip_file_end_line(live_journal.open().read())
    for i in range(max_open_calls - 1):
        current_read = live_journal.open().read()
        current_read_without_end_line = strip_file_end_line(current_read)
        # Race start line must be included in the live journal
        assert "inizio gara" in current_read
        # The current read must have added something on top of the previous one
        assert previous_read_without_end_line in current_read_without_end_line
        # The current read must have added the expected number of new lines
        diff_read_without_end_line = current_read_without_end_line.replace(previous_read_without_end_line, "")
        assert diff_read_without_end_line.count("\n") in num_new_events_per_read_list
        # Prepare for the next iteration
        previous_read_without_end_line = current_read_without_end_line
    # By the end, the file must have been read fully
    assert strip_file_end_line(mathrace_interaction.filter.strip_comments_and_unhandled_events_from_journal(
        journal)) == previous_read_without_end_line


def test_live_journal_raises_on_extra_read(
    journal: io.StringIO, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that live_journal raises when the journal is read more times than expected."""
    num_reads = 4
    live_journal = mathrace_interaction.filter.LiveJournal(journal, num_reads)
    for i in range(num_reads):
        live_journal.open().read()
    runtime_error_contains(
        lambda: live_journal.open().read(),
        "Journal was fully read already")
