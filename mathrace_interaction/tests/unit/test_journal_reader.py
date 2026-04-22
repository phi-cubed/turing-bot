# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.journal_reader."""

import datetime
import io
import json
import tempfile
import typing

import pytest

import mathrace_interaction
import mathrace_interaction.filter
import mathrace_interaction.typing


def test_journal_reader(
    journal: io.StringIO, race_name: str, race_date: datetime.datetime,
    turing_dict: mathrace_interaction.typing.TuringDict
) -> None:
    """Test that journal_reader correctly imports sample journals."""
    with mathrace_interaction.journal_reader(journal) as journal_stream:
        imported_dict = journal_stream.read(race_name, race_date)
    mathrace_interaction.filter.strip_mathrace_only_attributes_from_imported_turing(imported_dict)
    assert imported_dict == turing_dict


@pytest.mark.parametrize(
    "input_file_option,race_name_option,race_date_option,output_file_option", [
        ("-i", "-n", "-d", "-o"),
        ("--input-file", "--race-name", "--race-date", "--output-file")
    ]
)
def test_journal_reader_entrypoint(
    journal: io.StringIO, run_entrypoint: mathrace_interaction.typing.RunEntrypointFixtureType,
    race_name: str, race_date: datetime.datetime, turing_dict: mathrace_interaction.typing.TuringDict,
    input_file_option: str, race_name_option: str, race_date_option: str, output_file_option: str
) -> None:
    """Test running journal_reader as entrypoint."""
    with tempfile.NamedTemporaryFile() as journal_file, tempfile.NamedTemporaryFile() as json_file:
        with open(journal_file.name, "w") as journal_stream:
            journal_stream.write(journal.read())
        stdout, stderr = run_entrypoint(
            "mathrace_interaction.journal_reader", [
                input_file_option, journal_file.name, race_name_option, race_name,
                race_date_option, race_date.isoformat(), output_file_option, json_file.name
            ]
        )
        assert stdout == ""
        assert stderr == ""
        with open(json_file.name) as json_stream:
            imported_dict = json.load(json_stream)
        assert imported_dict == turing_dict
        # The same journal stream is shared on the parametrization on command line options: since the stream
        # was consumed reset it to the beginning before passing to the next parametrized item
        journal.seek(0)


