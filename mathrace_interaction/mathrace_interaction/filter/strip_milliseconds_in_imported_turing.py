# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Strip fictitious milliseconds that have been added to a turing dictionary in case of events at the same time."""

import argparse
import datetime
import json

from mathrace_interaction.typing import TuringDict


def strip_milliseconds_in_imported_turing(imported_dict: TuringDict) -> None:
    """
    Strip fictitious milliseconds that have been added to a turing dictionary in case of events at the same time.

    The journal reader adds one millisecond for every event happening at the same time. In some cases, for instance
    when writing back the turing dictionary to a journal file, it may be desirable to strip those extra milliseconds.
    The ordering would be preserved in the output journal file, but it would necessarily be preserved in turing
    without the fictitious milliseconds.

    The dictionary is modified in-place.

    Parameters
    ----------
    imported_dict
        The turing dictionary representing the race, imported from a mathrace journal.
    """
    imported_dict["inizio"] = datetime.datetime.fromisoformat(
        imported_dict["inizio"]).replace(microsecond=0).isoformat()
    for e in imported_dict["eventi"]:
        e["orario"] = datetime.datetime.fromisoformat(e["orario"]).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input-file", type=str, required=True, help="Path of the input json file")
    parser.add_argument("-o", "--output-file", type=str, required=True, help="Path of the output json file")
    args = parser.parse_args()
    with open(args.input_file) as input_json_stream:
        imported_dict = json.load(input_json_stream)
    strip_milliseconds_in_imported_turing(imported_dict)
    with open(args.output_file, "w") as output_json_stream:
        output_json_stream.write(json.dumps(imported_dict, indent=4))
