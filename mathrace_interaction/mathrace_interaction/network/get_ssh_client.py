# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Connect to an SSH server."""

import typing

import paramiko


def get_ssh_client(host: str, user: str, **kwargs: typing.Any) -> paramiko.SSHClient:  # noqa: ANN401
    """
    Connect to an SSH server.

    Parameters
    ----------
    host
        The SSH host.
    user
        The name of a user that is allowed to login into the SSH host.
        It must be possible to do so without typing a password.
    **kwargs
        Additional keyword arguments passed to paramiko.SSHClient.connect

    Returns
    -------
    :
        An SSH client by paramiko.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, **kwargs)
    return client
