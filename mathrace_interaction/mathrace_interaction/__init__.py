# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""mathrace_interaction main module."""

import warnings

from mathrace_interaction.determine_journal_version import determine_journal_version
from mathrace_interaction.journal_reader import journal_reader
from mathrace_interaction.journal_version_converter import journal_version_converter
from mathrace_interaction.journal_writer import journal_writer
from mathrace_interaction.list_journal_versions import list_journal_versions
from mathrace_interaction.live_journal_to_live_turing import live_journal_to_live_turing
from mathrace_interaction.live_turing_to_html import live_turing_to_html
from mathrace_interaction.live_turing_to_live_journal import live_turing_to_live_journal

# Silence warning when trying to run modules as entrypoint
for entrypoint in (
    "determine_journal_version", "journal_reader", "journal_version_converter", "journal_writer",
    "list_journal_versions", "live_journal_to_live_turing", "live_turing_to_html", "live_turing_to_live_journal"
):
    warnings.filterwarnings(
        "ignore", message=(
            f"'{__name__}.{entrypoint}' found in sys.modules after import of package '{__name__}', "
            f"but prior to execution of '{__name__}.{entrypoint}'; this may result in unpredictable behaviour"
        )
    )
