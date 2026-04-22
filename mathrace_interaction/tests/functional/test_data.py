# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test consistency of files in data."""

import pathlib

import pytest


def test_data_directory_exists(data_dir: pathlib.Path) -> None:
    """Test the presence of the data directory."""
    assert data_dir.exists()
    assert data_dir.is_dir()


@pytest.mark.parametrize("race_extension", [".journal", ".json"])
def test_data_has_a_score_file_for_every_race_file(data_dir: pathlib.Path, race_extension: str) -> None:
    """Test that every journal or json file has an associated score file."""
    found_files = 0
    for entry in data_dir.rglob(f"*{race_extension}"):
        assert entry.is_file() or entry.is_dir()
        if entry.is_file():
            assert entry.with_suffix(".score").exists()
            found_files += 1
        elif entry.is_dir():
            pass
        else:
            raise RuntimeError(f"Invalid {entry}")
    assert found_files > 0


def test_data_has_a_race_file_for_every_score_file(data_dir: pathlib.Path) -> None:
    """Test that every journal or json file has an associated score file."""
    found_files = 0
    for entry in data_dir.rglob("*.score"):
        assert entry.is_file() or entry.is_dir()
        if entry.is_file():
            exists_journal = entry.with_suffix(".journal").exists()
            exists_json = entry.with_suffix(".json").exists()
            assert int(exists_journal) + int(exists_json) == 1
            found_files += 1
        elif entry.is_dir():
            pass
        else:
            raise RuntimeError(f"Invalid {entry}")
    assert found_files > 0


def test_data_contains_only_journal_and_score_files(data_dir: pathlib.Path) -> None:
    """Test that the data directory only contains journal, json and score files."""
    for entry in data_dir.rglob("*"):
        assert entry.is_file() or entry.is_dir()
        if entry.is_file():
            if entry.name == "fix_phiquadro_journals.sh":
                # allow auxiliary script
                pass
            else:
                assert entry.suffix in (".journal", ".json", ".score")
        elif entry.is_dir():
            pass
        else:
            raise RuntimeError(f"Invalid {entry}")
