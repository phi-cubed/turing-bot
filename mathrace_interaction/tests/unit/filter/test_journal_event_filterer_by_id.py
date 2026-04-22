# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.filter.journal_event_filterer_by_id."""

import io
import tempfile

import pytest

import mathrace_interaction.filter
import mathrace_interaction.typing


def test_journal_event_filterer_by_id(journal: io.StringIO) -> None:
    """Test journal_event_filterer_by_id."""
    assert mathrace_interaction.filter.journal_event_filterer_by_id(
        journal, 7) == mathrace_interaction.filter.journal_event_filterer_by_timestamp(journal, "450")


@pytest.mark.parametrize("input_file_option,id_upper_bound_option,output_file_option", [
    ("-i", "-p", "-o"), ("--input-file", "--id-upper-bound", "--output-file")])
def test_journal_event_filterer_by_id_entrypoint(
    journal: io.StringIO, run_entrypoint: mathrace_interaction.typing.RunEntrypointFixtureType,
    input_file_option: str, id_upper_bound_option: str, output_file_option: str
) -> None:
    """Test running journal_event_filterer_by_id as entrypoint."""
    with tempfile.NamedTemporaryFile() as input_journal_file, tempfile.NamedTemporaryFile() as output_journal_file:
        with open(input_journal_file.name, "w") as input_journal_stream:
            input_journal_stream.write(journal.read())
        stdout, stderr = run_entrypoint(
            "mathrace_interaction.filter.journal_event_filterer_by_id", [
                input_file_option, input_journal_file.name, id_upper_bound_option, "7",
                output_file_option, output_journal_file.name
            ]
        )
        assert stdout == ""
        assert stderr == ""
        with open(output_journal_file.name) as output_journal_stream:
            filtered_by_id = output_journal_stream.read()
        # Obtain an equivalent journal using a timestamp based filter at the same time when event 7 happens.
        # The journal stream was consumed when preparing input_journal_file, so it must be reset.
        journal.seek(0)
        filtered_by_timestamp = mathrace_interaction.filter.journal_event_filterer_by_timestamp(journal, "450")
        assert filtered_by_id == filtered_by_timestamp
