# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test that the final race scores are equal to the expected ones."""

import datetime
import json
import os
import pathlib
import typing

import engine.models
import pytest
import pytest_django.live_server_helper
import selenium.webdriver.common.by

import mathrace_interaction
import mathrace_interaction.filter
import mathrace_interaction.network
import mathrace_interaction.typing


def test_journal_scores(
    journal: typing.TextIO, journal_name: str, data_dir: pathlib.Path,
    live_server: pytest_django.live_server_helper.LiveServer,
    read_score_file: mathrace_interaction.typing.ReadScoreFileFixtureType
) -> None:
    """Test that the final race scores are equal to the expected ones (journal files)."""
    # Import the journal into turing via journal_reader
    journal_year, _ = journal_name.split(os.sep, maxsplit=1)
    journal_date = datetime.datetime(int(journal_year), 1, 1, tzinfo=datetime.UTC)
    with mathrace_interaction.journal_reader(journal) as journal_stream:
        turing_dict = journal_stream.read(journal_name, journal_date)
    mathrace_interaction.filter.strip_mathrace_only_attributes_from_imported_turing(turing_dict)
    mathrace_interaction.filter.strip_trailing_zero_bonus_superbonus_from_imported_turing(turing_dict)
    gara = engine.models.Gara.create_from_dict(turing_dict)
    # Open a browser and get the computed scores
    browser = mathrace_interaction.network.TuringClassificationSelenium(live_server.url, gara.pk, 10)
    browser.go_to_classification_page("squadre", {})
    browser.lock()
    actual = browser.get_teams_score()
    # Compare the computed scores to the expected ones
    expected = read_score_file(data_dir, journal_name)
    assert actual == expected
    browser.quit()


def test_json_scores(
    json_name: str, data_dir: pathlib.Path, live_server: pytest_django.live_server_helper.LiveServer,
    read_score_file: mathrace_interaction.typing.ReadScoreFileFixtureType
) -> None:
    """Test that the final race scores are equal to the expected ones (json files)."""
    # Import the json file into turing
    with open(data_dir / json_name) as json_stream:
        turing_dict = json.load(json_stream)
    gara = engine.models.Gara.create_from_dict(turing_dict)
    # Open a browser and get the computed scores
    browser = mathrace_interaction.network.TuringClassificationSelenium(live_server.url, gara.pk, 10)
    browser.go_to_classification_page("squadre", {})
    browser.lock()
    actual = browser.get_teams_score()
    # Compare the computed scores to the expected ones
    expected = read_score_file(data_dir, json_name)
    assert actual == expected
    browser.quit()


