# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""pytest configuration file for functional tests."""

import pathlib

import pytest

import mathrace_interaction.test

_data_dir = pathlib.Path(__file__).parent.parent.parent / "data"

_journals = mathrace_interaction.test.get_data_files_in_directory(_data_dir, "journal")

_journal_versions = {
    # r5539
    "2013/disfida.journal": "r5539",
    "2014/disfida.journal": "r5539",
    # r11167
    # ... untested ...
    # r11184
    "2014/kangourou.journal": "r11167",
    "2015/kangourou.journal": "r11184",
    "2016/disfida.journal": "r11184",
    "2016/kangourou.journal": "r11184",
    "2017/disfida.journal": "r11184",
    "2018/disfida.journal": "r11184",
    "2019/cesenatico_finale_femminile_formato_extracted.journal": "r11184",
    "2019/disfida.journal": "r11184",
    "2020/cesenatico_finale.journal": "r11184",
    "2020/cesenatico_finale_femminile.journal": "r11184",
    "2020/cesenatico_semifinale_A.journal": "r11184",
    "2020/cesenatico_semifinale_B.journal": "r11184",
    "2020/cesenatico_semifinale_C.journal": "r11184",
    "2020/cesenatico_semifinale_D.journal": "r11184",
    "2021/cesenatico_finale.journal": "r11184",
    "2021/cesenatico_finale_femminile.journal": "r11184",
    "2021/cesenatico_semifinale_A.journal": "r11184",
    "2021/cesenatico_semifinale_B.journal": "r11184",
    "2021/cesenatico_semifinale_C.journal": "r11184",
    "2021/cesenatico_semifinale_D.journal": "r11184",
    "2021/cesenatico_semifinale_E.journal": "r11184",
    "2021/cesenatico_semifinale_F.journal": "r11184",
    "2023/disfida_legacy_format.journal": "r11184",
    # r11189
    "2015/disfida.journal": "r11189",
    # r17497
    "2019/cesenatico_finale_formato_extracted.journal": "r17497",
    # r17505
    "2019/cesenatico_finale_formato_extracted_nomi_squadra.journal": "r17505",
    # r17548
    "2019/cesenatico_finale_femminile_formato_journal.journal": "r17548",
    "2019/cesenatico_finale_formato_journal.journal": "r17548",
    "2019/cesenatico_semifinale_A.journal": "r17548",
    "2019/cesenatico_semifinale_B.journal": "r17548",
    "2019/cesenatico_semifinale_C.journal": "r17548",
    "2019/cesenatico_semifinale_D.journal": "r17548",
    # r20642
    "2020/disfida.journal": "r20642",
    "2022/cesenatico_finale.journal": "r20642",
    "2022/cesenatico_finale_femminile.journal": "r20642",
    "2022/cesenatico_semifinale_A.journal": "r20642",
    "2022/cesenatico_semifinale_B.journal": "r20642",
    "2022/cesenatico_semifinale_C.journal": "r20642",
    "2022/cesenatico_semifinale_D.journal": "r20642",
    "2022/qualificazione_arezzo_cagliari_taranto_trento.journal": "r20642",
    "2022/qualificazione_brindisi_catania_forli_cesena_sassari.journal": "r20642",
    "2022/qualificazione_campobasso_collevaldelsa_pisa_napoli.journal": "r20642",
    "2022/qualificazione_femminile_1.journal": "r20642",
    "2022/qualificazione_femminile_2.journal": "r20642",
    "2022/qualificazione_femminile_3.journal": "r20642",
    "2022/qualificazione_firenze.journal": "r20642",
    "2022/qualificazione_foggia_lucca_nuoro_tricase.journal": "r20642",
    "2022/qualificazione_genova.journal": "r20642",
    "2022/qualificazione_milano.journal": "r20642",
    "2022/qualificazione_narni.journal": "r20642",
    "2022/qualificazione_parma.journal": "r20642",
    "2022/qualificazione_pordenone_udine.journal": "r20642",
    "2022/qualificazione_reggio_emilia.journal": "r20642",
    "2022/qualificazione_roma.journal": "r20642",
    "2022/qualificazione_torino.journal": "r20642",
    "2022/qualificazione_trieste.journal": "r20642",
    "2022/qualificazione_velletri.journal": "r20642",
    "2022/qualificazione_vicenza.journal": "r20642",
    "2022/disfida.journal": "r20642",
    "2023/qualificazione_femminile_1.journal": "r20642",
    "2023/qualificazione_femminile_2.journal": "r20642",
    "2023/qualificazione_femminile_3.journal": "r20642",
    # r20644
    # ... untested ...
    # r25013
    "2023/disfida_new_format.journal": "r25013",
    "2024/february_9_short_run.journal": "r25013",
    "2024/disfida.journal": "r25013",
}


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize tests with journal fixture over journals in the data directory."""
    mathrace_interaction.test.parametrize_journal_fixtures(
        lambda: {journal_name: open(journal) for (journal_name, journal) in _journals.items()},
        lambda: _journal_versions,
        metafunc
    )


@pytest.fixture
def data_dir() -> pathlib.Path:
    """Return the data directory of mathrace-interaction."""
    return _data_dir
