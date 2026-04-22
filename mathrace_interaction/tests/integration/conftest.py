# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""pytest configuration file for integration tests."""

import datetime
import os
import pathlib
import typing

import _pytest
import engine.models
import pytest
import Turing

import mathrace_interaction
import mathrace_interaction.test

read_score_file = mathrace_interaction.test.read_score_file_fixture
runtime_error_contains = mathrace_interaction.test.runtime_error_contains_fixture

@pytest.fixture
def simple_turing_race() -> engine.models.Gara:  # type: ignore[no-any-unimported]
    """Create a new turing race with the same content as the one used in the unit tests."""
    race_date = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
    turing_dict = {
        "nome": "test race",
        "inizio": race_date.isoformat(),
        "durata": 10,
        "durata_blocco": 2,
        "n_blocco": 4,
        "k_blocco": 1,
        "punteggio_iniziale_squadre": None,
        "fixed_bonus": "20,15,10,8,6,5,4,3,2,1",
        "super_mega_bonus": "100,60,40,30,20,10",
        "num_problemi": 7,
        "soluzioni": [
            {"nome": f"Problema {p}", "problema": p, "punteggio": 20, "risposta": 1} for p in range(1, 8)],
        "squadre": [{"nome": f"Squadra {s}", "num": s, "ospite": False} for s in range(1, 11)],
        "eventi": [
            {
                "subclass": "Jolly",
                "orario": (race_date + datetime.timedelta(minutes=4, seconds=3)).isoformat(),
                "squadra_id": 1,
                "problema": 2
            },
            {
                "subclass": "Jolly",
                "orario": (race_date + datetime.timedelta(minutes=4, seconds=11)).isoformat(),
                "squadra_id": 2,
                "problema": 3
            },
            {
                "subclass": "Jolly",
                "orario": (race_date + datetime.timedelta(minutes=4, seconds=19)).isoformat(),
                "squadra_id": 3,
                "problema": 4
            },
            {
                "subclass": "Consegna",
                "orario": (race_date + datetime.timedelta(minutes=5, seconds=30)).isoformat(),
                "squadra_id": 5,
                "problema": 5,
                "risposta": 1
            },
            {
                "subclass": "Consegna",
                "orario": (race_date + datetime.timedelta(minutes=5, seconds=41)).isoformat(),
                "squadra_id": 6,
                "problema": 6,
                "risposta": 0
            },
            {
                "subclass": "Consegna",
                "orario": (race_date + datetime.timedelta(minutes=7, seconds=15)).isoformat(),
                "squadra_id": 2,
                "problema": 3,
                "risposta": 1
            },
            {
                "subclass": "Consegna",
                "orario": (race_date + datetime.timedelta(minutes=7, seconds=30)).isoformat(),
                "squadra_id": 3,
                "problema": 4,
                "risposta": 0
            },
            {
                "subclass": "Consegna",
                "orario": (race_date + datetime.timedelta(minutes=8, seconds=30)).isoformat(),
                "squadra_id": 8,
                "problema": 2,
                "risposta": 0
            },
            {
                "subclass": "Bonus",
                "orario": (race_date + datetime.timedelta(minutes=8, seconds=40)).isoformat(),
                "squadra_id": 7,
                "punteggio": 43
            },
            {
                "subclass": "Consegna",
                "orario": (race_date + datetime.timedelta(minutes=9, seconds=30)).isoformat(),
                "squadra_id": 9,
                "problema": 3,
                "risposta": 1
            }
        ]
    }
    return engine.models.Gara.create_from_dict(turing_dict)

# Data files

_data_dir = pathlib.Path(__file__).parent.parent.parent / "data"

_journals = mathrace_interaction.test.get_data_files_in_directory(_data_dir, "journal")

_journal_versions = {
    journal_name: mathrace_interaction.determine_journal_version(open(journal))
    for (journal_name, journal) in _journals.items()}

