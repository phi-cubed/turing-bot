# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test that the files produced by journal_reader can be imported into turing."""

import datetime
import io
import os
import tempfile
import typing

import engine.models
import jsondiff
import pytest

import mathrace_interaction
import mathrace_interaction.filter
import mathrace_interaction.typing


@pytest.mark.django_db
def test_journal_reader_integration(journal: typing.TextIO, journal_name: str) -> None:
    """Test that journal_reader can import journals in the data directory."""
    journal_year, _ = journal_name.split(os.sep, maxsplit=1)
    journal_date = datetime.datetime(int(journal_year), 1, 1, tzinfo=datetime.UTC)
    with mathrace_interaction.journal_reader(journal) as journal_stream:
        turing_dict = journal_stream.read(journal_name, journal_date)
    mathrace_interaction.filter.strip_mathrace_only_attributes_from_imported_turing(turing_dict)
    mathrace_interaction.filter.strip_trailing_zero_bonus_superbonus_from_imported_turing(turing_dict)
    gara = engine.models.Gara.create_from_dict(turing_dict)
    diff = jsondiff.diff(gara.to_dict(), turing_dict, syntax="symmetric")
    assert diff == {}


@pytest.mark.django_db
def test_journal_reader_without_date_integration(journal: typing.TextIO, journal_name: str) -> None:
    """Test that journal_reader can import journals in the data directory (race setup only)."""
    with mathrace_interaction.journal_reader(journal) as journal_stream:
        turing_dict = journal_stream.read(journal_name, None)
    mathrace_interaction.filter.strip_mathrace_only_attributes_from_imported_turing(turing_dict)
    mathrace_interaction.filter.strip_trailing_zero_bonus_superbonus_from_imported_turing(turing_dict)
    assert len(turing_dict["eventi"]) == 0
    gara = engine.models.Gara.create_from_dict(turing_dict)
    diff = jsondiff.diff(gara.to_dict(), turing_dict, syntax="symmetric")
    assert diff == {}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "input_file_option,race_name_option,race_date_option,race_setup_only_option,upload_option", [
        ("-i", "-n", "-d", "", "-u"),
        ("--input-file", "--race-name", "--race-date", "", "--upload"),
        ("-i", "-n", "", "-s", "-u"),
        ("--input-file", "--race-name", "", "--race-setup-only", "--upload"),
    ]
)
def test_journal_reader_entrypoint_integration(
    journal: typing.TextIO, run_entrypoint: mathrace_interaction.typing.RunEntrypointFixtureType,
    journal_name: str, input_file_option: str, race_name_option: str, race_date_option: str,
    race_setup_only_option: str, upload_option: str
) -> None:
    """Test running journal_reader as entrypoint."""
    with tempfile.NamedTemporaryFile() as journal_file:
        with open(journal_file.name, "w") as journal_stream:
            journal_stream.write(journal.read())
        journal.seek(0)
        if race_date_option != "":
            journal_year, _ = journal_name.split(os.sep, maxsplit=1)
            journal_date = datetime.datetime(int(journal_year), 1, 1, tzinfo=datetime.UTC)
            race_date_or_setup_only_options = [race_date_option, journal_date.isoformat()]
        else:
            journal_date = None
            race_date_or_setup_only_options = [race_setup_only_option]
        stdout, stderr = run_entrypoint(
            "mathrace_interaction.journal_reader", [
                input_file_option, journal_file.name, race_name_option, journal_name,
                *race_date_or_setup_only_options, upload_option
            ]
        )
        assert stdout != ""
        assert stdout.isnumeric()
        assert stderr == ""
        imported_dict = engine.models.Gara.objects.get(pk=int(stdout)).to_dict()
        # Convert a further copy without upload for comparison
        journal_copy = io.StringIO(journal.read())
        journal.seek(0)
        with mathrace_interaction.journal_reader(journal_copy) as expected_stream:
            expected_dict = expected_stream.read(journal_name, journal_date)
        mathrace_interaction.filter.strip_mathrace_only_attributes_from_imported_turing(expected_dict)
        if race_date_option == "":
            assert len(expected_dict["eventi"]) == 0
        mathrace_interaction.filter.strip_trailing_zero_bonus_superbonus_from_imported_turing(expected_dict)
        assert imported_dict == expected_dict
