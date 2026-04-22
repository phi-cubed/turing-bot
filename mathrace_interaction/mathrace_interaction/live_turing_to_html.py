# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Follow a live session in turing and convert it into a sequence of html files."""

import argparse
import datetime
import json
import pathlib
import shutil
import time
import types
import typing

import prettytable
import pytz

from mathrace_interaction.network import TuringClassificationSelenium


def live_turing_to_html(
    turing_url: str, turing_models: types.ModuleType, turing_race_id: int, turing_race_admin_password: str,
    sleep: float, output_directory: pathlib.Path, compute_current_time: typing.Callable[[int], datetime.datetime],
    termination_condition: typing.Callable[[int], bool]
) -> None:  # pragma: no cover
    """
    Follow a live session in turing and convert it into a sequence of html files.

    Parameters
    ----------
    turing_url
        The URL of the live turing instance.
    turing_models
        The python module containing the turing model Gara.
    turing_race_id
        The ID of the turing race to follow.
    turing_race_admin_password
        The password of the administrator of the turing race.
    sleep
        The amount of time to wait between consecutive reads of the turing state.
    output_directory
        The path of the output directory
    compute_current_time
        A function that computes the current time given the current time counter
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

    # Constants associated to the browsers we will open
    UNICA_LIVE = 0  # noqa: N806
    UNICA_COMPARISON = 1  # noqa: N806
    SQUADRE_LIVE = 2  # noqa: N806
    PROBLEMI_LIVE = 3  # noqa: N806
    STATO_LIVE = 4  # noqa: N806
    browsers_name = [
        ("unica", "live"), ("unica", "comparison"), ("squadre", "live"), ("problemi", "live"), ("stato", "live")]

    # Constants associated to the table we will create
    POSITION_COLUMN = 0  # noqa: N806
    TEAM_ID_COLUMN = 1  # noqa: N806
    SCORE_COLUMN = 3  # noqa: N806

    # Constants associated to the output directories
    OUTPUT_LIVE = 0  # noqa: N806
    OUTPUT_COMPARISON = 1  # noqa: N806

    # Create subdirectories in the output directory, if they do not exist yet
    datetime_files_directory = output_directory / "datetime_files"
    live_turing_json_files_directory = output_directory / "live_turing_json_files"
    html_files_directory = [output_directory / "html_files", output_directory / "html_files_comparison"]
    table_files_directory = [output_directory / "table_files", output_directory / "table_files_comparison"]
    for directory in (
        datetime_files_directory, live_turing_json_files_directory, *html_files_directory, *table_files_directory
    ):
        directory.mkdir(parents=True, exist_ok=True)
    for INSTANCE in (UNICA_LIVE, SQUADRE_LIVE, PROBLEMI_LIVE, STATO_LIVE):  # noqa: N806
        (html_files_directory[OUTPUT_LIVE] / browsers_name[INSTANCE][0]).mkdir(parents=True, exist_ok=True)
    for INSTANCE in (UNICA_COMPARISON, ):  # noqa: N806
        (html_files_directory[OUTPUT_COMPARISON] / browsers_name[INSTANCE][0]).mkdir(parents=True, exist_ok=True)

    # Read the current time counter if available, otherwise set it to zero
    time_counter = 0
    time_counter_file = output_directory / "time_counter.txt"
    if time_counter_file.exists():
        time_counter = int(time_counter_file.read_text())
        time_counter += 1

    # Open two browsers to access the classification with querystring ?ended=False and ?ended=True
    browsers = [TuringClassificationSelenium(turing_url, turing_race.pk, sleep // 2) for _ in range(5)]
    for browser in browsers:
        browser.login(turing_race.admin.username, turing_race_admin_password)
    # Connect the live browsers to the live instance with ?ended=False
    for INSTANCE in (UNICA_LIVE, SQUADRE_LIVE, PROBLEMI_LIVE, STATO_LIVE):  # noqa: N806
        browsers[INSTANCE].go_to_classification_page(
            browsers_name[INSTANCE][0], {"ended": "false", "computation_rate": str(sleep // 4)})

    # Save CSS files for HTML export
    if time_counter == 0:
        browsers[UNICA_LIVE].lock()
        css_files, font_files = browsers[UNICA_LIVE].get_auxiliary_files()
        for (auxiliary_files, write_content) in (
            (css_files, lambda path, content: path.write_text(content)),
            (font_files, lambda path, content: path.write_bytes(content))
        ):
            for (filename, content) in auxiliary_files.items():
                write_content(  # type: ignore[no-untyped-call]
                    html_files_directory[OUTPUT_LIVE] / browsers_name[UNICA_LIVE][0] / filename, content
                )
                for (BROWSER_INSTANCE, OUTPUT_INSTANCE) in zip(  # noqa: N806
                    (UNICA_COMPARISON, SQUADRE_LIVE, PROBLEMI_LIVE, STATO_LIVE),
                    (OUTPUT_COMPARISON, OUTPUT_LIVE, OUTPUT_LIVE, OUTPUT_LIVE)
                ):
                    shutil.copy(
                        html_files_directory[OUTPUT_LIVE] / browsers_name[UNICA_LIVE][0] / filename,
                        html_files_directory[OUTPUT_INSTANCE] / browsers_name[BROWSER_INSTANCE][0] / filename)
        browsers[UNICA_LIVE].unlock()

    # Continuously read the turing state
    previous_positions = None
    previous_scores = None
    while True:
        print(f"{time_counter=}")
        # Compute the current time, up to the microsecond
        current_time = compute_current_time(time_counter)
        actual_time = datetime.datetime.now(current_time.tzinfo)
        inizio = turing_race.inizio.astimezone(current_time.tzinfo)
        timestamp = (current_time - inizio).total_seconds()
        # Precision to the second is more then enough for our goals: strip the microseconds,
        # and recompute the dates
        timestamp = int(timestamp)
        current_time = inizio + datetime.timedelta(seconds=timestamp)
        # Write out current time
        (datetime_files_directory / f"{time_counter}.datetime").write_text("""Computed: {current_time}
