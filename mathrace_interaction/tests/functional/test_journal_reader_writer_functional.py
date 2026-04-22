# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.journal_reader and mathrace_interaction.journal_writer on journals in data."""

import datetime
import io
import os
import typing

import pytest

import mathrace_interaction
import mathrace_interaction.filter


def strip_race_end_line(journal_content: str) -> str:
    """Strip the race end line from a journal content."""
    return "\n".join(line for line in journal_content.split("\n") if "termine gara" not in line)


def offset_timestamp(journal_content: str, timestamp_offset: int) -> str:
    """Offset all timestamps of the prescribed amount of seconds."""
    input_lines = [line for line in journal_content.split("\n")]
    output_lines = []
    for line in input_lines:
        if line.startswith("---") or "inizio gara" in line:
            output_lines.append(line)
        else:
            timestamp, event = line.split(" ", maxsplit=1)
            output_lines.append(f"{int(timestamp) + timestamp_offset} {event}")
    return "\n".join(output_lines)


def replace_deadline_score_increase(
    journal_content: str, mock_deadline_score_increase: int, actual_deadline_score_increase: int
) -> str:
    """Replace the deadline score increase time."""
    input_lines = [line for line in journal_content.split("\n")]
    output_lines = []
    for line in input_lines:
        if line.startswith("--- 003"):
            output_lines.append(
                line.replace(f"{mock_deadline_score_increase} --", f"{actual_deadline_score_increase} --"))
        else:
            output_lines.append(line)
    return "\n".join(output_lines)


def strip_race_setup_code_lines(journal_content: str, code: str) -> str:
    """Strip all lines associated to the provided race setup event."""
    input_lines = [line for line in journal_content.split("\n")]
    output_lines = []
    for line in input_lines:
        if not line.startswith(f"--- {code}"):
            output_lines.append(line)
    return "\n".join(output_lines)


def strip_protocol_numbers(journal_content: str) -> str:
    """Strip protocol numbers from race events."""
    input_lines = [line for line in journal_content.split("\n")]
    output_lines = []
    for line in input_lines:
        if "PROT:" in line:
            line_before_prot, line_after_prot = line.split("PROT:")
            _, line_after_prot = line_after_prot.split("squadra")
            output_lines.append(f"{line_before_prot} squadra {line_after_prot}")
        else:
            output_lines.append(line)
    return "\n".join(output_lines)


def strip_manual_bonus_reason(journal_content: str) -> str:
    """Strip reason explaining why manual bonus was added."""
    input_lines = [line for line in journal_content.split("\n")]
    output_lines = []
    for line in input_lines:
        if "motivazione:" in line:
            line_before_reason, _ = line.split(" motivazione:")
            output_lines.append(line_before_reason)
        else:
            output_lines.append(line)
    return "\n".join(output_lines)


