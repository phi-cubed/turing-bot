# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Follow a live session in turing and convert it into a sequence of mathrace journals."""

import argparse
import json
import pathlib
import shutil
import time
import types
import typing

from mathrace_interaction.journal_writer import journal_writer
from mathrace_interaction.typing import TuringDict


def live_turing_to_live_journal(
    turing_models: types.ModuleType, turing_race_id: int, journal_version: str,
    sleep: float, output_directory: pathlib.Path, termination_condition: typing.Callable[[int], bool]
) -> None:
    """
    Follow a live session in turing and convert it into a sequence of mathrace journals.

    Parameters
    ----------
    turing_models
        The python module containing the turing model Gara.
    turing_race_id
        The ID of the turing race to follow.
    journal_version
        Version of the output journal file
    sleep
        The amount of time to wait between consecutive reads of the turing state.
    output_directory
        The path of the output directory
    termination_condition
        A function to determine whether to terminate the processing given the current time counter.
    """
    # Get the actual turing models out of the turing_models argument
    Gara = getattr(turing_models, "Gara")  # noqa: N806

    # Get the turing race from its ID
    turing_race = Gara.objects.get(pk=turing_race_id)

    # The race must have been started before running this script
    if turing_race.inizio is None:
        raise RuntimeError(f"Please start race {turing_race_id} from the turing web interface")

    # Create the output directory if it does not exist yet
    output_directory.mkdir(parents=True, exist_ok=True)

    # Create subdirectories in the output directory, if they do not exist yet
    live_journal_files_directory = output_directory / "live_journal_files"
    live_turing_json_files_directory = output_directory / "live_turing_json_files"
    live_journal_files_directory.mkdir(parents=True, exist_ok=True)
    live_turing_json_files_directory.mkdir(parents=True, exist_ok=True)

    # Read the current time counter if available, otherwise set it to zero
    time_counter = 0
    time_counter_file = output_directory / "time_counter.txt"
    if time_counter_file.exists():
        time_counter = int(time_counter_file.read_text())
    else:
        time_counter_file.write_text(str(time_counter))

    # Continuously read the turing state
    while True:
        print(f"{time_counter=}")
        # Get the turing dictionary associated to the race at the time represented by the current counter
        _convert_and_backup_turing_dict(
            turing_race.to_dict(), time_counter, journal_version, live_journal_files_directory,
            live_turing_json_files_directory)
        # Write out the time counter
        time_counter_file.write_text(str(time_counter))
        # Break out of the loop if the race has ended
        if termination_condition(time_counter):
            break
        # Upate the time counter
        time_counter += 1
        # Wait before reading again the updated version of the turing state
        time.sleep(sleep)


def _convert_and_backup_turing_dict(
    turing_dict: TuringDict, time_counter: int, journal_version: str,
    live_journal_files_directory: pathlib.Path, live_turing_json_files_directory: pathlib.Path
) -> None:
    """
    Convert the current turing state into a dictionary and a journal file, and back up those files.

    Parameters
    ----------
    turing_dict
        Dictionary representing the current turing state.
    time_counter
        Current value of the time counter.
    journal_version
        Version of the output journal file
    live_journal_files_directory
        The path of the directory where the journal files backups are stored.
    live_turing_json_files_directory
        The path of the directory where the turing dictionaries backups are stored.
    """
    with open(live_turing_json_files_directory / f"{time_counter}.json", "w") as turing_json_file:
        turing_json_file.write(json.dumps(turing_dict, indent=4))
    shutil.copy(
        live_turing_json_files_directory / f"{time_counter}.json",
        live_turing_json_files_directory / "latest.json")
    with journal_writer(
        open(live_journal_files_directory / f"{time_counter}.journal", "w"), journal_version
    ) as journal_file:
        journal_file.write(turing_dict)
    shutil.copy(
        live_journal_files_directory / f"{time_counter}.journal",
        live_journal_files_directory / "latest.journal")


if __name__ == "__main__":  # pragma: no cover
    # This import requires turing to be available, and thus cannot be moved to the common section.
    # We skip coverage testing of this part because we cannot cover this in unit tests, since they
    # cannot interact with turing. Testing this entrypoint is delayed to integration testing.
    import django
    django.setup()

    import engine.models

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-t", "--turing-race-id", type=int, required=True, help="ID of the turing race to follow")
    parser.add_argument(
        "-s", "--sleep", type=float, required=False, default=1.0,
        help="The amount of time to wait between consecutive turing race exports")
    parser.add_argument("-v", "--journal-version", type=str, required=True, help="Version of the output journal file")
    parser.add_argument("-o", "--output-directory", type=str, required=True, help="Path of the output directory")
    args = parser.parse_args()

    live_turing_to_live_journal(
        engine.models, args.turing_race_id, args.journal_version, args.sleep, pathlib.Path(args.output_directory),
        lambda time_counter: False)
