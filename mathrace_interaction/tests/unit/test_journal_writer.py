# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.journal_writer."""

import datetime
import io
import json
import tempfile

import pytest

import mathrace_interaction
import mathrace_interaction.filter
import mathrace_interaction.typing


def test_journal_writer(
    turing_dict: mathrace_interaction.typing.TuringDict, journal: io.StringIO, journal_version: str
) -> None:
    """Test that journal_writer correctly exports sample journals."""
    with (
        io.StringIO("") as exported_journal,
        mathrace_interaction.journal_writer(exported_journal, journal_version) as journal_stream
    ):
        journal_stream.write(turing_dict)
        assert mathrace_interaction.filter.strip_comments_and_unhandled_events_from_journal(
            journal) == exported_journal.getvalue().strip("\n")


@pytest.mark.parametrize(
    "input_file_option,journal_version_option,output_file_option", [
        ("-i", "-v", "-o"),
        ("--input-file", "--journal-version", "--output-file")
    ]
)
def test_journal_writer_entrypoint(
    turing_dict: mathrace_interaction.typing.TuringDict,
    run_entrypoint: mathrace_interaction.typing.RunEntrypointFixtureType,
    race_name: str, race_date: datetime.datetime, journal: io.StringIO, journal_version: str,
    input_file_option: str, journal_version_option: str, output_file_option: str
) -> None:
    """Test running journal_writer as entrypoint."""
    with tempfile.NamedTemporaryFile() as json_file, tempfile.NamedTemporaryFile() as journal_file:
        with open(json_file.name, "w") as json_stream:
            json_stream.write(json.dumps(turing_dict))
        stdout, stderr = run_entrypoint(
            "mathrace_interaction.journal_writer", [
                input_file_option, json_file.name, journal_version_option, journal_version,
                output_file_option, journal_file.name
            ]
        )
        assert stdout == ""
        assert stderr == ""
        with open(journal_file.name) as journal_stream:
            exported_journal = journal_stream.read()
        assert mathrace_interaction.filter.strip_comments_and_unhandled_events_from_journal(
            journal) == exported_journal.strip("\n")
        # The same journal stream is shared on the parametrization on command line options: since the stream
        # was consumed reset it to the beginning before passing to the next parametrized item
        journal.seek(0)


