# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.filter.strip_milliseconds_in_imported_turing."""

import copy
import datetime
import json
import random
import tempfile

import pytest

import mathrace_interaction.filter
import mathrace_interaction.typing


@pytest.fixture
def random_dict(turing_dict: mathrace_interaction.typing.TuringDict) -> mathrace_interaction.typing.TuringDict:
    """Randomly add change the milliseconds field of all events in the provided dictionary."""
    turing_dict_copy = copy.deepcopy(turing_dict)
    for e in turing_dict_copy["eventi"]:
        e["orario"] = datetime.datetime.fromisoformat(e["orario"]).replace(
            microsecond=random.randrange(1, 1000) * 1000).isoformat()
    return turing_dict_copy


def test_strip_milliseconds_in_imported_turing(
    random_dict: mathrace_interaction.typing.TuringDict, turing_dict: mathrace_interaction.typing.TuringDict
) -> None:
    """Test strip_milliseconds_in_imported_turing."""
    mathrace_interaction.filter.strip_milliseconds_in_imported_turing(random_dict)
    assert random_dict == turing_dict


@pytest.mark.parametrize("input_file_option,output_file_option", [("-i", "-o"), ("--input-file", "--output-file")])
def test_strip_milliseconds_in_imported_turing_entrypoint(
    random_dict: mathrace_interaction.typing.TuringDict, turing_dict: mathrace_interaction.typing.TuringDict,
    run_entrypoint: mathrace_interaction.typing.RunEntrypointFixtureType,
    input_file_option: str, output_file_option: str
) -> None:
    """Test running strip_milliseconds_in_imported_turing as entrypoint."""
    with tempfile.NamedTemporaryFile() as input_json_file, tempfile.NamedTemporaryFile() as output_json_file:
        with open(input_json_file.name, "w") as input_json_stream:
            input_json_stream.write(json.dumps(random_dict))
        stdout, stderr = run_entrypoint(
            "mathrace_interaction.filter.strip_milliseconds_in_imported_turing", [
                input_file_option, input_json_file.name, output_file_option, output_json_file.name
            ]
        )
        assert stdout == ""
        assert stderr == ""
        with open(output_json_file.name) as output_json_stream:
            imported_dict = json.load(output_json_stream)
        assert imported_dict == turing_dict
