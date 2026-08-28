from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException

# The EmailOctopus popup widget has its own ungated ~10s auto-show timer,
# independent of the site's custom sessionStorage-gated one (see
# tests/test_subscribe_popup.py for the documented xfail on this). That
# timer can fire mid-test and cover unrelated elements (like nav links),
# causing intercepted clicks that have nothing to do with what's actually
# being tested. This locator lets click() defensively clear it out of the
# way rather than letting it fail unrelated tests.
_BLOCKING_POPUP_CLOSE_BUTTON = (By.CSS_SELECTOR, "button.close[aria-label='Close']")


class BasePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def click(self, locator):
        el = self.wait.until(EC.element_to_be_clickable(locator))
        try:
            el.click()
        except ElementClickInterceptedException:
            self._dismiss_blocking_popup_if_present()
            el = self.wait.until(EC.element_to_be_clickable(locator))
            el.click()
        return el

    def _dismiss_blocking_popup_if_present(self):
        try:
            close_btn = self.driver.find_element(*_BLOCKING_POPUP_CLOSE_BUTTON)
            if close_btn.is_displayed():
                close_btn.click()
        except Exception:
            pass

    def find(self, locator):
        return self.wait.until(EC.presence_of_element_located(locator))

    def is_visible(self, locator, timeout=10):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(locator)
            )
            return True
        except Exception:
            return False

    def is_not_present(self, locator, timeout=5):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.invisibility_of_element_located(locator)
            )
            return True
        except Exception:
            return False

    def get_attribute(self, locator, attr):
        return self.find(locator).get_attribute(attr)

    def wait_for_class(self, locator, class_name, present=True, timeout=10):
        """Poll until an element does/doesn't have a given CSS class.
        Needed for elements that toggle visibility via a class + opacity
        transition rather than being added/removed from the DOM - plain
        visibility checks can't be trusted for those.
        """
        def condition(driver):
            try:
                el = driver.find_element(*locator)
                classes = (el.get_attribute("class") or "").split()
                has_class = class_name in classes
                return has_class if present else not has_class
            except Exception:
                return not present

        return WebDriverWait(self.driver, timeout).until(condition)

    def wait_for_url_contains(self, fragment, timeout=10):
        """Poll until the current URL contains the given fragment.
        Astro navigates via a client-side page transition, so the URL
        updates shortly after a nav click, not synchronously with it -
        checking current_url immediately after click() is a race condition.
        """
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.url_contains(fragment)
            )
        except Exception:
            return False

    def title(self):
        return self.driver.title