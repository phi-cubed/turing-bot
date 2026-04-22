# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.filter.strip_trailing_zero_bonus_superbonus_from_imported_turing."""

import copy
import json
import tempfile

import pytest

import mathrace_interaction.filter
import mathrace_interaction.typing


@pytest.fixture
def modified_dict(turing_dict: mathrace_interaction.typing.TuringDict) -> mathrace_interaction.typing.TuringDict:
    """Append trailing zeros to bonus and superbonus definition."""
    turing_dict_copy = copy.deepcopy(turing_dict)
    for (key_index, key) in enumerate(("fixed_bonus", "super_mega_bonus")):
        turing_dict_copy[key] = turing_dict[key] + ",0,0" * (key_index + 1)
    return turing_dict_copy


def test_strip_trailing_zero_bonus_superbonus_from_imported_turing(
    modified_dict: mathrace_interaction.typing.TuringDict, turing_dict: mathrace_interaction.typing.TuringDict
) -> None:
    """Test strip_trailing_zero_bonus_superbonus_from_imported_turing."""
    mathrace_interaction.filter.strip_trailing_zero_bonus_superbonus_from_imported_turing(modified_dict)
    assert modified_dict == turing_dict


@pytest.mark.parametrize("input_file_option,output_file_option", [("-i", "-o"), ("--input-file", "--output-file")])
def test_strip_trailing_zero_bonus_superbonus_from_imported_turing_entrypoint(
    modified_dict: mathrace_interaction.typing.TuringDict, turing_dict: mathrace_interaction.typing.TuringDict,
    run_entrypoint: mathrace_interaction.typing.RunEntrypointFixtureType,
    input_file_option: str, output_file_option: str
) -> None:
    """Test running strip_trailing_zero_bonus_superbonus_from_imported_turing as entrypoint."""
    with tempfile.NamedTemporaryFile() as input_json_file, tempfile.NamedTemporaryFile() as output_json_file:
        with open(input_json_file.name, "w") as input_json_stream:
            input_json_stream.write(json.dumps(modified_dict))
        stdout, stderr = run_entrypoint(
            "mathrace_interaction.filter.strip_trailing_zero_bonus_superbonus_from_imported_turing", [
                input_file_option, input_json_file.name, output_file_option, output_json_file.name
            ]
        )
        assert stdout == ""
        assert stderr == ""
        with open(output_json_file.name) as output_json_stream:
            imported_dict = json.load(output_json_stream)
        assert imported_dict == turing_dict