def same_version_comparison(journal: typing.TextIO, journal_name: str, exported_journal: str) -> None:
    """Return the expected journal for a same version comparison."""
    stripped_journal = mathrace_interaction.filter.strip_comments_and_unhandled_events_from_journal(journal)
    # The line containing the end race timestamp cannot be compared, because the two implementations use
    # different conventions on setting the grace period for answer submission after race end
    stripped_journal = strip_race_end_line(stripped_journal)
    exported_journal = strip_race_end_line(exported_journal)
    # We do not store the reason for manual bonus, hence it must be removed from the input journal in order
    # to be able to carry out a comparison
    stripped_journal = strip_manual_bonus_reason(stripped_journal)
    # Some journals have an expected timestamp offset due to the TIMER_UPDATE not happening on the minute
    if journal_name == "2013/disfida.journal":
        timer_offset = 24
    elif journal_name == "2014/disfida.journal":
        timer_offset = 18
    elif journal_name == "2014/kangourou.journal":
        timer_offset = 51
    elif journal_name == "2015/disfida.journal":
        timer_offset = 8
    elif journal_name == "2015/kangourou.journal":
        timer_offset = 42
    elif journal_name == "2016/disfida.journal":
        timer_offset = 50
    elif journal_name == "2016/kangourou.journal":
        timer_offset = 38
    else:
        timer_offset = None
    if timer_offset is not None:
        stripped_journal = offset_timestamp(stripped_journal, timer_offset)
    # Some journals contain a mock deadline score increase set to a big number, larger than the total race time
    if journal_name in ("2014/kangourou.journal", "2015/kangourou.journal", "2016/kangourou.journal"):
        stripped_journal = replace_deadline_score_increase(stripped_journal, 10000, 90)
    # Some journals contain differences in the style of race setup code lines that we cannot check here,
    # because this library maintains a single style
    if journal_name in (
        "2019/cesenatico_finale_femminile_formato_journal.journal", "2019/cesenatico_finale_formato_journal.journal",
        "2019/cesenatico_semifinale_A.journal", "2019/cesenatico_semifinale_B.journal",
        "2019/cesenatico_semifinale_C.journal", "2019/cesenatico_semifinale_D.journal"
    ):
        # These journals use the alternative race definition 002, but does not provide explicitly
        # the question definition 004 and team definition 005 sections.
        stripped_journal = strip_race_setup_code_lines(stripped_journal, "002")
        exported_journal = strip_race_setup_code_lines(exported_journal, "002")
        exported_journal = strip_race_setup_code_lines(exported_journal, "004")
        exported_journal = strip_race_setup_code_lines(exported_journal, "005")
    elif journal_name in (
        "2020/disfida.journal", "2022/cesenatico_finale.journal", "2022/cesenatico_finale_femminile.journal",
        "2022/cesenatico_semifinale_A.journal", "2022/cesenatico_semifinale_B.journal",
        "2022/cesenatico_semifinale_C.journal", "2022/cesenatico_semifinale_D.journal",
        "2022/qualificazione_arezzo_cagliari_taranto_trento.journal",
        "2022/qualificazione_brindisi_catania_forli_cesena_sassari.journal",
        "2022/qualificazione_campobasso_collevaldelsa_pisa_napoli.journal",
        "2022/qualificazione_femminile_1.journal", "2022/qualificazione_femminile_2.journal",
        "2022/qualificazione_femminile_3.journal", "2022/qualificazione_firenze.journal",
        "2022/qualificazione_foggia_lucca_nuoro_tricase.journal", "2022/qualificazione_genova.journal",
        "2022/qualificazione_milano.journal", "2022/qualificazione_narni.journal",
        "2022/qualificazione_parma.journal", "2022/qualificazione_pordenone_udine.journal",
        "2022/qualificazione_reggio_emilia.journal", "2022/qualificazione_roma.journal",
        "2022/qualificazione_torino.journal", "2022/qualificazione_trieste.journal",
        "2022/qualificazione_velletri.journal", "2022/qualificazione_vicenza.journal", "2022/disfida.journal",
        "2023/qualificazione_femminile_1.journal", "2023/qualificazione_femminile_2.journal",
        "2023/qualificazione_femminile_3.journal"
    ):
        # These journals use the standard race definition 003, but our exporter decides to use the alternative one.
        stripped_journal = strip_race_setup_code_lines(stripped_journal, "003")
        exported_journal = strip_race_setup_code_lines(exported_journal, "002")
        if journal_name not in (
            "2022/cesenatico_finale.journal", "2023/qualificazione_femminile_1.journal",
            "2023/qualificazione_femminile_2.journal", "2023/qualificazione_femminile_3.journal"
        ):
            exported_journal = strip_race_setup_code_lines(exported_journal, "005")
    # Some journals report in a slightly different format the bonus and superbonus entries.
    # This typically happens when setting a large superbonus cardinality and adding zeros at the end
    if journal_name in (
        "2020/disfida.journal", "2022/cesenatico_finale.journal",
        "2022/cesenatico_finale_femminile.journal", "2022/cesenatico_semifinale_A.journal",
        "2022/cesenatico_semifinale_B.journal", "2022/cesenatico_semifinale_C.journal",
        "2022/cesenatico_semifinale_D.journal", "2022/qualificazione_arezzo_cagliari_taranto_trento.journal",
        "2022/qualificazione_brindisi_catania_forli_cesena_sassari.journal",
        "2022/qualificazione_campobasso_collevaldelsa_pisa_napoli.journal",
        "2022/qualificazione_femminile_1.journal", "2022/qualificazione_femminile_2.journal",
        "2022/qualificazione_femminile_3.journal", "2022/qualificazione_firenze.journal",
        "2022/qualificazione_foggia_lucca_nuoro_tricase.journal", "2022/qualificazione_genova.journal",
        "2022/qualificazione_milano.journal", "2022/qualificazione_narni.journal",
        "2022/qualificazione_parma.journal", "2022/qualificazione_pordenone_udine.journal",
        "2022/qualificazione_reggio_emilia.journal", "2022/qualificazione_roma.journal",
        "2022/qualificazione_torino.journal", "2022/qualificazione_trieste.journal",
        "2022/qualificazione_velletri.journal", "2022/qualificazione_vicenza.journal", "2022/disfida.journal",
        "2023/qualificazione_femminile_1.journal", "2023/qualificazione_femminile_2.journal",
        "2023/qualificazione_femminile_3.journal", "2023/disfida_new_format.journal",
        "2024/february_9_short_run.journal", "2024/disfida.journal"
    ):
        stripped_journal = strip_race_setup_code_lines(stripped_journal, "011")
        exported_journal = strip_race_setup_code_lines(exported_journal, "011")
        stripped_journal = strip_race_setup_code_lines(stripped_journal, "012")
        exported_journal = strip_race_setup_code_lines(exported_journal, "012")
    # Some journals have protocol numbers that are not formally correct
    if journal_name in ("2019/cesenatico_semifinale_A.journal", ):
        stripped_journal = strip_protocol_numbers(stripped_journal)
        exported_journal = strip_protocol_numbers(exported_journal)
    # Compare the two journals
    assert stripped_journal == exported_journal


