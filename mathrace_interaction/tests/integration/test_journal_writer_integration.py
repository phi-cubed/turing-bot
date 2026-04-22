# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test interaction between turing and journal_writer."""

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
def test_journal_writer_integration(journal: typing.TextIO, journal_name: str, journal_version: str) -> None:
    """Test interaction between turing and journal_writer."""
    # First, import the journal into turing via journal_reader
    journal_year, _ = journal_name.split(os.sep, maxsplit=1)
    journal_date = datetime.datetime(int(journal_year), 1, 1, tzinfo=datetime.UTC)
    with mathrace_interaction.journal_reader(journal) as journal_stream:
        turing_dict = journal_stream.read(journal_name, journal_date)
    mathrace_interaction.filter.strip_mathrace_only_attributes_from_imported_turing(turing_dict)
    mathrace_interaction.filter.strip_trailing_zero_bonus_superbonus_from_imported_turing(turing_dict)
    gara = engine.models.Gara.create_from_dict(turing_dict)
    # Then, export it back via journal_writer
    with (
        io.StringIO("") as exported_journal,
        mathrace_interaction.journal_writer(exported_journal, journal_version) as journal_stream
    ):
        journal_stream.write(gara.to_dict())
        exported_journal_content = exported_journal.getvalue()
    # Since the exported journal may be slightly different to the original one, and those differences
    # are already tested in functional testing, convert it back to a turing dictionary, and verify it has
    # the same content as the first dictionary
    with mathrace_interaction.journal_reader(io.StringIO(exported_journal_content)) as converted_stream:
        converted_stream.strict_timestamp_race_events = False  # type: ignore[attr-defined]
        reimported_dict = converted_stream.read(journal_name, journal_date)
    mathrace_interaction.filter.strip_mathrace_only_attributes_from_imported_turing(reimported_dict)
    mathrace_interaction.filter.strip_trailing_zero_bonus_superbonus_from_imported_turing(reimported_dict)
    # The two dictionaries must be the same
    diff = jsondiff.diff(reimported_dict, turing_dict, syntax="symmetric")
    assert diff == {}


@pytest.mark.django_db
@pytest.mark.parametrize(
    (
        "input_file_option,output_file_option,race_name_option,race_date_option,journal_version_option,"
        "upload_option,download_option"
    ), [
        ("-i", "-o", "-n", "-d", "-v", "-u", "-d"),
        ("--input-file", "--output-file", "--race-name", "--race-date", "--journal-version", "--upload", "--download")
    ]
)
def test_journal_writer_entrypoint_integration(
    journal: typing.TextIO, run_entrypoint: mathrace_interaction.typing.RunEntrypointFixtureType,
    journal_name: str, journal_version: str, input_file_option: str, output_file_option: str, race_name_option: str,
    race_date_option: str, journal_version_option: str, upload_option: str, download_option: str
) -> None:
    """Test running journal_writer as entrypoint."""
    with tempfile.NamedTemporaryFile() as input_journal_file, tempfile.NamedTemporaryFile() as output_journal_file:
        # First, import the journal into turng via journal_reader
        journal_year, _ = journal_name.split(os.sep, maxsplit=1)
        journal_date = datetime.datetime(int(journal_year), 1, 1, tzinfo=datetime.UTC)
        with open(input_journal_file.name, "w") as input_journal_stream:
            input_journal_stream.write(journal.read())
        journal.seek(0)
        stdout, stderr = run_entrypoint(
            "mathrace_interaction.journal_reader", [
                input_file_option, input_journal_file.name, race_name_option, journal_name,
                race_date_option, journal_date.isoformat(), upload_option
            ]
        )
        assert stdout != ""
        assert stdout.isnumeric()
        assert stderr == ""
        imported_pk = stdout
        imported_dict = engine.models.Gara.objects.get(pk=int(imported_pk)).to_dict()
        # Then, export it back via journal_writer
        stdout, stderr = run_entrypoint(
            "mathrace_interaction.journal_writer", [
                download_option, imported_pk, journal_version_option, journal_version,
                output_file_option, output_journal_file.name
            ]
        )
        assert stdout == ""
        assert stderr == ""
        # Re-import the journal file and compare it to the first dictionary
        with mathrace_interaction.journal_reader(open(output_journal_file.name)) as converted_stream:
            converted_stream.strict_timestamp_race_events = False  # type: ignore[attr-defined]
            reimported_dict = converted_stream.read(journal_name, journal_date)
        mathrace_interaction.filter.strip_mathrace_only_attributes_from_imported_turing(reimported_dict)
        mathrace_interaction.filter.strip_trailing_zero_bonus_superbonus_from_imported_turing(reimported_dict)
        # The two dictionaries must be the same
        diff = jsondiff.diff(reimported_dict, imported_dict, syntax="symmetric")
        assert diff == {}
