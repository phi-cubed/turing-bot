# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""mathrace_interaction.filter module."""

import warnings

from mathrace_interaction.filter.journal_event_filterer import journal_event_filterer
from mathrace_interaction.filter.journal_event_filterer_by_id import journal_event_filterer_by_id
from mathrace_interaction.filter.journal_event_filterer_by_timestamp import journal_event_filterer_by_timestamp
from mathrace_interaction.filter.live_journal import LiveJournal
from mathrace_interaction.filter.strip_comments_and_unhandled_events_from_journal import (
    strip_comments_and_unhandled_events_from_journal)
from mathrace_interaction.filter.strip_mathrace_only_attributes_from_imported_turing import (
    strip_mathrace_only_attributes_from_imported_turing)
from mathrace_interaction.filter.strip_milliseconds_in_imported_turing import strip_milliseconds_in_imported_turing
from mathrace_interaction.filter.strip_trailing_zero_bonus_superbonus_from_imported_turing import (
    strip_trailing_zero_bonus_superbonus_from_imported_turing)

# Silence warning when trying to run modules as entrypoint
for entrypoint in (
    "journal_event_filterer_by_id", "journal_event_filterer_by_timestamp",
    "strip_comments_and_unhandled_events_from_journal", "strip_mathrace_only_attributes_from_imported_turing",
    "strip_milliseconds_in_imported_turing", "strip_trailing_zero_bonus_superbonus_from_imported_turing"
):
    warnings.filterwarnings(
        "ignore", message=(
            f"'{__name__}.{entrypoint}' found in sys.modules after import of package '{__name__}', "
            f"but prior to execution of '{__name__}.{entrypoint}'; this may result in unpredictable behaviour"
        )
    )
