# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Strip attributes marked as mathrace only from an imported turing dict."""

import argparse
import json

from mathrace_interaction.typing import TuringDict


def strip_mathrace_only_attributes_from_imported_turing(imported_dict: TuringDict) -> None:
    """
    Strip attributes marked as mathrace only from an imported turing dict.

    The dictionary is modified in-place.

    Parameters
    ----------
    imported_dict
        The turing dictionary representing the race, imported from a mathrace journal.
    """
    if "mathrace_only" in imported_dict:
        del imported_dict["mathrace_only"]
    if "mathrace_id" in imported_dict:
        del imported_dict["mathrace_id"]
    for value in imported_dict.values():
        if isinstance(value, list):
            for value_entry in value:
                assert isinstance(value_entry, dict)
                strip_mathrace_only_attributes_from_imported_turing(value_entry)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input-file", type=str, required=True, help="Path of the input json file")
    parser.add_argument("-o", "--output-file", type=str, required=True, help="Path of the output json file")
    args = parser.parse_args()
    with open(args.input_file) as input_json_stream:
        imported_dict = json.load(input_json_stream)
    strip_mathrace_only_attributes_from_imported_turing(imported_dict)
    with open(args.output_file, "w") as output_json_stream:
        output_json_stream.write(json.dumps(imported_dict, indent=4))
