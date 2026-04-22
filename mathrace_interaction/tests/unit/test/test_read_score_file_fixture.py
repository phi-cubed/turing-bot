# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.test.read_score_file_fixture."""

import pathlib
import tempfile

import mathrace_interaction.typing


def test_read_score_file_fixture(
    read_score_file: mathrace_interaction.typing.ReadScoreFileFixtureType
) -> None:
    """Test the read_score_file fixture by writing and reading back a simple list."""
    with tempfile.TemporaryDirectory() as output_directory:
        output_path = pathlib.Path(output_directory)
        with open(output_path / "test.score", "w") as score_stream:
            score_stream.write("# this is a comment\n")
            score_stream.write("[1,\n")
            score_stream.write("2,\n")
            score_stream.write("# another comment\n")
            score_stream.write("3,\n")
            score_stream.write("4]")
        scores = read_score_file(output_path, "test.score")
        assert scores == [1, 2, 3, 4]
