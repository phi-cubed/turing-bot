# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.test.mock_models."""

import mathrace_interaction.test.mock_models
import mathrace_interaction.typing


def test_mock_models(turing_dict: mathrace_interaction.typing.TuringDict) -> None:
    """Test mock_models by loading and exporting an existing turing race."""
    Gara = mathrace_interaction.test.mock_models.Gara  # noqa: N806
    turing_race = Gara.create_from_dict(turing_dict)
    assert turing_race.to_dict() == turing_dict
    assert Gara.objects.get(turing_race.pk) is turing_race
    # Saving again will not change the output of GaraObjects.get
    turing_race.save()
    assert Gara.objects.get(turing_race.pk) is turing_race