def test_journal_reader_wrong_first_line(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the file initalization line is missing."""
    wrong_journal = io.StringIO("""\
0 002 inizio gara
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Invalid first line 0 002 inizio gara")


def test_journal_reader_missing_race_definition(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the race definition is missing."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
0 002 inizio gara
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        'Invalid line 0 002 inizio gara in race definition: it does not start with "--- "')


@pytest.mark.parametrize("separator", ["", "-- "])
def test_journal_reader_different_separator_in_race_definition(separator: str, race_date: datetime.datetime) -> None:
    """Test that journal_reader accept either the empty string or -- as separator in the race definition line."""
    journal_with_separator = io.StringIO(f"""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 {separator}squadre: 10 quesiti: 7
0 002 inizio gara
600 029 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_separator) as journal_stream:
        imported_dict = journal_stream.read("journal_with_separator", race_date)
    assert len(imported_dict["squadre"]) == 10
    assert len(imported_dict["soluzioni"]) == 7


def test_journal_reader_wrong_race_definition_code(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the race definition is containing a wrong code."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 993 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        'Invalid line --- 993 10 7 70 10 6 4 1 1 10 2 in race definition: it does not start with "--- 003"')


def test_journal_reader_wrong_race_definition_parts(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the race definition contains a wrong number of parts."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 00000 -- squadre: 10 quesiti: 7
0 002 inizio gara
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Invalid line --- 003 10 7 70 10 6 4 1 1 10 2 00000 in race definition: it does not contain "
        "the expected number of parts")


def test_journal_reader_wrong_race_definition_bonus_cardinality(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the race definition contains a wrong bonus cardinality."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 99910 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Invalid line --- 003 10 7 70 99910 6 4 1 1 10 2 in race definition: the expected bonus cardinality is 10, "
        "but the race definition contains 99910.")


def test_journal_reader_wrong_race_definition_supbonus_cardinality(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the race definition contains a wrong superbonus cardinality."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 9996 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Invalid line --- 003 10 7 70 10 9996 4 1 1 10 2 in race definition: the expected superbonus cardinality "
        "is 6, but the race definition contains 9996.")


def test_journal_reader_wrong_race_definition_alternative_k_blocco(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the race definition contains a wrong alternative k parameter."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 9991 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Invalid line --- 003 10 7 70 10 6 4 9991 1 10 2 in race definition: the expected alternative k is 1, "
        "but the race definition contains 9991.")


def test_journal_reader_wrong_race_definition_race_type(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the race definition contains a wrong race type."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 9991 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Invalid line --- 003 10 7 70 10 6 4 1 9991 10 2 in race definition: the expected race type is 1, "
        "but the race definition contains 9991.")


def test_journal_reader_race_event_with_inconsistent_deadline_score_increase(race_date: datetime.datetime) -> None:
    """Test that journal_reader sets the deadline for score increase as zero when the last int is wrong."""
    journal_with_wrong_deadline_score_increase = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 999 -- squadre: 10 quesiti: 7
0 002 inizio gara
600 029 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_wrong_deadline_score_increase) as journal_stream:
        dict_with_wrong_deadline_score_increase = journal_stream.read(
            "journal_with_wrong_deadline_score_increase", race_date)
    assert dict_with_wrong_deadline_score_increase["durata"] == 10
    assert dict_with_wrong_deadline_score_increase["durata_blocco"] == 0


@pytest.mark.parametrize(
    "race_start_event,extra_text",
    [("0 002 inizio gara", ""), ("00:00:00.000 200 inizio gara", " 0000")]
)
def test_journal_reader_wrong_question_definition(
    race_start_event: str, extra_text: str, race_date: datetime.datetime,
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """
    Test that journal_reader raises an error when a question definition line does not contain the expect word.

    The parametrization switches between version r5539 and version r25013.
    """
    wrong_journal = io.StringIO(f"""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
--- 004 1 20{extra_text}
{race_start_event}
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        f"Invalid line --- 004 1 20{extra_text} in question definition: it does not contain the word quesito")


@pytest.mark.parametrize(
    "RACE_START,RACE_SUSPENDED,RACE_RESUMED,RACE_END,generate_timestamp", [
        ("002", "027", "028", "029", lambda minute: str(60 * minute)),
        ("200", "201", "202", "210", lambda minute: f"00:0{minute}:00" if minute < 10 else f"00:{minute}:00")
    ]
)
def test_journal_reader_race_suspension_ignored(
    RACE_START: str, RACE_SUSPENDED: str, RACE_RESUMED: str, RACE_END: str,  # noqa: N803
    generate_timestamp: typing.Callable[[int], str], race_date: datetime.datetime
) -> None:
    """Test that race suspension events are ignored by journal_reader."""
    journal_without_suspension = io.StringIO(f"""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
{generate_timestamp(0)} {RACE_START} inizio gara
{generate_timestamp(10)} {RACE_END} termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_without_suspension) as journal_stream:
        dict_without_suspension = journal_stream.read("race_suspension_test", race_date)

    journal_with_suspension = io.StringIO(f"""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
{generate_timestamp(0)} {RACE_START} inizio gara
{generate_timestamp(5)} {RACE_SUSPENDED} gara sospesa
{generate_timestamp(6)} {RACE_RESUMED} gara ripresa
{generate_timestamp(10)} {RACE_END} termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_suspension) as journal_stream:
        dict_with_suspension = journal_stream.read("race_suspension_test", race_date)

    assert dict_without_suspension == dict_with_suspension


@pytest.mark.parametrize(
    "RACE_START,TIMER_UPDATE,MANUAL_BONUS,RACE_END,generate_timestamp", [
        ("002", "022", "091", "029", lambda minute: str(60 * minute)),
        ("200", "101", "130", "210", lambda minute: f"00:0{minute}:00" if minute < 10 else f"00:{minute}:00")
    ]
)
def test_journal_reader_race_event_manual_bonus(
    RACE_START: str, TIMER_UPDATE: str, MANUAL_BONUS: str, RACE_END: str,  # noqa: N803
    generate_timestamp: typing.Callable[[int], str], race_date: datetime.datetime
) -> None:
    """Test that manual bonus race events are logged by journal_reader."""
    journal_with_manual_bonus = io.StringIO(f"""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
{generate_timestamp(0)} {RACE_START} inizio gara
{generate_timestamp(1)} {TIMER_UPDATE} aggiorna punteggio esercizi, orologio: 1
{generate_timestamp(5)} {MANUAL_BONUS} 2 10 squadra 2 bonus 10 motivazione: errore inserimento dati
{generate_timestamp(10)} {RACE_END} termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_manual_bonus) as journal_stream:
        dict_with_manual_bonus = journal_stream.read("journal_with_manual_bonus", race_date)
    assert len(dict_with_manual_bonus["eventi"]) == 1
    assert dict_with_manual_bonus["eventi"][0]["orario"] == (race_date + datetime.timedelta(minutes=5)).isoformat()


@pytest.mark.parametrize(
    "generate_timestamp", [
        lambda minute: str(60 * minute),
        lambda minute: f"00:0{minute}:00" if minute < 10 else f"00:{minute}:00"
    ]
)
def test_journal_reader_race_other_timer_ignored(
    generate_timestamp: typing.Callable[[int], str], race_date: datetime.datetime
) -> None:
    """Test that race events associated to the second timer are ignored by journal_reader."""
    journal_without_other_timer = io.StringIO(f"""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
{generate_timestamp(0)} 200 inizio gara
{generate_timestamp(1)} 101 aggiorna punteggio esercizi, orologio: 1
{generate_timestamp(10)} 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_without_other_timer) as journal_stream:
        dict_without_other_timer = journal_stream.read("race_other_timer_test", race_date)

    journal_with_other_timer = io.StringIO(f"""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
{generate_timestamp(0)} 200 inizio gara
{generate_timestamp(1)} 101 aggiorna punteggio esercizi, orologio: 1
{generate_timestamp(5)} 901 avanzamento estrapolato orologio: 5
{generate_timestamp(10)} 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_other_timer) as journal_stream:
        dict_with_other_timer = journal_stream.read("race_other_timer_test", race_date)

    assert dict_without_other_timer == dict_with_other_timer


def test_journal_reader_wrong_race_event_code(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when an unhandled event code is encountered."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
300 123 wrong race event code
600 029 termine gara
--- 999 fine simulatore
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Invalid line 300 123 wrong race event code in race events: unhandled event type 123")


def test_journal_reader_wrong_race_start_text(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the race start event contains extra text."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara testo aggiuntivo
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Invalid final line 0 002 inizio gara testo aggiuntivo")


def test_journal_reader_wrong_timer_update_text(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the timer update event contains invalid text."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
60 022 NON aggiorna punteggio esercizi, orologio: 1
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Invalid event content NON aggiorna punteggio esercizi, orologio: 1 in timer update event")


def test_journal_reader_race_event_with_timer_offset(race_date: datetime.datetime) -> None:
    """Test that race events timestamps are offset by timer event."""
    journal_with_timer_offset = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
45 022 aggiorna punteggio esercizi, orologio: 1
80 011 2 3 1 squadra 2, quesito 3: giusto
600 029 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_timer_offset) as journal_stream:
        dict_with_timer_offset = journal_stream.read("journal_with_timer_offset", race_date)
    assert dict_with_timer_offset["mathrace_only"]["timestamp_offset"] == "15"
    assert len(dict_with_timer_offset["eventi"]) == 1
    assert dict_with_timer_offset["eventi"][0]["orario"] == (race_date + datetime.timedelta(seconds=95)).isoformat()


def test_journal_reader_jolly_selection_before_timer_offset(race_date: datetime.datetime) -> None:
    """
    Test that it is possible to select the jolly before timer offset is computed.

    A jolly selected before timer offset computation will have the timestamp neglecting the offset.
    """
    journal_with_timer_offset = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
30 010 1 2 squadra 1 sceglie 2 come jolly
45 022 aggiorna punteggio esercizi, orologio: 1
80 010 2 3 squadra 2 sceglie 3 come jolly
600 029 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_timer_offset) as journal_stream:
        dict_with_timer_offset = journal_stream.read("journal_with_timer_offset", race_date)
    assert dict_with_timer_offset["mathrace_only"]["timestamp_offset"] == "15"
    assert len(dict_with_timer_offset["eventi"]) == 2
    assert dict_with_timer_offset["eventi"][0]["orario"] == (race_date + datetime.timedelta(seconds=30)).isoformat()
    assert dict_with_timer_offset["eventi"][1]["orario"] == (race_date + datetime.timedelta(seconds=95)).isoformat()


def test_journal_reader_answer_submission_before_timer_offset(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that it is not allowed to submit an answer before timer offset is computed."""
    journal_with_timer_offset = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
30 011 2 3 1 squadra 2, quesito 3: giusto
45 022 aggiorna punteggio esercizi, orologio: 1
600 029 termine gara
--- 999 fine simulatore
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(journal_with_timer_offset).read(
            "journal_with_timer_offset", race_date),
        "Cannot convert 30 to date and time because of empty timestamp offset")


def test_journal_reader_live_race(race_date: datetime.datetime) -> None:
    """Test journal reader on a live race, i.e. a journal in which the race end event is missing."""
    live_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
60 022 aggiorna punteggio esercizi, orologio: 1
80 010 1 2 squadra 1 sceglie 2 come jolly
90 011 2 3 1 squadra 2, quesito 3: giusto
100 010 2 3 squadra 2 sceglie 3 come jolly
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(live_journal) as journal_stream:
        dict_with_timer_offset = journal_stream.read("live_journal", race_date)
    assert len(dict_with_timer_offset["eventi"]) == 3
    assert dict_with_timer_offset["eventi"][0]["orario"] == (race_date + datetime.timedelta(seconds=80)).isoformat()
    assert dict_with_timer_offset["eventi"][1]["orario"] == (race_date + datetime.timedelta(seconds=90)).isoformat()
    assert dict_with_timer_offset["eventi"][2]["orario"] == (race_date + datetime.timedelta(seconds=100)).isoformat()


def test_journal_reader_multiple_race_events_at_same_time(race_date: datetime.datetime) -> None:
    """Test that the order of race events happening at the same time is preserved by shifting of a few milliseconds."""
    journal_with_events_at_same_time = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
60 022 aggiorna punteggio esercizi, orologio: 1
80 011 2 3 1 squadra 2, quesito 3: giusto
80 011 4 5 1 squadra 4, quesito 5: giusto
80 011 6 7 1 squadra 6, quesito 7: giusto
600 029 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_events_at_same_time) as journal_stream:
        dict_with_events_at_same_time = journal_stream.read("journal_with_events_at_same_time", race_date)
    assert len(dict_with_events_at_same_time["eventi"]) == 3
    assert dict_with_events_at_same_time["eventi"][0]["orario"] == (
        race_date + datetime.timedelta(seconds=80)).isoformat()
    assert dict_with_events_at_same_time["eventi"][0]["squadra_id"] == 2
    assert dict_with_events_at_same_time["eventi"][1]["orario"] == (
        race_date + datetime.timedelta(seconds=80, milliseconds=1)).isoformat()
    assert dict_with_events_at_same_time["eventi"][1]["squadra_id"] == 4
    assert dict_with_events_at_same_time["eventi"][2]["orario"] == (
        race_date + datetime.timedelta(seconds=80, milliseconds=2)).isoformat()
    assert dict_with_events_at_same_time["eventi"][2]["squadra_id"] == 6


