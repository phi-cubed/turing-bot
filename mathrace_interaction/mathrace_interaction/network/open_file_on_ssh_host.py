# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Connect to an SSH server."""

import io
import pathlib
import typing

import paramiko


def open_file_on_ssh_host(path: pathlib.Path, client: paramiko.SSHClient | None) -> typing.TextIO:
    """
    Open a local or remote file.

    Parameters
    ----------
    path
        The path of the file to be opened.
    client
        An SSH client by paramiko if the file is hosted on a remote SSH server. If None, the file is local.

    Returns
    -------
    :
        A I/O stream that reads the provided file.
    """
    if client is None:
        return open(path)
    else:
        stream = client.open_sftp().open(str(path))
        stream.prefetch()
        return io.StringIO(stream.read().decode())