def test_journal_writer_wrong_num_questions(
    turing_dict: mathrace_interaction.typing.TuringDict,
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when turing is inconsistent on the number of questions."""
    turing_dict["num_problemi"] = str(int(turing_dict["num_problemi"]) + 1)
    with (
        io.StringIO("") as exported_journal,
        mathrace_interaction.journal_writer(exported_journal, "r5539") as journal_stream
    ):
        runtime_error_contains(
            lambda: journal_stream.write(turing_dict), "Inconsistent data in turing dictionary: 8 != 7")


def test_journal_writer_wrong_race_event(
    turing_dict: mathrace_interaction.typing.TuringDict,
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when an unhandled event code is encountered."""
    turing_dict["eventi"].append({"subclass": "UnhandledEvent"})
    with (
        io.StringIO("") as exported_journal,
        mathrace_interaction.journal_writer(exported_journal, "r5539") as journal_stream
    ):
        runtime_error_contains(
            lambda: journal_stream.write(turing_dict), "Unhandled event type UnhandledEvent")


def test_journal_writer_wrong_version(
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_writer raises an error when requesting a wrong version."""
    with io.StringIO("") as exported_journal:
        runtime_error_contains(
            lambda: mathrace_interaction.journal_writer(exported_journal, "r0"),
            "r0 is not among the available versions")


def test_journal_writer_wrong_k_blocco(
    turing_dict: mathrace_interaction.typing.TuringDict,
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_writer raises an error when k_blocco != 1, but the requested version does not support it."""
    turing_dict["k_blocco"] = 2
    with (
        io.StringIO("") as exported_journal,
        mathrace_interaction.journal_writer(exported_journal, "r5539") as journal_stream
    ):
        runtime_error_contains(
            lambda: journal_stream.write(turing_dict),
            "This version does not support a value of k_blocco different from one")


def test_journal_writer_not_started_yet_without_events(
    turing_dict: mathrace_interaction.typing.TuringDict, journal: io.StringIO, journal_version: str
) -> None:
    """Test journal_writer when the race has not started yet."""
    turing_dict["inizio"] = None
    turing_dict["eventi"].clear()
    with (
        io.StringIO("") as exported_journal,
        mathrace_interaction.journal_writer(exported_journal, journal_version) as journal_stream
    ):
        journal_stream.write(turing_dict)
        assert (
            "\n".join(line for line in journal.read().split("\n") if line.startswith("---"))
            == exported_journal.getvalue().strip("\n")
        )


def test_journal_writer_not_started_yet_with_events(
    turing_dict: mathrace_interaction.typing.TuringDict,
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test journal_writer raises an error when the race has not started yet, yet it contains events."""
    turing_dict["inizio"] = None
    with (
        io.StringIO("") as exported_journal,
        mathrace_interaction.journal_writer(exported_journal, "r5539") as journal_stream
    ):
        runtime_error_contains(
            lambda: journal_stream.write(turing_dict), "Race has not started, yet there are 10 events")


def test_journal_writer_wrong_race_events_order(
    turing_dict: mathrace_interaction.typing.TuringDict,
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_writer raises an error when race events are incorrectly sorted."""
    turing_dict["eventi"][-2], turing_dict["eventi"][-1] = turing_dict["eventi"][-1], turing_dict["eventi"][-2]
    with (
        io.StringIO("") as exported_journal,
        mathrace_interaction.journal_writer(exported_journal, "r5539") as journal_stream
    ):
        runtime_error_contains(
            lambda: journal_stream.write(turing_dict),
            "The file contains incorrectly sorted events: event at time 2000-01-01 00:09:30+00:00 "
            "happens before event at time 2000-01-01 00:08:40+00:00")


def test_journal_writer_wrong_race_events_order_not_strict(
    turing_dict: mathrace_interaction.typing.TuringDict
) -> None:
    """Test that journal_writer without strict mode allows to export incorrectly sorted events."""
    turing_dict["eventi"][-2], turing_dict["eventi"][-1] = turing_dict["eventi"][-1], turing_dict["eventi"][-2]
    with (
        io.StringIO("") as exported_journal,
        mathrace_interaction.journal_writer(exported_journal, "r5539") as journal_stream
    ):
        journal_stream.strict_timestamp_race_events = False  # type: ignore[attr-defined]
        journal_stream.write(turing_dict)
        exported_lines = exported_journal.getvalue().splitlines()
        assert exported_lines[-4] == "570 011 9 3 1 squadra 9, quesito 3: giusto"
        assert exported_lines[-3] == "520 091 7 43 squadra 7 bonus 43"
        assert exported_lines[-2] == "600 029 termine gara"
        assert exported_lines[-1] == "--- 999 fine simulatore"


def test_journal_writer_missing_initial_score(
    turing_dict: mathrace_interaction.typing.TuringDict, journal: io.StringIO, journal_version: str
) -> None:
    """Test that journal_writer correctly exports journals even for turing dictionaries with no initial score."""
    turing_dict["punteggio_iniziale_squadre"] = None
    with (
        io.StringIO("") as exported_journal,
        mathrace_interaction.journal_writer(exported_journal, journal_version) as journal_stream
    ):
        journal_stream.write(turing_dict)
        exported_lines = exported_journal.getvalue().splitlines()
        if journal_version in ("r5539", "r11167", "r11184", "r11189"):
            assert exported_lines[1] == "--- 003 10 7 70 10 6 4 1 1 10 8 -- squadre: 10 quesiti: 7"
        elif journal_version in ("r17497", "r17505"):
            assert exported_lines[1] == "--- 003 10 7 70 10 6 4.1 1 1 10 8 -- squadre: 10 quesiti: 7"
        elif journal_version in ("r17548", "r20642", "r20644", "r25013"):
            assert exported_lines[1] == "--- 002 10+0 7:20 4.1;1 10-2 -- squadre: 10 quesiti: 7"
        else:
            raise ValueError("Invalid journal version")
