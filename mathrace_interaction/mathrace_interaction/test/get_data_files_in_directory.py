# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Return all data files with a given extension in a specific directory."""

import pathlib


def get_data_files_in_directory(directory: pathlib.Path, extension: str) -> dict[str, pathlib.Path]:
    """Return all data files with a given extension in a specific directory."""
    file_set = set()
    for entry in directory.rglob("*"):
        assert entry.is_file() or entry.is_dir()
        if entry.is_file():
            if entry.suffix == f".{extension}":
                file_set.add(entry)
        elif entry.is_dir():
            pass
        else:  # pragma: no cover
            raise RuntimeError(f"Invalid {entry}")
    return {str(file_.relative_to(directory)): file_ for file_ in sorted(file_set)}
