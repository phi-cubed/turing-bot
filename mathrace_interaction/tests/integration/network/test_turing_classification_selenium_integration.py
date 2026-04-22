# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Test mathrace_interaction.network.TuringClassificationSelenium on a live turing instace."""

import datetime

import engine.models
import pytest
import pytest_django.live_server_helper
import selenium.webdriver.common.by
import selenium.webdriver.support.color

import mathrace_interaction.network
import mathrace_interaction.time
import mathrace_interaction.typing


class Browser(mathrace_interaction.network.TuringClassificationSelenium):
    """Helper class that extends TuringClassificationSelenium on the URL of the live turing instance."""

    def __init__(self, live_server: pytest_django.live_server_helper.LiveServer, race_id: int) -> None:
        super().__init__(live_server.url, race_id, 10)

    def login(self, user: engine.models.User | None) -> None:  # type: ignore[no-any-unimported, override]
        """Log into the turing instance with the credententials of the provided user."""
        if user is not None:
            super().login(user.username, "pw" + user.username)



def test_classification_browser_login_integration(  # type: ignore[no-any-unimported]
    live_server: pytest_django.live_server_helper.LiveServer, authenticated_user: engine.models.User
) -> None:
    """Test mathrace_interaction.network.TuringClassificationSelenium.login."""
    browser = Browser(live_server, 0)
    browser.login(authenticated_user)
    assert "Cambio password" in browser.page_source
    browser.quit()


def test_classification_browser_go_to_classification_page_integration(  # type: ignore[no-any-unimported]
    live_server: pytest_django.live_server_helper.LiveServer, simple_turing_race: engine.models.Gara,
    any_user: engine.models.User
) -> None:
    """Test mathrace_interaction.network.TuringClassificationSelenium.go_to_classification_page."""
    browser = Browser(live_server, simple_turing_race.pk)
    browser.login(any_user)
    browser.go_to_classification_page("unica", {})
    assert (
        f'Gara: <a href="/engine/gara/{simple_turing_race.pk}">test race</a> - visualizzazione unica'
        in browser.page_source)
    browser.quit()


