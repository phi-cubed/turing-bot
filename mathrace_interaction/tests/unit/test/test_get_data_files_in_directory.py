# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.test.get_data_files_in_directory."""

import pathlib
import tempfile

import mathrace_interaction.test
import mathrace_interaction.typing


def test_get_data_files_in_directory_empty() -> None:
    """Test get_data_files_in_directory on an empty directory."""
    with tempfile.TemporaryDirectory() as directory:
        assert len(mathrace_interaction.test.get_data_files_in_directory(pathlib.Path(directory), "data")) == 0


def test_get_data_files_in_directory_only_files() -> None:
    """Test get_data_files_in_directory on a syntetic directory that only contains files."""
    with tempfile.TemporaryDirectory() as directory:
        directory_path = pathlib.Path(directory)
        pathlib.Path(directory_path / "file1.data").touch()
        pathlib.Path(directory_path / "file2.data").touch()
        pathlib.Path(directory_path / "file3.score").touch()
        assert len(mathrace_interaction.test.get_data_files_in_directory(pathlib.Path(directory), "data")) == 2


def test_get_data_files_in_directory_nested_directories() -> None:
    """Test get_data_files_in_directory on a syntetic directory that contains nested directories."""
    with tempfile.TemporaryDirectory() as directory:
        directory_path = pathlib.Path(directory)
        (directory_path / "subdir1").mkdir()
        pathlib.Path(directory_path / "subdir1" / "file1.data").touch()
        (directory_path / "subdir2").mkdir()
        pathlib.Path(directory_path / "subdir2" / "file2.data").touch()
        pathlib.Path(directory_path / "file3.score").touch()
        assert len(mathrace_interaction.test.get_data_files_in_directory(pathlib.Path(directory), "data")) == 2


def test_get_data_files_in_directory_symbolic_link(
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test get_data_files_in_directory on a syntetic directory that contains a symbolic link."""
    with tempfile.TemporaryDirectory() as directory:
        directory_path = pathlib.Path(directory)
        pathlib.Path(directory_path / "file1.data").touch()
        pathlib.Path(directory_path / "file2.data").symlink_to(pathlib.Path(directory_path / "file1.data"))
        assert len(mathrace_interaction.test.get_data_files_in_directory(pathlib.Path(directory), "data")) == 2
