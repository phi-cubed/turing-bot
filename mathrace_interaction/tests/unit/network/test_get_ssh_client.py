# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.network.get_ssh_client."""

import typing

import mockssh
import paramiko
import pytest

import mathrace_interaction.network


@pytest.mark.parametrize("get_client", [
    lambda ssh_server: ssh_server.client("user"),
    lambda ssh_server: mathrace_interaction.network.get_ssh_client(
        ssh_server.host, "user", port=ssh_server.port, key_filename=ssh_server._users["user"][0])
])
def test_get_ssh_client_echo(
    ssh_server: mockssh.Server, get_client: typing.Callable[[mockssh.Server], paramiko.SSHClient]
) -> None:
    """Test get_ssh_client by running a simple command."""
    client = get_client(ssh_server)
    _, stdout, _ = client.exec_command("echo 'Hello from pytest'")
    assert stdout.read().decode().strip("\n") == "Hello from pytest"