def test_journal_reader_wrong_race_events_order(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when race events are incorrectly sorted."""
    journal_with_incorrectly_sorted_events = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
60 022 aggiorna punteggio esercizi, orologio: 1
82 011 4 5 1 squadra 4, quesito 5: giusto
81 011 2 3 1 squadra 2, quesito 3: giusto
600 029 termine gara
--- 999 fine simulatore
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(journal_with_incorrectly_sorted_events).read(
            "journal_with_incorrectly_sorted_events", race_date),
        "The file contains incorrectly sorted events: event at time 2000-01-01 00:01:22+00:00 "
        "happens before event at time 2000-01-01 00:01:21+00:00 (timestamp 81)")


def test_journal_reader_wrong_race_events_order_not_strict(race_date: datetime.datetime) -> None:
    """Test that journal_reader without strict mode allows to import incorrectly sorted events."""
    journal_with_incorrectly_sorted_events = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
60 022 aggiorna punteggio esercizi, orologio: 1
82 011 4 5 1 squadra 4, quesito 5: giusto
81 011 2 3 1 squadra 2, quesito 3: giusto
600 029 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_incorrectly_sorted_events) as journal_stream:
        journal_stream.strict_timestamp_race_events = False  # type: ignore[attr-defined]
        dict_with_incorrectly_sorted_events = journal_stream.read("journal_with_incorrectly_sorted_events", race_date)
    assert len(dict_with_incorrectly_sorted_events["eventi"]) == 2
    assert dict_with_incorrectly_sorted_events["eventi"][0]["orario"] == (
        race_date + datetime.timedelta(seconds=82)).isoformat()
    assert dict_with_incorrectly_sorted_events["eventi"][0]["squadra_id"] == 4
    assert dict_with_incorrectly_sorted_events["eventi"][1]["orario"] == (
        race_date + datetime.timedelta(seconds=81)).isoformat()
    assert dict_with_incorrectly_sorted_events["eventi"][1]["squadra_id"] == 2


def test_journal_reader_missing_protocol_numbers(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the version is r11184+ but a line is missing the protocol."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 200 inizio gara
60 101 aggiorna punteggio esercizi, orologio: 1
61 120 1 2 PROT:1 squadra 1 sceglie 2 come jolly
62 120 2 3 PROT_AND_ANOTHER_STRING:2 squadra 2 sceglie 3 come jolly
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Cannot determine protocol number from 2 3 PROT_AND_ANOTHER_STRING:2 squadra 2 sceglie 3 come jolly")


def test_journal_reader_race_definition_before_r17497_timestamps_after_20644(race_date: datetime.datetime) -> None:
    """Test the interplay between a race definition before r17497 with timestamps defined in r17505."""
    journal_with_timestamps = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
00:00:00.000 200 inizio gara
00:01:00.000 101 aggiorna punteggio esercizi, orologio: 1
00:01:03.000 120 1 2 PROT:1 squadra 1 sceglie 2 come jolly
00:10:00.000 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_timestamps) as journal_stream:
        imported_dict = journal_stream.read("journal_with_timestamps", race_date)
    assert len(imported_dict["squadre"]) == 10
    assert len(imported_dict["soluzioni"]) == 7
    assert len(imported_dict["eventi"]) == 1
    assert imported_dict["eventi"][0]["orario"] == (race_date + datetime.timedelta(seconds=63)).isoformat()


def test_journal_reader_wrong_alternative_race_definition_code(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the alternative race definition is containing a wrong code."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 992 10+0:70 7:20 4.1;1 10-2 -- squadre: 10 quesiti: 7
00:00:00.000 200 inizio gara
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Invalid line --- 992 10+0:70 7:20 4.1;1 10-2 in race definition: it does not start "
        'with "--- 003" or "--- 002"')


def test_journal_reader_wrong_alternative_race_definition_parts(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the alt. race definition contains a wrong number of parts."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 002 10+0:70 7:20 4.1;1 10-2 00000 -- squadre: 10 quesiti: 7
0 200 inizio gara
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Invalid line --- 002 10+0:70 7:20 4.1;1 10-2 00000 in alternative race definition: it does not contain "
        "the expected number of parts")


def test_journal_reader_alternative_race_definition_num_teams_entry_without_optional_arguments(
    race_date: datetime.datetime
) -> None:
    """Test a num_teams entry in the alternative race definition without any optional argument."""
    journal_with_num_teams = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 002 10 7:20 4.1;1 10-2 -- squadre: 10 quesiti: 7
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_num_teams) as journal_stream:
        imported_dict = journal_stream.read("journal_with_num_teams", race_date)
    assert len(imported_dict["squadre"]) == 10
    assert imported_dict["mathrace_only"]["num_teams"] == "10"
    assert imported_dict["mathrace_only"]["num_teams_alternative"] == "10"
    assert imported_dict["mathrace_only"]["num_teams_nonguests"] == "10"
    assert imported_dict["mathrace_only"]["num_teams_guests"] == "0"
    assert imported_dict["punteggio_iniziale_squadre"] is None


def test_journal_reader_alternative_race_definition_num_teams_entry_with_guests_optional_argument(
    race_date: datetime.datetime
) -> None:
    """Test a num_teams entry in the alternative race definition with the first optional argument."""
    journal_with_num_teams = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 002 10+2 7:20 4.1;1 10-2 -- squadre: 12 quesiti: 7
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_num_teams) as journal_stream:
        imported_dict = journal_stream.read("journal_with_num_teams", race_date)
    assert len(imported_dict["squadre"]) == 12
    assert imported_dict["mathrace_only"]["num_teams"] == "12"
    assert imported_dict["mathrace_only"]["num_teams_alternative"] == "10+2"
    assert imported_dict["mathrace_only"]["num_teams_nonguests"] == "10"
    assert imported_dict["mathrace_only"]["num_teams_guests"] == "2"
    assert imported_dict["punteggio_iniziale_squadre"] is None


def test_journal_reader_alternative_race_definition_num_teams_entry_with_initial_score_optional_argument(
    race_date: datetime.datetime
) -> None:
    """Test a num_teams entry in the alternative race definition with the second optional argument."""
    journal_with_num_teams = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 002 10:70 7:20 4.1;1 10-2 -- squadre: 10 quesiti: 7
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_num_teams) as journal_stream:
        imported_dict = journal_stream.read("journal_with_num_teams", race_date)
    assert len(imported_dict["squadre"]) == 10
    assert imported_dict["mathrace_only"]["num_teams"] == "10"
    assert imported_dict["mathrace_only"]["num_teams_alternative"] == "10:70"
    assert imported_dict["mathrace_only"]["num_teams_nonguests"] == "10"
    assert imported_dict["mathrace_only"]["num_teams_guests"] == "0"
    assert imported_dict["punteggio_iniziale_squadre"] == 70


def test_journal_reader_alternative_race_definition_num_teams_entry_with_both_optional_arguments(
    race_date: datetime.datetime
) -> None:
    """Test a num_teams entry in the alternative race definition with both optional arguments."""
    journal_with_num_teams = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 002 10+2:70 7:20 4.1;1 10-2 -- squadre: 12 quesiti: 7
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_num_teams) as journal_stream:
        imported_dict = journal_stream.read("journal_with_num_teams", race_date)
    assert len(imported_dict["squadre"]) == 12
    assert imported_dict["mathrace_only"]["num_teams"] == "12"
    assert imported_dict["mathrace_only"]["num_teams_alternative"] == "10+2:70"
    assert imported_dict["mathrace_only"]["num_teams_nonguests"] == "10"
    assert imported_dict["mathrace_only"]["num_teams_guests"] == "2"
    assert imported_dict["punteggio_iniziale_squadre"] == 70


def test_journal_reader_alternative_race_definition_num_questions_entry_without_optional_argument(
    race_date: datetime.datetime
) -> None:
    """Test a num_questions entry in the alternative race definition without optional argument."""
    journal_with_num_teams = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 002 10+2:70 7 4.1;1 10-2 -- squadre: 12 quesiti: 7
--- 004 1 30 quesito 1
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_num_teams) as journal_stream:
        imported_dict = journal_stream.read("journal_with_num_teams", race_date)
    assert len(imported_dict["soluzioni"]) == 7
    assert imported_dict["num_problemi"] == 7
    assert imported_dict["mathrace_only"]["num_questions_alternative"] == "7"
    assert imported_dict["mathrace_only"]["default_score"] == "20"
    assert imported_dict["punteggio_iniziale_squadre"] == 70
    assert imported_dict["soluzioni"][0]["punteggio"] == 30
    assert imported_dict["soluzioni"][1]["punteggio"] == 20


def test_journal_reader_alternative_race_definition_num_questions_entry_with_optional_argument(
    race_date: datetime.datetime
) -> None:
    """Test a num_questions entry in the alternative race definition with optional argument."""
    journal_with_num_teams = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 002 10+2:70 7:40 4.1;1 10-2 -- squadre: 12 quesiti: 7
--- 004 1 30 quesito 1
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_num_teams) as journal_stream:
        imported_dict = journal_stream.read("journal_with_num_teams", race_date)
    assert len(imported_dict["soluzioni"]) == 7
    assert imported_dict["num_problemi"] == 7
    assert imported_dict["mathrace_only"]["num_questions_alternative"] == "7:40"
    assert imported_dict["mathrace_only"]["default_score"] == "40"
    assert imported_dict["punteggio_iniziale_squadre"] == 70
    assert imported_dict["soluzioni"][0]["punteggio"] == 30
    assert imported_dict["soluzioni"][1]["punteggio"] == 40


def test_journal_reader_alternative_race_definition_n_k_altk_blocco_entry_without_optional_arguments(
    race_date: datetime.datetime
) -> None:
    """Test a n_k_altk_blocco entry in the alternative race definition without any optional argument."""
    journal_with_n_k_altk_blocco = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 002 10+2:70 7:40 4 10-2 -- squadre: 12 quesiti: 7
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_n_k_altk_blocco) as journal_stream:
        imported_dict = journal_stream.read("journal_with_n_k_altk_blocco", race_date)
    assert imported_dict["n_blocco"] == 4
    assert imported_dict["k_blocco"] == 1
    assert imported_dict["mathrace_only"]["alternative_k_blocco"] == "1"


def test_journal_reader_alternative_race_definition_n_k_altk_blocco_entry_with_guests_optional_argument(
    race_date: datetime.datetime
) -> None:
    """Test a n_k_altk_blocco entry in the alternative race definition with the first optional argument."""
    journal_with_n_k_altk_blocco = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 002 10+2:70 7:40 4.2 10-2 -- squadre: 12 quesiti: 7
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_n_k_altk_blocco) as journal_stream:
        imported_dict = journal_stream.read("journal_with_n_k_altk_blocco", race_date)
    assert imported_dict["n_blocco"] == 4
    assert imported_dict["k_blocco"] == 2
    assert imported_dict["mathrace_only"]["alternative_k_blocco"] == "1"


def test_journal_reader_alternative_race_definition_n_k_altk_blocco_entry_with_initial_score_optional_argument(
    race_date: datetime.datetime
) -> None:
    """Test a n_k_altk_blocco entry in the alternative race definition with the second optional argument."""
    journal_with_n_k_altk_blocco = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 002 10+2:70 7:40 4;1 10-2 -- squadre: 12 quesiti: 7
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_n_k_altk_blocco) as journal_stream:
        imported_dict = journal_stream.read("journal_with_n_k_altk_blocco", race_date)
    assert imported_dict["n_blocco"] == 4
    assert imported_dict["k_blocco"] == 1
    assert imported_dict["mathrace_only"]["alternative_k_blocco"] == "1"


def test_journal_reader_alternative_race_definition_with_wrong_alternative_k_blocco_optional_argument(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the race definition contains a wrong alternative k parameter."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 002 10+2:70 7:40 4.1;9991 10-2 -- squadre: 12 quesiti: 7
0 200 inizio gara
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Invalid line --- 002 10+2:70 7:40 4.1;9991 10-2 in race definition: the expected alternative k is 1, "
        "but the race definition contains 9991.")


def test_journal_reader_alternative_race_definition_n_k_altk_blocco_entry_with_both_optional_arguments(
    race_date: datetime.datetime
) -> None:
    """Test a n_k_altk_blocco entry in the alternative race definition with both optional arguments."""
    journal_with_n_k_altk_blocco = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 002 10+2:70 7:40 4.2;1 10-2 -- squadre: 12 quesiti: 7
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_n_k_altk_blocco) as journal_stream:
        imported_dict = journal_stream.read("journal_with_n_k_altk_blocco", race_date)
    assert imported_dict["n_blocco"] == 4
    assert imported_dict["k_blocco"] == 2
    assert imported_dict["mathrace_only"]["alternative_k_blocco"] == "1"


def test_journal_reader_alternative_race_definition_missing_deadline_score_increase(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the race definition is missing the score increase deadline."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 002 10+2:70 7:40 4.1;1 10 -- squadre: 12 quesiti: 7
0 200 inizio gara
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Invalid line --- 002 10+2:70 7:40 4.1;1 10 in race definition: it does not contain the operator -")


@pytest.mark.parametrize(
    "race_definition_line", [
        "--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7",
        "--- 002 10+0:70 7:40 4.1;1 10-2 -- squadre: 10 quesiti: 7"
    ]
)
def test_journal_reader_bonus_superbonus_lines_with_different_race_definitions(
    race_definition_line: str, race_date: datetime.datetime
) -> None:
    """Test lines defining bonus and superbonus when used in combination with the different race definition."""
    journal_bonus_superbonus = io.StringIO(f"""\
--- 001 inizializzazione simulatore
{race_definition_line}
--- 011 10 120 115 110 18 16 15 14 13 12 11
--- 012 6 2100 260 240 230 220 210
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_bonus_superbonus) as journal_stream:
        imported_dict = journal_stream.read("journal_bonus_superbonus", race_date)
    assert imported_dict["fixed_bonus"] == "120,115,110,18,16,15,14,13,12,11"
    assert imported_dict["super_mega_bonus"] == "2100,260,240,230,220,210"


