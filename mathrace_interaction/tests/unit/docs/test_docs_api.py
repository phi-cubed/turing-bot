# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test consistency of docs/api.rst with modules in the actual library."""

import os
import pathlib


def test_docs_api() -> None:
    """Test consistency of docs/api.rst with modules in the actual library."""
    root_dir = pathlib.Path(__file__).parent.parent.parent.parent
    docs_dir = root_dir / "docs"
    source_dir = root_dir / "mathrace_interaction"
    # Get the list of modules reported in docs/api.rst
    modules_in_api_rst = []
    with open(docs_dir / "api.rst") as api_rst_stream:
        for line in api_rst_stream:
            line = line.strip("\n").strip(" ")
            if line.startswith("mathrace_interaction"):
                modules_in_api_rst.append(line)
    # Get the modules in the actual library
    modules_in_source_dir = []
    for entry in source_dir.rglob("*__init__.py"):
        assert entry.is_file()
        modules_in_source_dir.append(str(entry.relative_to(root_dir).parent).replace(os.sep, "."))
    # Compare the two lists
    modules_compare = set(modules_in_api_rst).symmetric_difference(modules_in_source_dir)
    assert len(modules_compare) == 0, (
        "docs/api.rst is not consistent with modules in the actual library: the symmetric difference "
        "of the modules is {modules_compare}")
    # Ensure that modules reported in docs/api.rst are alphabetically ordered
    modules_in_api_rst_ordered = list(sorted(modules_in_api_rst))
    assert modules_in_api_rst == modules_in_api_rst_ordered, "docs/api.rst is not alphabetically orderdered."
