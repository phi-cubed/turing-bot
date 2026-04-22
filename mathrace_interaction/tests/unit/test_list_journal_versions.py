# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.list_journal_versions."""


import mathrace_interaction
import mathrace_interaction.typing


def test_list_journal_versions() -> None:
    """Test the cardinality of versions returned by list_journal_versions."""
    versions = mathrace_interaction.list_journal_versions()
    assert len(versions) == 10


def test_list_journal_versions_entrypoint(
    run_entrypoint: mathrace_interaction.typing.RunEntrypointFixtureType
) -> None:
    """Test running list_journal_versions as entrypoint."""
    stdout, _stderr = run_entrypoint("mathrace_interaction.list_journal_versions", [])
    assert len(stdout.split(", ")) == 10