def test_journal_reader_bonus_superbonus_lines_with_standard_race_definition_smaller_cardinality(
    race_date: datetime.datetime
) -> None:
    """
    Test lines defining bonus and superbonus when used in combination with the standard race definition.

    This test is about the case in which the race definition reports a smaller cardinality (9 vs 10, 5 vs 6)
    than the bonus/superbonus lines.
    """
    journal_bonus_superbonus = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 9 5 4 1 1 10 2 -- squadre: 10 quesiti: 7
--- 011 10 120 115 110 18 16 15 14 13 12 11
--- 012 6 2100 260 240 230 220 210
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_bonus_superbonus) as journal_stream:
        imported_dict = journal_stream.read("journal_bonus_superbonus", race_date)
    assert imported_dict["fixed_bonus"] == "120,115,110,18,16,15,14,13,12"
    assert imported_dict["super_mega_bonus"] == "2100,260,240,230,220"


def test_journal_reader_bonus_superbonus_lines_with_standard_race_definition_larger_cardinality(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """
    Test lines defining bonus and superbonus when used in combination with the standard race definition.

    This test is about the case in which the race definition reports a larger cardinality (11 vs 10, 7 vs 6)
    than the bonus/superbonus lines. This results in an error.
    """
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 11 7 4 1 1 10 2 -- squadre: 10 quesiti: 7
--- 011 10 120 115 110 18 16 15 14 13 12 11
--- 012 6 2100 260 240 230 220 210
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Invalid line 10 120 115 110 18 16 15 14 13 12 11 in race definition: not enough values to read")


def test_journal_reader_bonus_superbonus_lines_with_comments(race_date: datetime.datetime) -> None:
    """Test lines defining bonus and superbonus with comments at the end of the line."""
    journal_bonus_superbonus = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 002 10+0:70 7:40 4.1;1 10-2 -- squadre: 10 quesiti: 7
--- 011 10 120 115 110 18 16 15 14 13 12 11 definizione dei 10 livelli di bonus
--- 012 6 2100 260 240 230 220 210 definizione dei 6 livelli di superbonus
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_bonus_superbonus) as journal_stream:
        imported_dict = journal_stream.read("journal_bonus_superbonus", race_date)
    assert imported_dict["fixed_bonus"] == "120,115,110,18,16,15,14,13,12,11"
    assert imported_dict["super_mega_bonus"] == "2100,260,240,230,220,210"