@pytest.mark.parametrize("order_attribute_in_json,order_attribute_in_score,ended", [
    # These cases give the correct classification
    ("correct", "correct", True),
    ("correct", "correct", False),
    ("wrong", "correct", True), # purposely using the other score file
    # This case gives the wrong classification
    ("wrong", "wrong", False)
])
def test_smartematica_2024_short_wrong_order_bug(  # type: ignore[no-any-unimported]
    data_dir: pathlib.Path, live_server: pytest_django.live_server_helper.LiveServer,
    read_score_file: mathrace_interaction.typing.ReadScoreFileFixtureType, admin_user: engine.models.User,
    order_attribute_in_json: str, order_attribute_in_score: str, ended: bool
) -> None:
    """
    Test to show that storing event in an incorrect order can cause wrong classification results.

    The file bugs/smartematica_2024_short_wrong_order.json contains a shorter version of the Smartematica 2024.
    The file contains the first 01h:01min:28sec of 01h:40min:00sec race.
    The events in the file are NOT sorted chronologically:
    - race starts at 14:15:10
    - a first block of 325 events from 14:23:05 to 15:16:38 (when the race was interrupted), sorted chronologically.
      In particular, 322 events out of 325 in the first block are of type "Consegna".
    - a second block of 63 events from 14:17:11 to 14:24:53, sorted chronologically.
      Hence, the second block contains some events that should have been stored before the first block.
      In particular, 46 events out of 63 in the second block are of type "Consegna".

    The results of the classification are not consistent during (?ended=false) and after (?ended=true) the race.

    === Backtrace of client.js with ?ended=false ===
    0) The events are stored in the database as follows
       database = [
            # from the first block
            Time: 14:23:05, 14:23:20, ..., 15:16:00, 15:16:38,  # 322 events
            ID:          1,        2, ...,      321,      322,
            # and then, from the second block
            14:17:30, 14:17:44, ..., 14:24:42, 14:24:53   # 46 events
            ID:  323,      324, ...,      368,      369
       ]
    1) When calling ClassificaClient.init(), the database is queried via
            $.getJSON(this.url)
       where this.url queries StatusView.get() in views.py, which in turn queries Gara.get_consegne(last=None)
       in models.py. The output of Gara.get_consegne contains all events, with correct ordering enforced
       by qs.order_by('orario'). Afterwards constructor of Gara gets triggered on the output data.
       In the constructor of Gara, the method add_consegna is called for every consegna event in the race.
       Therefore, upon constructing Gara the futuro list contains 322 + 46 = 368 events, which is correct.
       The stored events are
       futuro = [ ... 322 + 46 events, correctly sorted chronologically ...]
              = [ID: 323, 324, ..., 1, ..., 321, 322]
       passato = []
       In particular, this means that Gara.last_consegna_id is the ID of the last element in futuro,
       which is equal to 322 (i.e., last element of the first block).
    2) Immediately after construction of Gara, ClassificaClient.init() sets the progress attribute of the Gara object
       to null. Inside the setter of Gara.progress, the value of Gara.time is updated to the current time returned by
       the server. Inside the setter of Gara.time, there is a call to Gara.update_events, which is responsible
       of moving events from the futuro array to the passato one. In Gara.update_events, we are in the if branch,
       because some events that the Gara constructor memorized in the futuro array have actually already happened,
       and thus must be moved to the passato array.
       At the end of this step, all events are moved to the passato array, hence
       futuro = []
       passato = [ ... 322 + 46 events, correctly sorted chronologically ...]
               = [ID: 323, 324, ..., 1, ..., 321, 322]
       At this point, the classification is displayed correctly.
    3) Wait a few seconds, until setInterval(client.update(), refresh_rate) in class_template.html is triggered
       for the first time, after which ClassificaClient.update() is called.
       As part of the update, the database is queried via
            $.getJSON(this.url, {last_consegna_id: 369})
       where this.url queries StatusView.get() in views.py, which in turn queries Gara.get_consegne(last=322)
       in models.py. In the implementation in Gara.get_consegne, a non-default value of last limits the query
       to IDs above the last one. If the database was correctly sorted, this would mean processing only the future
       events. In this case, in which the database is not correctly sorted, the answer is
       data = [ ... 46 events with ID > 322, i.e. the 46 events from the second block ...]
       which are then stored in futuro.
       At the end of this step, the stored events are
       futuro = [ ... copies of the 46 events in the second block ...]
              = [ID: 323, 324, ...., 369]
       passato = [ ... 322 + 46 events, correctly sorted chronologically ... ]
       and last Gara.last_consegna_id = 369.
    4) At the end of the client.update() call, Gara.progress is set. This calls Gara.update_events which,
       in turn, moves the 46 extra copies from passato to futuro. Now
       futuro = []
       passato = [ ... 322 + 46 + 46 events, correctly sorted chronologically ...]
               = [ID: 323, 324, ..., 1, ..., 321, 322, and then again!, 323, 324, ..., 369]
       At this point, the classification is incorrect because of the extra 46 events, because:
       - if the consegna was correct, the extra event is effectively ignore;
       - if the consegna was incorrect, due to 0003_penalize_wrong_answer_after_correct_answer.patch
         we assign them -10 points. Hence, due to the extra copies every team who has submitted
         an incorrect answer in the first block gets penalized twice.
    5) Wait a few seconds, for the next query to client.update(). This time, it calls Gara.get_consegne(last=369).
       There are no new events after ID 369, and the classification remains constant (wrong) forever.

    === Backtrace of client.js with ?ended=true ===
    The culprit in the case of ?ended=false is the call to client.update() at step 3).
    In the page with ?ended=true there is no call to client.update(), hence the backtrace will only carry out
    steps 0), 1) and 2), resulting in the correct classification.
    Even upon moving the replay controller, step 3) is never queried (i.e., the database is never interrogated again),
    and already existing and correctly sorted events are just moved between the passato and futuro arrays.
    """
    # Import the json files into turing
    with open(data_dir / f"bugs/smartematica_2024_short_{order_attribute_in_json}_order.json") as json_stream:
        turing_dict = json.load(json_stream)
    gara = engine.models.Gara.create_from_dict(turing_dict)
    gara.admin = admin_user
    gara.save()
    # Open a browser at time 01:30:00, i.e. after the final answer submission has taken place.
    # Set a large value for computation_rate so that we can process the scores as they are first shown
    # before the first recomputation takes place.
    browser = mathrace_interaction.network.TuringClassificationSelenium(live_server.url, gara.pk, 10)
    browser.login(admin_user.username, "pw" + admin_user.username)
    browser.go_to_classification_page(
        "squadre", {"ended": str(ended), "race_time": "01:30:00", "computation_rate": "00:00:05"})
    # Ensure that scores before the first recomputation are correct
    browser.lock()
    assert browser.get_teams_score() == read_score_file(data_dir, "bugs/smartematica_2024_short_correct_order.json")
    browser.unlock()
    # Wait for the for the first recomputation to take place
    if ended:
        browser.find_element(selenium.webdriver.common.by.By.ID, "elapsedTimeText").send_keys("01:30:05")
        browser._browser.execute_script("$('#elapsedTimeText').blur()")  # type: ignore[no-untyped-call]
    browser._wait_for_classification_timer("01:30:05")
    # Ensure that scores after the first recomputation are affected by the bug
    browser.lock()
    assert browser.get_teams_score() == read_score_file(
        data_dir, f"bugs/smartematica_2024_short_{order_attribute_in_score}_order.json")
    browser.unlock()
    browser.quit()