@pytest.mark.parametrize("classification_type", ["unica", "squadre"])
@pytest.mark.parametrize("querystring", [
    {"race_time": "360"}, {"ended": "false"}, {"computation_rate": "15"}
])
def test_classification_browser_go_to_classification_page_integration_non_default_querystring_normal_user(  # type: ignore[no-any-unimported]
    live_server: pytest_django.live_server_helper.LiveServer, simple_turing_race: engine.models.Gara,
    admin_user: engine.models.User, normal_user: engine.models.User, classification_type: str,
    querystring: dict[str, str], runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test team score computation with non default querystring and normal user."""
    simple_turing_race.admin = admin_user
    simple_turing_race.save()
    browser = Browser(live_server, simple_turing_race.pk)
    browser.login(normal_user)
    runtime_error_contains(
        lambda: browser.go_to_classification_page(classification_type, querystring),
        "The user does not have the permissions to see this classification")
    browser.quit()


@pytest.mark.parametrize("classification_type", ["unica", "squadre"])
@pytest.mark.parametrize("querystring", [
    {"race_time": "360"}, {"ended": "false"}, {"computation_rate": "15"}
])
def test_classification_browser_go_to_classification_page_integration_non_default_querystring_anonymous_user(  # type: ignore[no-any-unimported]
    live_server: pytest_django.live_server_helper.LiveServer, simple_turing_race: engine.models.Gara,
    admin_user: engine.models.User, classification_type: str,  querystring: dict[str, str],
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test team score computation with non default querystring and anonymous user."""
    simple_turing_race.admin = admin_user
    simple_turing_race.save()
    browser = Browser(live_server, simple_turing_race.pk)
    runtime_error_contains(
        lambda: browser.go_to_classification_page(classification_type, querystring),
        "The user must be logged in to see this classification")
    browser.quit()


@pytest.mark.parametrize("classification_type", ["unica", "squadre"])
@pytest.mark.parametrize("true_value", [True, 1, "true", "True"])
def test_classification_browser_go_to_classification_page_integration_ended_true(  # type: ignore[no-any-unimported]
    live_server: pytest_django.live_server_helper.LiveServer, simple_turing_race: engine.models.Gara,
    admin_user: engine.models.User, classification_type: str, true_value: bool | int | str
) -> None:
    """Test that the replay control panel appears when providing the querystring ended=true."""
    simple_turing_race.admin = admin_user
    simple_turing_race.save()
    browser = Browser(live_server, simple_turing_race.pk)
    browser.login(admin_user)
    browser.go_to_classification_page(classification_type, {"ended": str(true_value)})
    assert 'id="replayControl"' in browser.page_source
    browser.quit()


@pytest.mark.parametrize("classification_type", ["unica", "squadre"])
@pytest.mark.parametrize("false_value", [False, 0, "false", "False"])
def test_classification_browser_go_to_classification_page_integration_ended_false(  # type: ignore[no-any-unimported]
    live_server: pytest_django.live_server_helper.LiveServer, simple_turing_race: engine.models.Gara,
    admin_user: engine.models.User, classification_type: str, false_value: bool | int | str
) -> None:
    """Test that the replay control panel disappears when providing the querystring ended=false."""
    simple_turing_race.admin = admin_user
    simple_turing_race.save()
    browser = Browser(live_server, simple_turing_race.pk)
    browser.login(admin_user)
    browser.go_to_classification_page(classification_type, {"ended": str(false_value)})
    assert 'id="replayControl"' not in browser.page_source
    browser.quit()


def test_classification_browser_get_teams_score_integration(  # type: ignore[no-any-unimported]
    live_server: pytest_django.live_server_helper.LiveServer, simple_turing_race: engine.models.Gara,
    any_user: engine.models.User
) -> None:
    """Test mathrace_interaction.network.TuringClassificationSelenium.get_teams_score."""
    browser = Browser(live_server, simple_turing_race.pk)
    browser.login(any_user)
    browser.go_to_classification_page("squadre", {})
    browser.lock()
    scores = browser.get_teams_score()
    assert scores == [70, 166, 50, 70, 118, 60, 113, 60, 113, 70]
    browser.quit()


@pytest.mark.parametrize("race_time", ["00:06:00", "360"])
def test_classification_browser_get_teams_score_integration_non_default_race_time(  # type: ignore[no-any-unimported]
    live_server: pytest_django.live_server_helper.LiveServer, simple_turing_race: engine.models.Gara,
    admin_user: engine.models.User, race_time: str
) -> None:
    """Test team score computation with non default race time."""
    simple_turing_race.admin = admin_user
    simple_turing_race.save()
    browser = Browser(live_server, simple_turing_race.pk)
    browser.login(admin_user)
    browser.go_to_classification_page("squadre", {"race_time": race_time})
    browser.lock()
    scores = browser.get_teams_score()
    assert scores == [70, 70, 70, 70, 116, 60, 70, 70, 70, 70]
    browser.quit()


@pytest.mark.parametrize("computation_rate_prefix", ["00:00:0", ""])
def test_classification_browser_get_teams_score_integration_over_time(  # type: ignore[no-any-unimported]
    live_server: pytest_django.live_server_helper.LiveServer, simple_turing_race: engine.models.Gara,
    admin_user: engine.models.User, computation_rate_prefix: str
) -> None:
    """Test team score computation with non default computation rate and freeze/unfreeze time."""
    simple_turing_race.admin = admin_user
    simple_turing_race.save()

    # Open three browsers
    browser1 = Browser(live_server, simple_turing_race.pk)
    browser1.login(admin_user)
    browser2 = Browser(live_server, simple_turing_race.pk)
    browser2.login(admin_user)
    browser3 = Browser(live_server, simple_turing_race.pk)
    browser3.login(admin_user)

    # Set race time to a time which is just before the first answer submission
    base_querystring = {"race_time": "00:05:28", "ended": "false"}

    # Set a computation rate of 1 second in the first browser, and higher than 1 seconds in the other two browsers.
    querystring1 = {"computation_rate": computation_rate_prefix + "1"} | base_querystring
    querystring23 = {"computation_rate": computation_rate_prefix + "8"} | base_querystring
    browser1.go_to_classification_page("squadre", querystring1)
    browser2.go_to_classification_page("squadre", querystring23)
    browser3.go_to_classification_page("squadre", querystring23)

    # Compute scores before the first answer submission
    browser1.lock()
    browser2.lock()
    browser3.lock()
    scores1 = browser1.get_teams_score()
    scores2 = browser2.get_teams_score()
    scores3 = browser2.get_teams_score()
    assert scores1 == [70, 70, 70, 70, 70, 70, 70, 70, 70, 70]
    assert scores2 == [70, 70, 70, 70, 70, 70, 70, 70, 70, 70]
    assert scores3 == [70, 70, 70, 70, 70, 70, 70, 70, 70, 70]
    browser1.unlock()
    browser2.unlock()
    browser3.unlock()

    # Wait until the first browser registers the first answer submission
    browser1._wait_for_classification_timer("00:05:31")

    # Ensure that the second and third browser have not registered yet the first answer submission
    timer_to_int = mathrace_interaction.time.convert_timestamp_to_number_of_seconds
    assert timer_to_int(
        browser2.find_element(selenium.webdriver.common.by.By.ID, "orologio").text) < timer_to_int("00:05:30")
    assert timer_to_int(
        browser3.find_element(selenium.webdriver.common.by.By.ID, "orologio").text) < timer_to_int("00:05:30")

    # Freeze time for the third browser (but not for the second)
    browser3.freeze_time(datetime.datetime.now(), force_classification_update=False)

    # Lock page content at the time of the first answer submission.
    # Only the first browser will see the difference in the scores.
    browser1.lock()
    browser2.lock()
    browser3.lock()
    scores1 = browser1.get_teams_score()
    scores2 = browser2.get_teams_score()
    scores3 = browser3.get_teams_score()
    assert scores1 == [70, 70, 70, 70, 115, 70, 70, 70, 70, 70]
    assert scores2 == [70, 70, 70, 70, 70, 70, 70, 70, 70, 70]
    assert scores3 == [70, 70, 70, 70, 70, 70, 70, 70, 70, 70]
    browser1.unlock()
    browser2.unlock()
    browser3.unlock()

    # Wait for the second browser to register the first answer submission as well
    browser2._wait_for_classification_timer("00:05:32")

    # Lock page content at this final time: browser 1 and 2 will see now the same scores.
    browser1.lock()
    browser2.lock()
    scores1 = browser1.get_teams_score()
    scores2 = browser2.get_teams_score()
    assert scores1 == [70, 70, 70, 70, 115, 70, 70, 70, 70, 70]
    assert scores2 == [70, 70, 70, 70, 115, 70, 70, 70, 70, 70]
    browser1.unlock()
    browser2.unlock()

    # Browser 3 instead will still see the scores before the first submission.
    browser3.lock()
    scores3 = browser3.get_teams_score()
    assert scores3 == [70, 70, 70, 70, 70, 70, 70, 70, 70, 70]
    browser3.unlock()

    # Time needs to be unfrozen for the third browser to see the updated scores.
    browser3.unfreeze_time(force_classification_update=False)
    browser3._wait_for_classification_timer("00:05:32")
    browser3.lock()
    scores3 = browser3.get_teams_score()
    assert scores3 == [70, 70, 70, 70, 115, 70, 70, 70, 70, 70]
    browser3.unlock()

    browser1.quit()
    browser2.quit()
    browser3.quit()


def test_classification_browser_get_teams_position_integration(  # type: ignore[no-any-unimported]
    live_server: pytest_django.live_server_helper.LiveServer, simple_turing_race: engine.models.Gara,
    any_user: engine.models.User
) -> None:
    """Test mathrace_interaction.network.TuringClassificationSelenium.get_teams_position."""
    browser = Browser(live_server, simple_turing_race.pk)
    browser.login(any_user)
    browser.go_to_classification_page("squadre", {})
    browser.lock()
    positions = browser.get_teams_position()
    assert positions == [5, 1, 10, 6, 2, 8, 4, 9, 3, 7]
    browser.quit()


@pytest.mark.parametrize("race_time", ["00:06:00", "360"])
def test_classification_browser_get_teams_position_integration_non_default_race_time(  # type: ignore[no-any-unimported]
    live_server: pytest_django.live_server_helper.LiveServer, simple_turing_race: engine.models.Gara,
    admin_user: engine.models.User, race_time: str
) -> None:
    """Test team score computation with non default race time."""
    simple_turing_race.admin = admin_user
    simple_turing_race.save()
    browser = Browser(live_server, simple_turing_race.pk)
    browser.login(admin_user)
    browser.go_to_classification_page("squadre", {"race_time": race_time})
    browser.lock()
    positions = browser.get_teams_position()
    assert positions == [2, 3, 4, 5, 1, 10, 6, 7, 8, 9]
    browser.quit()


@pytest.mark.parametrize("query", ["score", "position"])
def test_classification_browser_get_teams_score_position_integration_wrong_classification_type(  # type: ignore[no-any-unimported]
    live_server: pytest_django.live_server_helper.LiveServer, simple_turing_race: engine.models.Gara,
    any_user: engine.models.User, query: str,
    runtime_error_contains: mathrace_interaction.typing.RuntimeErrorContainsFixtureType
) -> None:
    """Test that error is raised when trying to query for teams score/position on an unsupported classification."""
    if query == "score":
        def query_function(browser: Browser) -> list[int]:
            """Get the score of the teams in the race."""
            return browser.get_teams_score()
    else:
        assert query == "position"

        def query_function(browser: Browser) -> list[int]:
            """Get the position of the teams in the race."""
            return browser.get_teams_position()

    browser = Browser(live_server, simple_turing_race.pk)
    browser.login(any_user)
    browser.go_to_classification_page("unica", {})
    browser.lock()
    runtime_error_contains(lambda: query_function(browser), "The current page is not a squadre classification")
    browser.quit()
