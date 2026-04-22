# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Define two parametrized journal fixtures, and their respective versions."""

import typing

import pytest


def parametrize_journal_fixtures(
    generate_journals: typing.Callable[[], dict[str, typing.TextIO]],
    generate_journal_versions: typing.Callable[[], dict[str, str]],
    metafunc: pytest.Metafunc
) -> None:
    """
    Define two parametrized journal fixtures, and their respective versions.

    This functions defines the following fixtures:
    * journal: typing.TextIO
    * journal_version: str
    * journal_name: str
    * other_journal: typing.TextIO
    * other_journal_version: str
    * other_journal_name: str

    Note that the parameters are passed in a callables (e.g., lambda functions) rather than directly as dictionaries
    because internally this function will generate two copies. The two copies must not be sharing the same stream.

    Parameters
    ----------
    generate_journals
        A function that generates a dictionary from journal name to a typing.TextIO object that opens the journal.
    generate_journal_versions
        A function that generates a dictionary from journal name to a string that represents the journal version.
        The dictionary must have the same keys as the ones returned by generate_journals.
    metafunc:
        The pytest metafunction that will add the parametrization.
    """
    names = list(generate_journal_versions().keys())
    _names_check = set(generate_journals().keys()).symmetric_difference(names)
    assert len(_names_check) == 0, (
        f"The two generators return different keys: the symmetric difference of the returned keys is {_names_check}")

    journals = _dict_to_list(generate_journals(), names)
    journal_versions = _dict_to_list(generate_journal_versions(), names)
    journal_names = names
    journal_ids = names

    other_journals = _dict_to_list(generate_journals(), names)  # cannot reuse journals: the streams must be different!
    other_journal_versions = list(journal_versions)  # create a copy of the one associated to journals!
    other_journal_names = list(journal_names)  # create a copy of the one associated to journals!
    other_journal_ids = [f"other: {n}" for n in names]

    # Add parametrization

    for fixture_names_group, parametrized_values_group, group_ids in (
        [
            ("journal", "journal_version", "journal_name"),
            (journals, journal_versions, journal_names),
            journal_ids
        ],
        [
            ("other_journal", "other_journal_version", "other_journal_name"),
            (other_journals, other_journal_versions, other_journal_names),
            other_journal_ids
        ]
    ):
        required_fixture_names = []
        required_parametrized_values = []
        for fixture_name, parametrized_values in zip(fixture_names_group, parametrized_values_group):
            assert isinstance(fixture_name, str)
            if fixture_name in metafunc.fixturenames:
                required_fixture_names.append(fixture_name)
                required_parametrized_values.append(parametrized_values)
        if len(required_fixture_names) == 1:
            metafunc.parametrize(required_fixture_names[0], required_parametrized_values[0], ids=group_ids)
        elif len(required_fixture_names) > 1:
            metafunc.parametrize(
                ",".join(required_fixture_names), list(zip(*required_parametrized_values)), ids=group_ids)


def _dict_to_list(dictionary: dict[str, typing.Any], key_lists: list[str]) -> list[typing.Any]:
    """Convert the dictionary to a list of its values, sorted as in key_lists."""
    return [dictionary[k] for k in key_lists]
