# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Follow the mathrace journal of a live race, and register all events into a live session in turing."""

import argparse
import datetime
import json
import pathlib
import shutil
import time
import types
import typing

import jsondiff
import paramiko

from mathrace_interaction.filter import (
    strip_mathrace_only_attributes_from_imported_turing, strip_trailing_zero_bonus_superbonus_from_imported_turing)
from mathrace_interaction.journal_reader import journal_reader
from mathrace_interaction.network import get_ssh_client, open_file_on_ssh_host
from mathrace_interaction.typing import TuringDict


def live_journal_to_live_turing(
    open_input_file: typing.Callable[[], typing.TextIO], turing_models: types.ModuleType, turing_race_id: int,
    sleep: float, output_directory: pathlib.Path, termination_condition: typing.Callable[[int, bool], bool]
) -> None:
    """
    Follow the mathrace journal of a live race, and register all events into a live session in turing.

    Parameters
    ----------
    open_input_file
        A function that opens the input file, and returns a stream.
    turing_models
        The python module containing the turing models Gara, Consegna, Jolly and Bonus.
    turing_race_id
        The ID of the turing race to follow.
    sleep
        The amount of time to wait between consecutive reads of the input journal file.
    output_directory
        The path of the output directory
    termination_condition
        A function to determine whether to terminate the processing given the current time counter and
        a boolean which represents if the race has ended.
    """
    # Get the actual turing models out of the turing_models argument
    Gara = getattr(turing_models, "Gara")  # noqa: N806
    Squadra = getattr(turing_models, "Squadra")  # noqa: N806
    Consegna = getattr(turing_models, "Consegna")  # noqa: N806
    Jolly = getattr(turing_models, "Jolly")  # noqa: N806
    Bonus = getattr(turing_models, "Bonus")  # noqa: N806

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

    # Get the turing dictionary associated to the race at the time represented by the initial counter
    print(f"{time_counter=}")
    if time_counter == 0:
        print("\tInitializing from journal file")
        # Read and strip any race event, and delay processing them to the first iteration of the while loop below
        previous_turing_dict, _ = _convert_and_backup_input_file(
            turing_race.nome, turing_race.inizio, open_input_file, time_counter,
            live_journal_files_directory, live_turing_json_files_directory,
            clear_events=True)
        # Make sure that the turing race is actually consistent with the one on mathrace
        if turing_race.to_dict() != previous_turing_dict:
            raise RuntimeError(
                f"Turing race {turing_race_id} is not consistent with the one stored in the journal file. "
                "The difference between journal and turing races is "
                f'{jsondiff.diff(previous_turing_dict, turing_race.to_dict(), syntax="symmetric")}')
    else:
        print("\tInitializing from previous run")
        with open(live_turing_json_files_directory / f"{time_counter}.json") as turing_json_file:
            previous_turing_dict = json.load(turing_json_file)
        # Do not strip race events, otherwise they would be duplicated on the first iteration of the while loop below

    # Continuously read the input file
    time_counter += 1
    while True:
        print(f"{time_counter=}")
        # Get the turing dictionary associated to the race at the time represented by the current counter
        current_turing_dict, race_ended = _convert_and_backup_input_file(
            turing_race.nome, turing_race.inizio, open_input_file, time_counter,
            live_journal_files_directory, live_turing_json_files_directory,
            clear_events=False)
        # Determine newly added events, if any
        diff_turing_dict = jsondiff.diff(previous_turing_dict, current_turing_dict)
        print(f"\tDifference from previous time step is {diff_turing_dict}")
        assert isinstance(diff_turing_dict, dict), f"Expected a dict, got {type(diff_turing_dict)}"
        if len(diff_turing_dict.keys()) > 0:
            # New events were added
            assert len(diff_turing_dict.keys()) == 1, f"Expected only one key, got {diff_turing_dict.keys()}"
            assert "eventi" in diff_turing_dict.keys(), f"Expected only the eventi key, got {diff_turing_dict.keys()}"
            diff_turing_events = diff_turing_dict["eventi"]
            if isinstance(diff_turing_events, list):
                assert len(previous_turing_dict["eventi"]) == 0, (
                    f'Expected no previous events, but got {len(previous_turing_dict["eventi"])}')
                for event_dict in diff_turing_events:
                    assert isinstance(event_dict, dict), f"Expected a dict, got type({event_dict})"
                new_turing_events = diff_turing_events
            else:
                assert isinstance(diff_turing_events, dict), f"Expected a dict, got {type(diff_turing_events)}"
                assert len(diff_turing_events.keys()) == 1, f"Expected only one key, got {diff_turing_events.keys()}"
                assert jsondiff.insert in diff_turing_events.keys(), (
                    f"Expected only the insert key, got {diff_turing_events.keys()}")
                new_turing_position_and_events = diff_turing_events[jsondiff.insert]
                assert isinstance(new_turing_position_and_events, list), (
                    f"Expected a list, got {type(new_turing_position_and_events)}")
                new_turing_events = []
                for position_and_event in new_turing_position_and_events:
                    assert isinstance(position_and_event, tuple), f"Expected a tuple, got {type(position_and_event)}"
                    assert len(position_and_event) == 2, f"Expected two entries, got {position_and_event}"
                    event_position, event_dict = position_and_event
                    assert isinstance(event_position, int), f"Expected an int, got type({event_position})"
                    assert isinstance(event_dict, dict), f"Expected a dict, got type({event_dict})"
                    new_turing_events.append(event_dict)
            # Communicate new events to the live turing instance
            for event_dict in new_turing_events:
                print(f"\tAdding event {event_dict}")
                assert "subclass" in event_dict
                event_dict_copy = dict(event_dict)
                # Convert datetime string representation into date time object
                event_dict_copy["orario"] = datetime.datetime.fromisoformat(event_dict["orario"])
                # The team ID is local to the race, and needs to be converted into the primary key
                # in the database
                event_dict_copy["squadra"] = Squadra.objects.get(gara=turing_race, num=event_dict["squadra_id"])
                del event_dict_copy["squadra_id"]
                # Create an object of the event subclass
                event_subclass = event_dict_copy.pop("subclass")
                assert event_subclass in ("Consegna", "Jolly", "Bonus"), f"Invalid event subclass {event_subclass}"
                if event_subclass == "Consegna":
                    event_obj = Consegna(gara=turing_race, **event_dict_copy)
                elif event_subclass == "Jolly":
                    event_obj = Jolly(gara=turing_race, **event_dict_copy)
                elif event_subclass == "Bonus":
                    event_obj = Bonus(gara=turing_race, **event_dict_copy)
                event_obj.save()
                # Django requires to explicitly set the datetime field after saving, see Gara.create_from_dict
                event_obj.orario = event_dict_copy["orario"]
                event_obj.save()
                assert event_obj.orario == event_dict_copy["orario"]
        # Update the previous turing dictionary
        previous_turing_dict = current_turing_dict
        # Write out the time counter
        time_counter_file.write_text(str(time_counter))
        # Break out of the loop if the race has ended
        if termination_condition(time_counter, race_ended):
            break
        # Upate the time counter
        time_counter += 1
        # Wait before reading again the updated version of the input file
        time.sleep(sleep)