Actual: {actual_time}""")
        print(f"\tcomputed time is {current_time}")
        print(f"\tactual time is {actual_time}")
        print(f"\telapsed number of seconds {timestamp}")
        # Backup the turing dictionary associated to the race at the time represented by the current counter
        with open(live_turing_json_files_directory / f"{time_counter}.json", "w") as turing_json_file:
            turing_json_file.write(json.dumps(turing_race.to_dict(), indent=4))
        shutil.copy(
            live_turing_json_files_directory / f"{time_counter}.json",
            live_turing_json_files_directory / "latest.json")
        # Download browser content
        html: list[str] = [None for _ in browsers]  # type: ignore[misc]
        table: list[prettytable.PrettyTable] = [None for _ in browsers]  # type: ignore[misc]
        for (INSTANCE, browser) in enumerate(browsers):  # noqa: N806
            print(f"\tupdating {browsers_name[INSTANCE][0]} {browsers_name[INSTANCE][1]} browser")
            if browsers_name[INSTANCE][1] == "live":
                # Freeze the browser at the current time
                browser.freeze_time(current_time)
            else:
                # Time does not get updated in the comparison browser, and hence go to the updated classification page
                browser.go_to_classification_page("unica", {
                    "ended": "true", "computation_rate": "1", "race_time": str(timestamp)})
            # Save the content of the browser
            browser.lock()
            html[INSTANCE] = browser.get_cleaned_html_source()
            if INSTANCE in (UNICA_LIVE, UNICA_COMPARISON):
                table[INSTANCE] = browser.get_table()
            browser.unlock()
            # Do not bother unfreezing time in the live browser, since it would immediately be frozen again
            # at the next iteration
        # Write out the html files
        for (BROWSER_INSTANCE, _) in enumerate(browsers):  # noqa: N806
            if browsers_name[BROWSER_INSTANCE][1] == "live":
                OUTPUT_INSTANCE = OUTPUT_LIVE  # noqa: N806
            else:
                OUTPUT_INSTANCE = OUTPUT_COMPARISON  # noqa: N806
            assert html[BROWSER_INSTANCE] is not None
            (html_files_directory[OUTPUT_INSTANCE] / browsers_name[BROWSER_INSTANCE][0]
                / f"{time_counter}.html").write_text(
                    html[BROWSER_INSTANCE])
            # Add livejs script to the latest page so that it refreshes automatically
            # when uploaded to an HTTP server.
            # Note: livejs will not work when opening the file locally, since the file:// is not supported:
            # to try it you need to have a real server and access it through http:// or https://
            # As a workaround, you can start a local HTTP server by running
            #   python3 -m http.server
            # in the local directory.
            (html_files_directory[OUTPUT_INSTANCE] / browsers_name[BROWSER_INSTANCE][0] / "latest.html").write_text(
                (html_files_directory[OUTPUT_INSTANCE] / browsers_name[BROWSER_INSTANCE][0]
                    / f"{time_counter}.html").read_text().replace(
                        "</head>", '<script src="https://livejs.com/live.js"></script></head>'))
            with open(
                html_files_directory[OUTPUT_INSTANCE] / browsers_name[BROWSER_INSTANCE][0] / "watch.txt", "a"
            ) as text_file:
                text_file.write(f"updated at time counter {time_counter} ({current_time})\n")
        # Determine if the live table and the comparison one are the same or not
        assert table[UNICA_LIVE] is not None
        warn_table = (table[UNICA_LIVE].get_string() != table[UNICA_COMPARISON].get_string())
        # Compute team positions/scores, as a dictionary from the team ID to the team position/score
        positions = {r[TEAM_ID_COLUMN]: r[POSITION_COLUMN] for r in table[UNICA_LIVE].rows[1:]}
        scores = {r[TEAM_ID_COLUMN]: r[SCORE_COLUMN] for r in table[UNICA_LIVE].rows[1:]}
        # Compute the difference between the scores at this time and at the previous time
        print_fields: list[list[str]] = [None, None]  # type: ignore[list-item]
        print_fields[UNICA_LIVE] = ["Position", "Team ID", "Team name", "Score"]
        print_fields[UNICA_COMPARISON] = ["Position", "Team ID", "Team name", "Score"]  # do not assign the LIVE one!
        if previous_positions is not None:
            position_update = [
                previous_positions[r[TEAM_ID_COLUMN]] - positions[r[TEAM_ID_COLUMN]]
                for r in table[UNICA_LIVE].rows[1:]]
            table[UNICA_LIVE].add_column("Position update", [""] + [u if u != 0 else "" for u in position_update])
            print_fields[UNICA_LIVE].append("Position update")
        if previous_scores is not None:
            score_update = [
                scores[r[TEAM_ID_COLUMN]] - previous_scores[r[TEAM_ID_COLUMN]] for r in table[UNICA_LIVE].rows[1:]]
            table[UNICA_LIVE].add_column("Score update", [""] + [u if u != 0 else "" for u in score_update])
            print_fields[UNICA_LIVE].append("Score update")
        # Write out the table files
        for BROWSER_INSTANCE in (UNICA_LIVE, UNICA_COMPARISON):  # noqa: N806
            OUTPUT_INSTANCE = BROWSER_INSTANCE  # noqa: N806
            assert table[BROWSER_INSTANCE] is not None
            (table_files_directory[OUTPUT_INSTANCE] / f"{time_counter}.csv").write_text(
                table[BROWSER_INSTANCE].get_formatted_string(out_format="csv"))
            (table_files_directory[OUTPUT_INSTANCE] / f"{time_counter}.html").write_text(
                "<html><head></head><body>"
                + table[BROWSER_INSTANCE].get_formatted_string(
                    fields=print_fields[BROWSER_INSTANCE], out_format="html", format=True)
                + "</body>")
            shutil.copy(
                table_files_directory[OUTPUT_INSTANCE] / f"{time_counter}.csv",
                table_files_directory[OUTPUT_INSTANCE] / "latest.csv")
            (table_files_directory[OUTPUT_INSTANCE] / "latest.html").write_text(
                (table_files_directory[OUTPUT_INSTANCE] / f"{time_counter}.html").read_text().replace(
                    "</head>", '<script src="https://livejs.com/live.js"></script></head>'))
        # Write out the time counter
        time_counter_file.write_text(str(time_counter))
        # Print out table
        print("\t" + table[UNICA_LIVE].get_string(fields=print_fields[UNICA_LIVE]).replace("\n", "\n\t"))
        if warn_table:
            print("\tWARNING: live and comparison tables are different:")
            print("\t\tlive table is")
            print(table[UNICA_LIVE].get_string())
            print("\t\tcomparison table is")
            print(table[UNICA_COMPARISON].get_string())
            print(
                "\t\tThis warning typically happens when a team answers a question a fraction (less than 1) "
                "of a second after the live browser has taken the snapshot of the html page: the live browser "
                "will not have the answer, but the comparison browser will have it. If this is the case, "
                "the warning will disappear in the next time iteration. If not, you may also want to compare "
                f"html_files/{time_counter}.html and html_files_comparison/{time_counter}.html in the output "
                "directory."
            )
        # Break out of the loop if the race has ended
        if termination_condition(time_counter):
            break
        # Upate the time counter
        time_counter += 1
        # Replace previous positions/scores
        previous_positions = positions
        previous_scores = scores
        # Wait before reading again the updated version of the turing state
        actual_time_end = datetime.datetime.now(current_time.tzinfo)
        wait_time = sleep - (actual_time_end - actual_time).total_seconds()
        if wait_time > 0:
            print(f"\twaiting {wait_time} seconds for next time iteration")
            time.sleep(wait_time)


if __name__ == "__main__":  # pragma: no cover
    # This import requires turing to be available, and thus cannot be moved to the common section.
    # We skip coverage testing of this part because we cannot cover this in unit tests, since they
    # cannot interact with turing. Testing this entrypoint is delayed to integration testing.
    import django
    django.setup()

    import django.conf
    import engine.models

    TIME_ZONE_SETTING = getattr(django.conf.settings, "TIME_ZONE", None)
    assert TIME_ZONE_SETTING is not None
    assert isinstance(TIME_ZONE_SETTING, str)
    TIME_ZONE_SETTING = pytz.timezone(TIME_ZONE_SETTING)

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-u", "--turing-url", type=str, required=True, help="The URL of the live turing instance")
    parser.add_argument("-t", "--turing-race-id", type=int, required=True, help="ID of the turing race to follow")
    parser.add_argument(
        "-p", "--turing-race-admin-password", type=str, required=True,
        help="The password of the administrator of the turing race")
    parser.add_argument(
        "-s", "--sleep", type=float, required=False, default=1.0,
        help="The amount of time to wait between consecutive turing race exports")
    parser.add_argument("-o", "--output-directory", type=str, required=True, help="Path of the output directory")
    args = parser.parse_args()

    live_turing_to_html(
        args.turing_url, engine.models, args.turing_race_id, args.turing_race_admin_password,
        args.sleep, pathlib.Path(args.output_directory), lambda time_counter: datetime.datetime.now(TIME_ZONE_SETTING),
        lambda time_counter: False)