@pytest.mark.parametrize(
    "race_definition_line", [
        "--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7",
        "--- 002 8+2:70 7:40 4.1;1 10-2 -- squadre: 10 quesiti: 7"
    ]
)
def test_journal_reader_interplay_race_definition_with_team_definition(
    race_definition_line: str, race_date: datetime.datetime
) -> None:
    """Test the interplay between a race definition and team definition."""
    journal_with_guests = io.StringIO(f"""\
--- 001 inizializzazione simulatore
{race_definition_line}
--- 005 1 0 Squadra A
--- 005 2 1 Squadra B
--- 005 3 0 Squadra C
--- 005 4 1 Squadra D
--- 005 5 0 Squadra E
--- 005 6 0 Squadra F
--- 005 7 0 Squadra G
--- 005 8 0 Squadra H
--- 005 9 0 Squadra I
--- 005 10 0 Squadra J
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_guests) as journal_stream:
        imported_dict = journal_stream.read("journal_with_guests", race_date)
    assert imported_dict["n_blocco"] == 4
    assert imported_dict["k_blocco"] == 1
    assert len(imported_dict["squadre"]) == 10
    for s in range(10):
        assert imported_dict["squadre"][s]["nome"] == f"Squadra {chr(s + 97).capitalize()}"
        assert imported_dict["squadre"][s]["num"] == s + 1
        assert imported_dict["squadre"][s]["ospite"] is (True if s in (1, 3) else False)


@pytest.mark.parametrize(
    "race_definition_line,num_nonguests,num_guests", [
        ("--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7", 10, 0),
        ("--- 002 8+2:70 7:40 4.1;1 10-2 -- squadre: 10 quesiti: 7", 8, 2)
    ]
)
def test_journal_reader_interplay_race_definition_and_guests_without_team_definition(
    race_definition_line: str, num_nonguests: int, num_guests: int, race_date: datetime.datetime
) -> None:
    """
    Test the interplay between a race definition and guests without team definition.

    Guest teams, if present are at the end of the team list.
    """
    journal_with_guests = io.StringIO(f"""\
--- 001 inizializzazione simulatore
{race_definition_line}
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_guests) as journal_stream:
        imported_dict = journal_stream.read("journal_with_guests", race_date)
    assert imported_dict["n_blocco"] == 4
    assert imported_dict["k_blocco"] == 1
    assert len(imported_dict["squadre"]) == 10
    assert sum(not imported_dict["squadre"][s]["ospite"] for s in range(10)) == num_nonguests
    assert sum(imported_dict["squadre"][s]["ospite"] for s in range(10)) == num_guests
    for s in range(10):
        assert imported_dict["squadre"][s]["nome"] == f"Squadra {s + 1}"
        assert imported_dict["squadre"][s]["num"] == s + 1
        assert imported_dict["squadre"][s]["ospite"] is (True if s >= num_nonguests else False)


