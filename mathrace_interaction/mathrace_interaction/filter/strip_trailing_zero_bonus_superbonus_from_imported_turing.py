# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Strip trailing zeros in bonus and superbonus from an imported turing dict."""

import argparse
import json

from mathrace_interaction.typing import TuringDict


def strip_trailing_zero_bonus_superbonus_from_imported_turing(imported_dict: TuringDict) -> None:
    """
    Strip trailing zeros in bonus and superbonus from an imported turing dict.

    The dictionary is modified in-place.

    Parameters
    ----------
    imported_dict
        The turing dictionary representing the race, imported from a mathrace journal.
    """
    for key in ("fixed_bonus", "super_mega_bonus"):
        if key in imported_dict:
            imported_dict[key] = ",".join([x for x in imported_dict[key].split(",") if int(x) > 0])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input-file", type=str, required=True, help="Path of the input json file")
    parser.add_argument("-o", "--output-file", type=str, required=True, help="Path of the output json file")
    args = parser.parse_args()
    with open(args.input_file) as input_json_stream:
        imported_dict = json.load(input_json_stream)
    strip_trailing_zero_bonus_superbonus_from_imported_turing(imported_dict)
    with open(args.output_file, "w") as output_json_stream:
        output_json_stream.write(json.dumps(imported_dict, indent=4))
