# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run a module entrypoint."""

import os
import subprocess
import sys

import pytest

from mathrace_interaction.typing import RunEntrypointFixtureType


@pytest.fixture
def run_entrypoint_fixture() -> RunEntrypointFixtureType:
    """Run a module entrypoint."""
    def _(module: str, arguments: list[str]) -> tuple[str, str]:
        """Run a module entrypoint (internal implementation)."""
        library_name = "mathrace_interaction"
        if "COVERAGE_RUN" not in os.environ or library_name not in module:
            executable = sys.executable
        else:
            # Propagate coverage run to the subprocess. Note that a different COVERAGE_FILE is used, so it will
            # be the caller's responsability to combine all files together when printing the coverage report.
            dash_joined_arguments = "_".join(arguments)
            printable_dash_joined_arguments = "".join(c for c in dash_joined_arguments if c.isalnum())
            coverage_file = (
                f'{os.path.join(os.getcwd(), os.environ.get("COVERAGE_FILE", ".coverage"))}'
                f'_{module}_{printable_dash_joined_arguments}')
            executable = (f"COVERAGE_FILE={coverage_file} {sys.executable} -m coverage run --source={library_name}")
        run_module = subprocess.run(f'{executable} -m {module} {" ".join(arguments)}', shell=True, capture_output=True)
        stdout = run_module.stdout.decode().strip()
        stderr = run_module.stderr.decode().strip()
        if run_module.returncode != 0:
            raise RuntimeError(
                f"Running {module} with arguments {arguments} failed with exit code {run_module.returncode}, "
                f"stdout {stdout}, stderr {stderr}")
        else:
            return stdout, stderr

    return _
