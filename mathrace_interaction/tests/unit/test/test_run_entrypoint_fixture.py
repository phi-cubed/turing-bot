# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.test.run_entrypoint_fixture."""

import tempfile

import mathrace_interaction.typing


def test_run_entrypoint_with_hello_world(
    run_entrypoint: mathrace_interaction.typing.RunEntrypointFixtureType
) -> None:
    """Test the run_entrypoint fixture by running python3 -m __hello__."""
    stdout, stderr = run_entrypoint("__hello__", [])
    assert "Hello world!" in stdout
    assert stderr == ""


def test_run_entrypoint_with_base64_correct_flag(
    run_entrypoint: mathrace_interaction.typing.RunEntrypointFixtureType
) -> None:
    """Test the run_entrypoint fixture by running python3 -m base64 -e."""
    with tempfile.NamedTemporaryFile() as tmp_file:
        with open(tmp_file.name, "w") as tmp_stream:
            tmp_stream.write("test")
        stdout, stderr = run_entrypoint("base64", ["-e", tmp_file.name])
        assert stdout == "dGVzdA=="
        assert stderr == ""


def test_run_entrypoint_with_base64_wrong_flag(
    run_entrypoint: mathrace_interaction.typing.RunEntrypointFixtureType,
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test the run_entrypoint fixture by running python3 -m base64 with a wrong flag."""
    runtime_error_contains(
        lambda: run_entrypoint("base64", ["--wrong-flag"]),
        "Running base64 with arguments ['--wrong-flag'] failed with exit code 2, stdout , "
        "stderr option --wrong-flag not recognized")