def test_journal_reader_runs_on_data(journal: typing.TextIO, journal_name: str) -> None:
    """Test that journal_reader runs successfully on all journals in the data directory."""
    journal_year, _ = journal_name.split(os.sep, maxsplit=1)
    journal_date = datetime.datetime(int(journal_year), 1, 1, tzinfo=datetime.UTC)
    with mathrace_interaction.journal_reader(journal) as journal_stream:
        journal_stream.read(journal_name, journal_date)


def test_journal_reader_writer_same_version_comparison(
    journal: typing.TextIO, journal_name: str, journal_version: str
) -> None:
    """Test that journal_reader and journal_writer (almost) returns the original journal file."""
    journal_year, _ = journal_name.split(os.sep, maxsplit=1)
    journal_date = datetime.datetime(int(journal_year), 1, 1, tzinfo=datetime.UTC)
    with (
        io.StringIO("") as exported_journal,
        mathrace_interaction.journal_reader(journal) as input_journal_stream,
        mathrace_interaction.journal_writer(exported_journal, journal_version) as output_journal_stream
    ):
        turing_dict = input_journal_stream.read(journal_name, journal_date)
        mathrace_interaction.filter.strip_milliseconds_in_imported_turing(turing_dict)
        output_journal_stream.write(turing_dict)
        same_version_comparison(journal, journal_name, exported_journal.getvalue().strip("\n"))


