# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.live_turing_to_live_journal on journals in data and turing models."""

import datetime
import io
import os

import engine.models
import pytest

import mathrace_interaction
import mathrace_interaction.test


@pytest.mark.django_db
def test_live_turing_to_live_journal_on_data(journal: io.StringIO, journal_name: str) -> None:
    """Test test_live_turing_to_live_journal with a fixed number of reads."""
    journal_year, _ = journal_name.split(os.sep, maxsplit=1)
    journal_date = datetime.datetime(int(journal_year), 1, 1, tzinfo=datetime.UTC)
    journal_copy = io.StringIO(journal.read())
    journal.seek(0)
    num_reads = 6  # split the journal into very large chucks, otherwise testing time increases too much
    tester = mathrace_interaction.test.LiveTuringToLiveJournalTester(
        journal_copy, journal_name, journal_date, num_reads, engine.models)
    final_dict = tester.run()
    journal_copy = io.StringIO(journal.read())
    journal.seek(0)
    with mathrace_interaction.journal_reader(journal_copy) as expected_stream:
        expected_dict = expected_stream.read(journal_name, journal_date)
    mathrace_interaction.filter.strip_mathrace_only_attributes_from_imported_turing(expected_dict)
    mathrace_interaction.filter.strip_trailing_zero_bonus_superbonus_from_imported_turing(expected_dict)
    assert final_dict == expected_dict
