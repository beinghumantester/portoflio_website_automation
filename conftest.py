import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from utils.config import HEADLESS, BASE_URL


@pytest.fixture(scope="session")
def driver():
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
        # No real screen to maximize onto in headless mode, so fall back
        # to a fixed, generous viewport instead.
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")

    # Inside Docker, CHROME_BIN and CHROMEDRIVER_PATH point at the system
    # Chromium/chromedriver installed in the image - no need to download
    # anything, and no network egress required at test-run time.
    # Locally (outside Docker), these env vars won't be set, so we fall
    # back to webdriver-manager, which auto-downloads a matching driver.
    chrome_bin = os.getenv("CHROME_BIN")
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH")

    if chrome_bin:
        options.binary_location = chrome_bin

    if chromedriver_path:
        service = Service(chromedriver_path)
    else:
        service = Service(ChromeDriverManager().install())

    drv = webdriver.Chrome(service=service, options=options)
    drv.implicitly_wait(5)

    yield drv

    drv.quit()


@pytest.fixture
def open_home(driver):
    """Loads the portfolio homepage fresh, so each test starts from a clean slate.

    The browser itself is session-scoped (one Chrome instance for the whole
    run, instead of paying startup/teardown cost per test), but the
    subscribe-popup tests depend on genuine "first visit" state - the
    sessionStorage auto-show flag and the EmailOctopus widget's own
    localStorage-backed frequency cap. Sharing a profile across tests would
    otherwise leak that state between tests and make results depend on
    execution order. So every test clears cookies + local/session storage
    and reloads before it starts, to reproduce a true first visit each time.
    """
    driver.get(BASE_URL)
    driver.delete_all_cookies()
    driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
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
