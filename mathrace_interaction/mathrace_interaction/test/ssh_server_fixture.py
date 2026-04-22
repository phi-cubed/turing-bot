# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create a mock ssh server."""

import pathlib
import tempfile
import typing

import Cryptodome.PublicKey.RSA
import mockssh
import pytest


@pytest.fixture(scope="session")
def ssh_server_fixture() -> typing.Generator[mockssh.Server, None, None]:
    """Create a mock ssh server."""
    with tempfile.TemporaryDirectory() as home_ssh_directory:
        # Generate RSA public key and private key
        key = Cryptodome.PublicKey.RSA.generate(2048)
        home_ssh_path = pathlib.Path(home_ssh_directory)
        (home_ssh_path / "id_rsa").write_text(key.export_key().decode())
        (home_ssh_path / "id_rsa.pub").write_text(key.publickey().export_key().decode())
        # Create the SSH server
        with mockssh.Server({"user": str(home_ssh_path / "id_rsa")}) as s:
            yield s
