# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.test.ssh_server_fixture."""

import mockssh


def test_ssh_client_users(ssh_server: mockssh.Server) -> None:
    """Test the mockssh.Server fixture by listing the available users."""
    assert list(ssh_server.users) == ["user"]
