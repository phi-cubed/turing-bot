# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.live_journal_to_live_turing."""

import datetime
import io
import pathlib
import tempfile

import pytest

import mathrace_interaction
import mathrace_interaction.test
import mathrace_interaction.test.mock_models
import mathrace_interaction.typing


@pytest.mark.parametrize("num_reads", [2, 4, 6])
def test_live_journal_to_live_turing(
    journal: io.StringIO, race_name: str, race_date: datetime.datetime, num_reads: int,
    turing_dict: mathrace_interaction.typing.TuringDict
) -> None:
    """Test test_live_journal_to_live_turing with a fixed number of reads."""
    journal_copy = io.StringIO(journal.read())
    journal.seek(0)
    tester = mathrace_interaction.test.LiveJournalToLiveTuringTester(
        journal_copy, race_name, race_date, num_reads, mathrace_interaction.test.mock_models)
    final_dict = tester.run()
    assert final_dict == turing_dict


def test_live_journal_to_live_turing_not_started(
    turing_dict: mathrace_interaction.typing.TuringDict,
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that test_live_journal_to_live_turing raises an error when the turing race has not been started yet."""
    with tempfile.TemporaryDirectory() as output_directory:
        Gara = mathrace_interaction.test.mock_models.Gara  # noqa: N806
        turing_dict["inizio"] = None
        turing_race = Gara.create_from_dict(turing_dict)
        turing_race.save()
        runtime_error_contains(
            lambda: mathrace_interaction.live_journal_to_live_turing(
                lambda: io.StringIO(""), mathrace_interaction.test.mock_models, turing_race.pk, 0.0,
                pathlib.Path(output_directory), lambda time_counter, race_ended: False),
            f"Please start race {turing_race.pk} from the turing web interface")


def test_live_journal_to_live_turing_inconsistent_definition(
    turing_dict: mathrace_interaction.typing.TuringDict,
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that test_live_journal_to_live_turing raises an error on inconsistencies between turing and journal."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 8 -- squadre: 10 quesiti: 7
--- 004 1 20 quesito 1 punteggio iniziale 20
--- 004 2 20 quesito 2 punteggio iniziale 20
--- 004 3 20 quesito 3 punteggio iniziale 20
--- 004 4 20 quesito 4 punteggio iniziale 20
--- 004 5 20 quesito 5 punteggio iniziale 20
--- 004 6 20 quesito 6 punteggio iniziale 20
--- 004 7 21 quesito 7 punteggio iniziale 21
# the last question has score 21 instead of 20
--- 999 fine simulatore
""")
    with tempfile.TemporaryDirectory() as output_directory:
        Gara = mathrace_interaction.test.mock_models.Gara  # noqa: N806
        turing_dict["eventi"].clear()
        turing_race = Gara.create_from_dict(turing_dict)
        turing_race.save()
        runtime_error_contains(
            lambda: mathrace_interaction.live_journal_to_live_turing(
                lambda: io.StringIO(wrong_journal.getvalue()), mathrace_interaction.test.mock_models,
                turing_race.pk, 0.0, pathlib.Path(output_directory), lambda time_counter, race_ended: False),
            f"Turing race {turing_race.pk} is not consistent with the one stored in the journal file. "
            "The difference between journal and turing races is {'soluzioni': {6: {'punteggio': [21, 20]}}}")