@pytest.mark.parametrize(
    "race_definition_line", [
        "--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7",
        "--- 002 8+2:70 7:40 4.1;1 10-2 -- squadre: 10 quesiti: 7"
    ]
)
def test_journal_reader_wrong_interplay_race_definition_with_team_definition(
    race_definition_line: str, race_date: datetime.datetime,
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test the interplay between a race definition and team definition when not all teams are listed."""
    wrong_journal = io.StringIO(f"""\
--- 001 inizializzazione simulatore
{race_definition_line}
--- 005 1 0 Squadra A
--- 005 2 1 Squadra B
0 200 inizio gara
600 210 termine gara
--- 999 fine simulatore
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Must either initialize all teams or none, since only initializing some of them results in "
        "ambiguities in determining which teams are guests and which are not")


def test_journal_reader_wrong_question_definition_placeholder(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when a question definition does not contain the r25013 placeholder."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
--- 004 1 20 0000 quesito 1
--- 004 2 20 9999 quesito 2
0 200 inizio gara
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Invalid line --- 004 2 20 9999 quesito 2 in question definition: it does not contain "
        "the expected placeholder")

def test_journal_reader_wrong_final_line(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the file finalization line is missing."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
600 029 termine gara
--- 999 fine simulatore con testo extra che non ci dovrebbe essere
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Invalid final line --- 999 fine simulatore con testo extra che non ci dovrebbe essere")


def test_journal_reader_wrong_extra_line_after_final(
    race_date: datetime.datetime, runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error with an extra line after the file finalization one."""
    wrong_journal = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
600 029 termine gara
--- 999 fine simulatore
610 011 9 3 1 squadra 9, quesito 3: giusto
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        "Journal contains extra line 610 011 9 3 1 squadra 9, quesito 3: giusto after race end")


def test_journal_reader_without_date() -> None:
    """Test that journal_reader skips events when date is not provided."""
    journal_with_events = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
60 022 aggiorna punteggio esercizi, orologio: 1
80 010 1 2 squadra 1 sceglie 2 come jolly
90 011 2 3 1 squadra 2, quesito 3: giusto
100 010 2 3 squadra 2 sceglie 3 come jolly
600 029 termine gara
--- 999 fine simulatore
""")
    with mathrace_interaction.journal_reader(journal_with_events) as journal_stream:
        imported_dict = journal_stream.read("journal_with_events", None)
    assert len(imported_dict["squadre"]) == 10
    assert len(imported_dict["soluzioni"]) == 7
    assert len(imported_dict["eventi"]) == 0


@pytest.mark.parametrize(
    "input_file_option,race_name_option,race_setup_only_option,output_file_option", [
        ("-i", "-n", "-s", "-o"),
        ("--input-file", "--race-name", "--race-setup-only", "--output-file")
    ]
)
def test_journal_reader_without_date_entrypoint(
    run_entrypoint: mathrace_interaction.typing.RunEntrypointFixtureType,
    input_file_option: str, race_name_option: str, race_setup_only_option: str, output_file_option: str
) -> None:
    """Test running journal_reader as entrypoint when date is not provided."""
    journal_with_events = io.StringIO("""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
60 022 aggiorna punteggio esercizi, orologio: 1
80 010 1 2 squadra 1 sceglie 2 come jolly
90 011 2 3 1 squadra 2, quesito 3: giusto
100 010 2 3 squadra 2 sceglie 3 come jolly
600 029 termine gara
--- 999 fine simulatore
""")
    with tempfile.NamedTemporaryFile() as journal_file, tempfile.NamedTemporaryFile() as json_file:
        with open(journal_file.name, "w") as journal_stream:
            journal_stream.write(journal_with_events.read())
        stdout, stderr = run_entrypoint(
            "mathrace_interaction.journal_reader", [
                input_file_option, journal_file.name, race_name_option, "journal_with_events",
                race_setup_only_option, output_file_option, json_file.name
            ]
        )
        assert stdout == ""
        assert stderr == ""
        with open(json_file.name) as json_stream:
            imported_dict = json.load(json_stream)
        assert len(imported_dict["squadre"]) == 10
        assert len(imported_dict["soluzioni"]) == 7
        assert len(imported_dict["eventi"]) == 0


@pytest.mark.parametrize(
    "race_event,expected_error", [
        ("80 010 0 2 squadra 0 sceglie 2 come jolly", "invalid team number 0"),
        ("90 011 0 3 1 squadra 0, quesito 3: giusto", "invalid team number 0"),
        ("80 010 1 0 squadra 1 sceglie 0 come jolly", "invalid question number 0"),
        ("90 011 2 0 1 squadra 2, quesito 0: giusto", "invalid question number 0"),
        ("80 091 0 43 squadra 0 bonus 43", "invalid team number 0")
    ]
)
def test_journal_reader_invalid_team_id_or_question_id(
    race_event: str, expected_error: str, race_date: datetime.datetime,
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that journal_reader raises an error when the team ID or question ID is not a positive number."""
    wrong_journal = io.StringIO(f"""\
--- 001 inizializzazione simulatore
--- 003 10 7 70 10 6 4 1 1 10 2 -- squadre: 10 quesiti: 7
0 002 inizio gara
60 022 aggiorna punteggio esercizi, orologio: 1
{race_event}
""")
    runtime_error_contains(
        lambda: mathrace_interaction.journal_reader(wrong_journal).read("wrong_journal", race_date),
        f'Invalid event content {" ".join(race_event.split(" ")[2:])}: {expected_error}')
