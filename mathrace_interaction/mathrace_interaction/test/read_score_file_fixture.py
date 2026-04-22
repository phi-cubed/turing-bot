# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read score file from data directory."""

import pathlib

import pytest
import simpleeval

from mathrace_interaction.typing import ReadScoreFileFixtureType


@pytest.fixture
def read_score_file_fixture() -> ReadScoreFileFixtureType:
    """Read score file from data directory."""
    evaluator = simpleeval.EvalWithCompoundTypes()

    def _(directory: pathlib.Path, race_data_name: str) -> list[int]:
        """Read score file from data directory (internal implementation)."""
        with open((directory / race_data_name).with_suffix(".score")) as score_stream:
            scores = evaluator.eval(score_stream.read())
            assert isinstance(scores, list)
            assert all(isinstance(score, int) for score in scores)
            return scores

    return _
