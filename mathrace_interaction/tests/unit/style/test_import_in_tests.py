# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test that imports in tests do not use the 'from ... import ...' form."""

import pathlib


def test_import_in_tests() -> None:
    """Test that imports in tests do not use the 'from ... import ...' form."""
    root_dir = pathlib.Path(__file__).parent.parent.parent.parent
    failing_files = []
    for entry in (root_dir / "tests").rglob("*py"):
        assert entry.is_file()
        if entry != root_dir / "tests" / "unit" / "style" / "test_import_in_tests.py":
            # The if in the next like will surely fail when the test processes this file itself, so just skip it.
            if "from mathrace_interaction" in entry.read_text():
                failing_files.append(entry)
    assert len(failing_files) == 0, (
        "Remove 'from mathrace_interaction... import ...' from the following files: {failing_files}")