def _convert_and_backup_input_file(
    race_name: str, race_date: datetime.datetime, open_input_file: typing.Callable[[], typing.TextIO],
    time_counter: int, live_journal_files_directory: pathlib.Path, live_turing_json_files_directory: pathlib.Path,
    clear_events: bool = False
) -> tuple[TuringDict, bool]:
    """
    Open the input journal file and back it up. Then, convert it to a turing dictionary, and back that up too.

    Parameters
    ----------
    race_name
        Name of the race
    race_date
        Date of the race
    open_input_file
        A function that opens the input file, and returns a stream.
    time_counter
        Current value of the time counter.
    live_journal_files_directory
        The path of the directory where the journal files backups are stored.
    live_turing_json_files_directory
        The path of the directory where the turing dictionaries backups are stored.
    clear_events
        Clear out events after reading.
    """
    with open_input_file() as journal_file:
        race_ended = ("termine gara" in journal_file.read())
        journal_file.seek(0)
        (live_journal_files_directory / f"{time_counter}.journal").write_text(journal_file.read())
        shutil.copy(
            live_journal_files_directory / f"{time_counter}.journal",
            live_journal_files_directory / "latest.journal")
        journal_file.seek(0)
        with journal_reader(journal_file) as journal_to_turing:
            turing_dict = journal_to_turing.read(race_name, race_date)
        _clean_up_turing_dictionary(turing_dict)
        if clear_events:
            assert "eventi" in turing_dict
            turing_dict["eventi"].clear()
            (live_journal_files_directory / f"{time_counter}.journal.needs_to_clear_events").touch()
        with open(live_turing_json_files_directory / f"{time_counter}.json", "w") as turing_json_file:
            turing_json_file.write(json.dumps(turing_dict, indent=4))
        shutil.copy(
            live_turing_json_files_directory / f"{time_counter}.json",
            live_turing_json_files_directory / "latest.json")
    return turing_dict, race_ended


def _clean_up_turing_dictionary(turing_dict: TuringDict) -> None:
    """Clean up a turing dictionary in place."""
    strip_mathrace_only_attributes_from_imported_turing(turing_dict)
    strip_trailing_zero_bonus_superbonus_from_imported_turing(turing_dict)

if __name__ == "__main__":  # pragma: no cover
    # This import requires turing to be available, and thus cannot be moved to the common section.
    # We skip coverage testing of this part because we cannot cover this in unit tests, since they
    # cannot interact with turing. Testing this entrypoint is delayed to integration testing.
    import django
    django.setup()

    import engine.models

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-i", "--input-file", type=str, required=True, help="Path of the input journal file")
    parser.add_argument(
        "-h", "--input-file-host", type=str, required=False, default="", help="SSH host of the input journal file")
    parser.add_argument(
        "-u", "--input-file-host-user", type=str, required=False, default="", help="SSH host of the input journal file")
    parser.add_argument("-t", "--turing-race-id", type=int, required=True, help="ID of the turing race to follow")
    parser.add_argument(
        "-s", "--sleep", type=float, required=False, default=1.0,
        help="The amount of time to wait between consecutive reads of the input journal file")
    parser.add_argument("-o", "--output-directory", type=str, required=True, help="Path of the output directory")
    args = parser.parse_args()

    input_file_client: paramiko.SSHClient | None = None
    if args.input_file_host != "":
        input_file_client = get_ssh_client(args.input_file_host, args.input_file_host_user)
    live_journal_to_live_turing(
        lambda: open_file_on_ssh_host(pathlib.Path(args.input_file), input_file_client),
        engine.models, args.turing_race_id, args.sleep, pathlib.Path(args.output_directory),
        lambda time_counter, race_ended: race_ended)