# Integration testing with chrome driver takes several seconds for each journal file.
# To keep the total runtime of tests under control, run tests by default on a subset of the available files.
# Classify journals as either part of basic testing (key equal to True),
# or only part of full testing (key equal to False)
_journals_is_basic_testing = {
    # disfida: different formats across the years
    "2013/disfida.journal": True,
    "2014/disfida.journal": True,
    "2015/disfida.journal": True,
    "2016/disfida.journal": True,
    "2017/disfida.journal": True,
    "2018/disfida.journal": True,
    "2019/disfida.journal": True,
    "2020/disfida.journal": True,
    "2022/disfida.journal": True,
    "2023/disfida_legacy_format.journal": True,
    "2023/disfida_new_format.journal": True,
    "2024/disfida.journal": True,
    # kangourou: different total duration, score keeps increasing to the end of the race
    "2014/kangourou.journal": True,
    "2015/kangourou.journal": True,
    "2016/kangourou.journal": True,
    # cesenatico: alternative race definition and/or guest teams
    "2019/cesenatico_finale_femminile_formato_journal.journal": True,
    "2019/cesenatico_finale_formato_extracted.journal": True,
    "2019/cesenatico_finale_formato_journal.journal": True,
    "2019/cesenatico_semifinale_A.journal": False,
    "2019/cesenatico_semifinale_B.journal": False,
    "2019/cesenatico_semifinale_C.journal": False,
    "2019/cesenatico_semifinale_D.journal": False,
    # cesenatico: standard race definition, no guest teams, but with bonus/superbonus specification
    "2022/cesenatico_finale.journal": True,
    "2022/cesenatico_finale_femminile.journal": True,
    "2022/cesenatico_semifinale_A.journal": False,
    "2022/cesenatico_semifinale_B.journal": False,
    "2022/cesenatico_semifinale_C.journal": False,
    "2022/cesenatico_semifinale_D.journal": False,
    # cesenatico: standard race definition, no guest teams, no bonus/superbonus specification
    "2019/cesenatico_finale_femminile_formato_extracted.journal": False,
    "2020/cesenatico_finale.journal": False,
    "2020/cesenatico_finale_femminile.journal": False,
    "2020/cesenatico_semifinale_A.journal": False,
    "2020/cesenatico_semifinale_B.journal": False,
    "2020/cesenatico_semifinale_C.journal": False,
    "2020/cesenatico_semifinale_D.journal": False,
    "2021/cesenatico_finale.journal": False,
    "2021/cesenatico_finale_femminile.journal": False,
    "2021/cesenatico_semifinale_A.journal": False,
    "2021/cesenatico_semifinale_B.journal": False,
    "2021/cesenatico_semifinale_C.journal": False,
    "2021/cesenatico_semifinale_D.journal": False,
    "2021/cesenatico_semifinale_E.journal": False,
    "2021/cesenatico_semifinale_F.journal": False,
    # qualificazione: standard race definition, no guest teams, but with bonus/superbonus specification
    "2022/qualificazione_arezzo_cagliari_taranto_trento.journal": False,
    "2022/qualificazione_brindisi_catania_forli_cesena_sassari.journal": False,
    "2022/qualificazione_campobasso_collevaldelsa_pisa_napoli.journal": False,
    "2022/qualificazione_femminile_1.journal": False,
    "2022/qualificazione_femminile_2.journal": False,
    "2022/qualificazione_femminile_3.journal": False,
    "2022/qualificazione_firenze.journal": False,
    "2022/qualificazione_foggia_lucca_nuoro_tricase.journal": False,
    "2022/qualificazione_genova.journal": False,
    "2022/qualificazione_milano.journal": False,
    "2022/qualificazione_narni.journal": False,
    "2022/qualificazione_parma.journal": False,
    "2022/qualificazione_pordenone_udine.journal": False,
    "2022/qualificazione_reggio_emilia.journal": False,
    "2022/qualificazione_roma.journal": False,
    "2022/qualificazione_torino.journal": False,
    "2022/qualificazione_trieste.journal": False,
    "2022/qualificazione_velletri.journal": False,
    "2022/qualificazione_vicenza.journal": False,
    # qualificazione femminale: standard race definition, no guest teams, but with team names
    "2019/cesenatico_finale_formato_extracted_nomi_squadra.journal": True,
    "2023/qualificazione_femminile_1.journal": True,
    "2023/qualificazione_femminile_2.journal": True,
    "2023/qualificazione_femminile_3.journal": True,
    # additional tests: different timestamp format
    "2024/february_9_short_run.journal": True,
}

