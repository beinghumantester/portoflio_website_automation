import os
import time

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.chrome import ChromeDriverManager

from utils.config import HEADLESS, BASE_URL

# If set, tests connect to a remote Selenium Grid (hub + browser nodes,
# see docker-compose.yml) instead of launching a browser locally.
GRID_URL = os.getenv("SELENIUM_REMOTE_URL")
BROWSER = os.getenv("BROWSER", "chrome").lower()


def _build_chrome_options():
    options = ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1440,900")
    return options


def _build_firefox_options():
    options = FirefoxOptions()
    if HEADLESS:
        options.add_argument("-headless")
    options.add_argument("--width=1440")
    options.add_argument("--height=900")
    return options


@pytest.fixture
def driver():
    if GRID_URL:
        # Grid mode: the browser runs in a separate node container (see
        # docker-compose.yml). Retry a few times since the hub/node
        # containers may still be finishing startup when tests begin.
        options = _build_firefox_options() if BROWSER == "firefox" else _build_chrome_options()
        drv = None
        last_error = None
        for _ in range(5):
            try:
                drv = webdriver.Remote(command_executor=GRID_URL, options=options)
                break
            except Exception as e:
                last_error = e
                time.sleep(3)
        if drv is None:
            raise RuntimeError(f"Could not connect to Selenium Grid at {GRID_URL}: {last_error}")
    else:
        # Local mode (no grid) - launches Chrome directly. Used for plain
        # local dev, or the earlier non-Grid Docker setup if CHROME_BIN /
        # CHROMEDRIVER_PATH are set inside the image.
        options = _build_chrome_options()
        chrome_bin = os.getenv("CHROME_BIN")
        chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
        if chrome_bin:
            options.binary_location = chrome_bin
        service = ChromeService(chromedriver_path) if chromedriver_path else ChromeService(ChromeDriverManager().install())
        drv = webdriver.Chrome(service=service, options=options)

    drv.implicitly_wait(5)
    yield drv
    drv.quit()


@pytest.fixture
def open_home(driver):
    """Loads the portfolio homepage fresh, so each test starts from a clean slate.
    Important for the subscribe-popup tests, which depend on 'first visit' state.
    """
    driver.get(BASE_URL)
    return driver


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Attach a screenshot to the HTML report whenever a test fails."""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        driver = item.funcargs.get("driver") or item.funcargs.get("open_home")
        if driver:
            os.makedirs("reports/screenshots", exist_ok=True)
            screenshot_path = f"reports/screenshots/{item.name}.png"
            driver.save_screenshot(screenshot_path)