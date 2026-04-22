# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.determine_journal_version on journals in data directory."""

import typing

import mathrace_interaction


def test_determine_journal_version_on_data(journal: typing.TextIO, journal_version: str) -> None:
    """Test determine_journal_version with all journals in the data directory."""
    assert mathrace_interaction.determine_journal_version(journal) == journal_version