_jsons = mathrace_interaction.test.get_data_files_in_directory(_data_dir, "json")


@pytest.fixture
def admin_user() -> engine.models.User:  # type: ignore[no-any-unimported]
    """Return a superuser of turing."""
    return engine.models.User._default_manager.create_superuser(username="admin", password="pwadmin")


@pytest.fixture
def normal_user() -> engine.models.User:  # type: ignore[no-any-unimported]
    """Return a normal user (logged in, but not superuser) of turing."""
    return engine.models.User._default_manager.create_user(username="user", password="pwuser")


@pytest.fixture
def authenticated_user(request: _pytest.fixtures.SubRequest) -> engine.models.User:  # type: ignore[no-any-unimported]
    """Return a user after login, either administrator or not."""
    return request.getfixturevalue(request.param)


@pytest.fixture
def any_user(request: _pytest.fixtures.SubRequest) -> engine.models.User | None:  # type: ignore[no-any-unimported]
    """Return a logged in user, or None if the user is logged out."""
    if request.param is None:
        return None
    else:
        return request.getfixturevalue(request.param)


def pytest_addoption(parser: pytest.Parser, pluginmanager: pytest.PytestPluginManager) -> None:
    """Add options to run tests on all data files, rather than only the basic subset."""
    parser.addoption("--all-data-files", action="store_true", help="Run tests on all data files")


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize tests with fixtures to iterate over content of the data directory."""
    # Parametrization over journals
    assert set(_journals_is_basic_testing.keys()) == set(_journals.keys())
    if metafunc.config.option.all_data_files:
        journal_names = list(_journals_is_basic_testing.keys())
    else:
        journal_names = [
            journal_name for (journal_name, is_basic_testing) in _journals_is_basic_testing.items()
            if is_basic_testing]
    mathrace_interaction.test.parametrize_journal_fixtures(
        lambda: {journal_name: open(_journals[journal_name]) for journal_name in journal_names},
        lambda: {journal_name: _journal_versions[journal_name] for journal_name in journal_names},
        metafunc
    )
    # Parametrization over json files
    if "json_name" in metafunc.fixturenames:
        metafunc.parametrize("json_name", [json_name for json_name in _jsons if "bugs" not in json_name])
    # Parametrization over users
    if "authenticated_user" in metafunc.fixturenames:
        metafunc.parametrize("authenticated_user", ["admin_user", "normal_user"], indirect=True)
    if "any_user" in metafunc.fixturenames:
        metafunc.parametrize("any_user", ["admin_user", "normal_user", None], indirect=True)

@pytest.fixture
def data_dir() -> pathlib.Path:
    """Return the data directory of mathrace-interaction."""
    return _data_dir


# pytest-django sets up a test database, but entrypoints are tested in a separate process,
# and thus would use the production database. Manually overrided the database name as an environment variable.

_run_entrypoint_internal = mathrace_interaction.test.run_entrypoint_fixture

@pytest.fixture
def run_entrypoint(
    _run_entrypoint_internal: mathrace_interaction.typing.RunEntrypointFixtureType
) -> typing.Generator[mathrace_interaction.typing.RunEntrypointFixtureType, None, None]:
    """Customize DJANGO_SETTINGS_MODULE when running through entrypoints."""
    test_database_settings = Turing.settings.DATABASES["default"]
    test_database_engine = test_database_settings["ENGINE"]
    assert test_database_engine in ("django.db.backends.postgresql_psycopg2", "django.db.backends.sqlite3")
    if test_database_engine == "django.db.backends.postgresql_psycopg2":
        # pytest-django has already prepended test_ to the production database name
        test_database_name = test_database_settings["NAME"]
        assert "RDS_DB_NAME" not in os.environ
        os.environ["RDS_DB_NAME"] = test_database_name
    elif test_database_engine == "django.db.backends.sqlite3":
        # pytest-django has already prepared a temporary database, but there is no environment variable option
        # associated to it we can change. Simply skip entrypoint tests with sqlite3.
        pytest.skip(reason="Entrypoint tests are not compatible with sqlite3")
    yield _run_entrypoint_internal
    if test_database_engine == "django.db.backends.postgresql_psycopg2":
        os.environ.pop("RDS_DB_NAME")
