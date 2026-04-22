# Copyright (C) 2024-2026 by the Turing @ DMF authors
#
# This file is part of Turing @ DMF.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""A selenium browser that connects to a classification page on the current live turing instance."""

import datetime
import typing
import urllib.parse

import bs4
import prettytable
import requests
import selenium.common.exceptions
import selenium.webdriver
import selenium.webdriver.common.by
import selenium.webdriver.remote.webdriver
import selenium.webdriver.remote.webelement
import selenium.webdriver.support.expected_conditions as EC  # noqa: N812
import selenium.webdriver.support.ui
import tinycss2

from mathrace_interaction.time import convert_timestamp_to_number_of_seconds


class TuringClassificationSelenium:
    """
    A selenium browser that connects to a classification page on the current live turing instance.

    Parameters
    ----------
    root_url
        URL of the root of the turing website.
    race_id
        The ID of the turing race to follow.
    max_wait
        Maximum amount to wait in seconds for the requested page to load fully.

    Attributes
    ----------
    _browser
        The selenium browser that will be used to connect to the website.
    _root_url
        URL of the root of the turing website.
    _race_id
        The ID of the turing race to follow.
    _max_wait
        Maximum amount to wait in seconds for the requested page to load fully.
    _locked
        If unlocked (False), the browser is free to update the page, e.g. due to changes triggered by javascript.
        If locked (True), the web page seen by this class is frozen, and updates are not reflected in its content.
    _locked_page_source
        If locked, it contains the HTML source at time of locking.
        If unlocked, it contains None.
    _locked_page_soup
        If locked, it contains a BeautifulSoup object to parse the HTML source at time of locking.
        If unlocked, it contains None.
    """

    def __init__(self, root_url: str, race_id: int, max_wait: float) -> None:
        service = selenium.webdriver.ChromeService(executable_path="/usr/bin/chromedriver")
        options = selenium.webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        self._browser = selenium.webdriver.Chrome(service=service, options=options)
        self._root_url = root_url
        self._race_id = race_id
        self._max_wait = max_wait
        self._locked = False
        self._locked_page_source: str | None = None
        self._locked_page_soup: bs4.BeautifulSoup | None = None

    def lock(self) -> None:
        """Lock the browser on the current state of the web page."""
        assert not self._locked
        self._locked_page_source = self._browser.page_source
        self._locked_page_soup = bs4.BeautifulSoup(self._locked_page_source, "html.parser")
        self._locked = True

    def unlock(self) -> None:
        """Unlock the browser and follow new updates to the web page."""
        assert self._locked
        self._locked_page_source = None
        self._locked_page_soup = None
        self._locked = False

    @property
    def page_source(self) -> str:
        """Return the HTML source code of the current page."""
        if self._locked:
            assert self._locked_page_source is not None
            return self._locked_page_source
        else:
            return self._browser.page_source

    @property
    def page_soup(self) -> bs4.BeautifulSoup:
        """Return the HTML source code of the current page parse by BeautifulSoup."""
        if self._locked:
            assert self._locked_page_soup is not None
            return self._locked_page_soup
        else:
            return bs4.BeautifulSoup(self._browser.page_source, "html.parser")

    def ensure_locked(self) -> None:
        """Ensure that the browser is locked and, if not, raise an error."""
        if not self._locked:
            raise RuntimeError("Did you forget to lock the browser?")

    def ensure_unlocked(self) -> None:
        """Ensure that the browser is unlocked and, if not, raise an error."""
        if self._locked:
            raise RuntimeError("Did you forget to unlock the browser?")

    def get(self, url: str) -> None:
        """Load a web page in the current browser session."""
        self.ensure_unlocked()
        self._browser.get(url)

    def find_element(self, by: str, value: str) -> selenium.webdriver.remote.webelement.WebElement:
        """Find an element given a By strategy and locator."""
        self.ensure_unlocked()
        return self._browser.find_element(by, value)

    def find_elements(self, by: str, value: str) -> list[selenium.webdriver.remote.webelement.WebElement]:
        """Find an elements given a By strategy and locator."""
        self.ensure_unlocked()
        return self._browser.find_elements(by, value)

    def _wait_for_element(self, by: str, value: str) -> None:
        """Wait for an element to be present on the page."""
        self.ensure_unlocked()
        selenium.webdriver.support.wait.WebDriverWait(self._browser, self._max_wait).until(
            EC.presence_of_element_located((by, value)))

    def _wait_for_classification_timer(self, value: str) -> None:
        """Wait for classification timer to be greater than or equal to a certain value."""
        self.ensure_unlocked()

        def timer_above_value(
            locator: tuple[str, str]
        ) -> typing.Callable[[selenium.webdriver.remote.webdriver.WebDriver], bool]:
            """Predicate used in WebDriverWait, inspired by EC.text_to_be_present_in_element."""
            value_int = convert_timestamp_to_number_of_seconds(value)

            def _predicate(driver: selenium.webdriver.remote.webdriver.WebDriver) -> bool:
                try:
                    element_text = driver.find_element(*locator).text
                    element_int = convert_timestamp_to_number_of_seconds(element_text)
                    return element_int >= value_int
                except selenium.common.exceptions.StaleElementReferenceException:  # pragma: no cover
                    return False

            return _predicate

        selenium.webdriver.support.wait.WebDriverWait(self._browser, self._max_wait).until(
            timer_above_value((selenium.webdriver.common.by.By.ID, "orologio")))

    def _wait_for_classification_computed(self) -> None:
        """Wait for classification computation."""
        self.ensure_unlocked()

        def document_updated_is_true(driver: selenium.webdriver.remote.webdriver.WebDriver) -> bool:
            try:
                return driver.execute_script(  # type: ignore[no-any-return, no-untyped-call]
                    "return document.updated;")
            except selenium.common.exceptions.StaleElementReferenceException:  # pragma: no cover
                return False

        selenium.webdriver.support.wait.WebDriverWait(self._browser, self._max_wait).until(document_updated_is_true)

    def login(self, username: str, password: str) -> None:
        """Log into the turing instance with the provided credentials."""
        self.get(urllib.parse.urljoin(self._root_url, "accounts/login"))
        # Wait for the login button to appear, and send credentials
        self._wait_for_element(selenium.webdriver.common.by.By.ID, "submit")
        self.find_element(selenium.webdriver.common.by.By.NAME, "username").send_keys(username)
        self.find_element(selenium.webdriver.common.by.By.NAME, "password").send_keys(password)
        self.find_element(selenium.webdriver.common.by.By.ID, "submit").click()
        # Successful login redirects to the home page, where there is a link to change password
        try:
            self._wait_for_element(
                selenium.webdriver.common.by.By.CSS_SELECTOR, "a[href='/accounts/password_change/']")
        except selenium.common.exceptions.TimeoutException:
            if "Inserisci nome utente e password corretti" in self.page_source:
                raise RuntimeError("Could not login with the provided credentials")
            else:  # pragma: no cover
                raise

    def go_to_classification_page(self, classification_type: str, querystring: dict[str, str]) -> None:
        """Direct the browser to visit a specific classification type."""
        querystring_joined = (
            ("?" + "&".join(f"{k}={v}" for (k, v) in querystring.items())) if len(querystring) > 0 else "")
        self.get(
            urllib.parse.urljoin(
                self._root_url, f"engine/classifica/{self._race_id}/{classification_type}{querystring_joined}"))
        # Wait for the classification to be fully computed
        try:
            self._wait_for_classification_computed()
        except selenium.common.exceptions.TimeoutException:
            if "Purtroppo non sei autorizzato ad effettuare questa azione" in self.page_source:
                raise RuntimeError("The user does not have the permissions to see this classification")
            else:
                if len(self.find_elements(selenium.webdriver.common.by.By.NAME, "username")) > 0:
                    raise RuntimeError("The user must be logged in to see this classification")
                else:  # pragma: no cover
                    raise

    def ensure_classification_type(self, classification_type: str) -> None:
        """Ensure that the page contains a specific classification type."""
        expected_url = urllib.parse.urljoin(
            self._root_url, f"engine/classifica/{self._race_id}/{classification_type}")
        if not self._browser.current_url.startswith(expected_url):
            raise RuntimeError(f"The current page is not a {classification_type} classification")

    def get_table(self) -> prettytable.PrettyTable:
        """Get the table representing the unica classification."""
        self.ensure_locked()
        assert self._locked_page_soup is not None
        self.ensure_classification_type("unica")
        table = prettytable.PrettyTable()
        # Get the headers first
        timer_elements = self._locked_page_soup.find_all("h3", id="orologio")
        assert len(timer_elements) == 1
        header1 = ["Position", "Team ID", "Team name", "Score"]
        header2 = ["", "", timer_elements[0].text, ""]
        num_questions = 0
        while True:
            question_elements = self._locked_page_soup.find_all("th", id=f"pr-{num_questions + 1}")
            if len(question_elements) == 0:
                break
            else:
                assert len(question_elements) == 1
                question_text = question_elements[0].text.strip()
                if "\n" in question_text:  # score for each question goes to a new line
                    question_number, question_score = question_text.split("\n")
                    header1.append(question_number.strip())
                    header2.append(question_score.strip())
                else:
                    header1.append(question_text)
                    header2.append("")
                num_questions += 1
        header1.append("Bonus")
        header2.append("")
        table.field_names = header1
        if not all(cell == "" for cell in header2):
            table.add_row(header2)
        # Get the table content, row by row
        team_id = 1
        while True:
            row: list[int | str] = []
            position_elements = self._locked_page_soup.find_all("th", id=f"pos-{team_id}")
            if len(position_elements) == 0:
                break
            assert len(position_elements) == 1
            row.append(int(position_elements[0].text.strip()[:-1]))  # :-1 is to drop the trailing degree symbol
            team_id_elements = self._locked_page_soup.find_all("th", id=f"num-{team_id}")
            assert len(team_id_elements) == 1
            row.append(int(team_id_elements[0].text))
            team_name_elements = self._locked_page_soup.find_all("th", id=f"nome-{team_id}")
            assert len(team_name_elements) == 1
            row.append(team_name_elements[0].text)
            team_score_elements = self._locked_page_soup.find_all("th", id=f"punt-{team_id}")
            assert len(team_score_elements) == 1
            row.append(int(team_score_elements[0].text))
            for q in [*range(1, num_questions + 1), "bonus"]:
                question_score_elements = self._locked_page_soup.find_all("td", id=f"cell-{team_id}-{q}")
                assert len(question_score_elements) == 1
                question_score = question_score_elements[0].text.strip()
                if question_score != "":
                    row.append(int(question_score))
                else:
                    row.append("")
            table.add_row(row)
            team_id += 1
        return table

    def get_teams_score(self) -> list[int]:
        """Get the score of the teams in the race."""
        self.ensure_locked()
        assert self._locked_page_soup is not None
        self.ensure_classification_type("squadre")
        team_id = 1
        scores = []
        while True:
            score_elements = self._locked_page_soup.find_all("span", id=f"label-points-{team_id}")
            if len(score_elements) == 0:
                break
            else:
                assert len(score_elements) == 1
                scores.append(int(score_elements[0].text))
                team_id += 1
        return scores

    def get_teams_position(self) -> list[int]:
        """Get the position of the teams in the race."""
        self.ensure_locked()
        assert self._locked_page_soup is not None
        self.ensure_classification_type("squadre")
        team_id = 1
        positions = []
        while True:
            position_elements = self._locked_page_soup.find_all("span", id=f"label-pos-{team_id}")
            if len(position_elements) == 0:
                break
            else:
                assert len(position_elements) == 1
                positions.append(int(position_elements[0].text[:-1]))  # :-1 is to drop the trailing degree symbol
                team_id += 1
        return positions

    def get_auxiliary_files(self) -> tuple[dict[str, str], dict[str, bytes]]:
        """Get the content of CSS and font files used in the current page."""
        self.ensure_locked()
        assert self._locked_page_soup is not None

        # Get css files first
        all_css = dict()
        all_css_directory = dict()

        for css in self._locked_page_soup.find_all("link", rel="stylesheet"):
            # Do not use the current selenium browser to fetch the css content, otherwise
            # the browser would move away from the current page. However, since css content
            # is static, simply downloading the page via the python package requests suffices.
            request_url = urllib.parse.urljoin(self._root_url, css["href"])
            response = requests.get(request_url)
            assert response.status_code == 200
            directory, filename = css["href"].rsplit("/", 1)
            assert filename not in all_css, "Cannot have two css files with the same name"
            all_css[filename] = response.text
            all_css_directory[filename] = directory

        # Next, process each css file to extract the fonts that are required there
        all_fonts = dict()

        for css_filename in all_css.keys():
            rules = tinycss2.parse_stylesheet(all_css[css_filename])
            for rule in rules:
                if rule.type == "at-rule":  # which define fonts
                    for token in rule.content:
                        if token.type == "url":
                            font_url = token.value
                            if "?" not in font_url and "#" not in font_url:
                                request_url = urllib.parse.urljoin(
                                    self._root_url, all_css_directory[css_filename] + "/" + font_url)
                                response = requests.get(request_url)
                                assert response.status_code == 200
                                font_filename = font_url.split("/")[-1]
                                assert font_filename not in all_fonts, "Cannot have two font files with the same name"
                                all_fonts[font_filename] = response.content
                                all_css[css_filename] = all_css[css_filename].replace(font_url, font_filename)

        return all_css, all_fonts

    def get_cleaned_html_source(self) -> str:
        """
        Get a cleaned HTML source code of a page of the turing instance for local download.

        The HTML code is preprocessed as follows:
            - the path of any auxiliary file should be flattened to the one returned by get_auxiliary_files.
            - any local link to the live instance is removed, since it would not be available locally.
            - any javascript is removed, since in order to be visible locally the page cannot contain
              any script that requires the live server.
        """
        self.ensure_locked()
        # Create a new soup object, because the existing one would be changed if we used it
        assert self._locked_page_source is not None
        soup = bs4.BeautifulSoup(self._locked_page_source, "html.parser")

        # Flatten css path
        for css in soup.find_all("link", rel="stylesheet"):
            css["href"] = css["href"].split("/")[-1]

        # Remove local links
        for a in soup.select("a[href]"):
            assert isinstance(a["href"], str)
            if a["href"].startswith("/"):
                del a["href"]

        # Remove <script> tags
        for script in soup.select("script"):
            script.decompose()

        # Return postprocessed page
        return str(soup)

    def freeze_time(self, current_time: datetime.datetime, force_classification_update: bool = True) -> None:
        """Freeze the race time at the specified time."""
        javascript_timestamp = int(current_time.timestamp() * 1000)
        # Overwrite the javascript timer
        self._browser.execute_script(f"""\
if (!('timer_backup' in document.client)) {{
    document.client.timer_backup = document.client.timer.now;
}}

document.client.timer.now = function mock_timer() {{
    return {javascript_timestamp};
}}""")  # type: ignore[no-untyped-call]
        if force_classification_update:
            # Force an update of the race time, and wait for the updated event to be triggered
            # in order to be sure that the classification has been updated
            self._browser.execute_script("""\
    document.client.gara.time = document.client.timer.now()
    document.updated = false;""")  # type: ignore[no-untyped-call]
            self._wait_for_classification_computed()

    def unfreeze_time(self, force_classification_update: bool = True) -> None:
        """Undo a previous freeze of the race time."""
        has_timer_backup = self._browser.execute_script(  # type: ignore[no-untyped-call]
            "return 'timer_backup' in document.client;""")
        if not has_timer_backup:
            raise RuntimeError("Did you forget to freeze the time?")
        # Restore the javascript timer
        self._browser.execute_script("""\
document.client.timer.now = document.client.timer_backup;
delete document.client.timer_backup;""")  # type: ignore[no-untyped-call]
        if force_classification_update:
            # Force an update of the race time, and wait for the updated event to be triggered
            # in order to be sure that the classification has been updated
            self._browser.execute_script("""\
    document.client.gara.time = document.client.timer.now()
    document.updated = false;""")  # type: ignore[no-untyped-call]
            self._wait_for_classification_computed()

    def quit(self) -> None:
        """Quit the underlying selenium browser."""
        self._browser.quit()
        del self._browser
        self._browser = None  # type: ignore[assignment]