@pytest.mark.parametrize("target_version", mathrace_interaction.list_journal_versions())
def test_journal_version_converter_same_turing_dictionary(
    journal: typing.TextIO, journal_name: str, target_version: str
) -> None:
    """Test that journal_reader and journal_version_converter return the same turing dictionary."""
    if (
        journal_name in (
            "2019/cesenatico_finale_formato_extracted.journal", "2019/cesenatico_finale_formato_journal.journal",
            "2019/cesenatico_finale_formato_extracted_nomi_squadra.journal", "2019/cesenatico_semifinale_A.journal",
            "2019/cesenatico_semifinale_B.journal", "2019/cesenatico_semifinale_C.journal",
            "2019/cesenatico_semifinale_D.journal"
        ) and target_version in ("r5539", "r11167", "r11184", "r11189")
    ):
        pytest.skip("This version does not support a value of k_blocco different from one")
    elif (
        journal_name in (
            "2019/cesenatico_finale_formato_journal.journal",
            "2019/cesenatico_finale_formato_extracted_nomi_squadra.journal", "2019/cesenatico_semifinale_A.journal",
            "2019/cesenatico_semifinale_B.journal", "2019/cesenatico_semifinale_C.journal",
            "2019/cesenatico_semifinale_D.journal", "2022/cesenatico_finale.journal",
            "2023/qualificazione_femminile_1.journal", "2023/qualificazione_femminile_2.journal",
            "2023/qualificazione_femminile_3.journal", "2023/disfida_new_format.journal",
            "2024/february_9_short_run.journal"
        ) and target_version in ("r5539", "r11167", "r11184", "r11189", "r17497")
    ):
        pytest.skip("This version does not support customizing the team name or setting its guest status")
    elif (
        journal_name in (
            "2020/disfida.journal", "2022/cesenatico_finale.journal", "2022/cesenatico_finale_femminile.journal",
            "2022/cesenatico_semifinale_A.journal", "2022/cesenatico_semifinale_B.journal",
            "2022/cesenatico_semifinale_C.journal", "2022/cesenatico_semifinale_D.journal",
            "2022/qualificazione_arezzo_cagliari_taranto_trento.journal",
            "2022/qualificazione_brindisi_catania_forli_cesena_sassari.journal",
            "2022/qualificazione_campobasso_collevaldelsa_pisa_napoli.journal",
            "2022/qualificazione_femminile_1.journal", "2022/qualificazione_femminile_2.journal",
            "2022/qualificazione_femminile_3.journal", "2022/qualificazione_firenze.journal",
            "2022/qualificazione_foggia_lucca_nuoro_tricase.journal", "2022/qualificazione_genova.journal",
            "2022/qualificazione_milano.journal", "2022/qualificazione_narni.journal",
            "2022/qualificazione_parma.journal", "2022/qualificazione_pordenone_udine.journal",
            "2022/qualificazione_reggio_emilia.journal", "2022/qualificazione_roma.journal",
            "2022/qualificazione_torino.journal", "2022/qualificazione_trieste.journal",
            "2022/qualificazione_velletri.journal", "2022/qualificazione_vicenza.journal", "2022/disfida.journal",
            "2024/disfida.journal"
        ) and target_version in ("r5539", "r11167", "r11184", "r11189", "r17497", "r17505", "r17548")
    ):
        pytest.skip("This version does not support customizing bonus and superbonus values")
    elif (
        (
            journal_name in (
                "2019/cesenatico_finale_formato_journal.journal", "2019/cesenatico_semifinale_A.journal",
                "2019/cesenatico_semifinale_B.journal", "2019/cesenatico_semifinale_C.journal",
                "2019/cesenatico_semifinale_D.journal"
            ) and target_version in ("r17505", )
        )
        or
        (
            journal_name in (
                "2019/cesenatico_finale_femminile_formato_journal.journal",
            ) and target_version in ("r5539", "r11167", "r11184", "r11189", "r17497", "r17505")
        )
    ):
        pytest.skip("This version hardcodes the initial score, while the original journal did not store it")
    else:
        journal_year, _ = journal_name.split(os.sep, maxsplit=1)
        journal_date = datetime.datetime(int(journal_year), 1, 1, tzinfo=datetime.UTC)
        journal_copy = io.StringIO(journal.read())
        journal.seek(0)
        with mathrace_interaction.journal_reader(journal_copy) as journal_stream:
            turing_dict1 = journal_stream.read(journal_name, journal_date)
            with mathrace_interaction.journal_reader(
                io.StringIO(mathrace_interaction.journal_version_converter(journal_copy, target_version).strip("\n"))
            ) as converted_stream:
                converted_stream.strict_timestamp_race_events = False  # type: ignore[attr-defined]
                turing_dict2 = converted_stream.read(journal_name, journal_date)
        mathrace_interaction.filter.strip_mathrace_only_attributes_from_imported_turing(turing_dict1)
        mathrace_interaction.filter.strip_mathrace_only_attributes_from_imported_turing(turing_dict2)
        assert turing_dict1 == turing_dict2
