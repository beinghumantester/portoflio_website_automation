from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException, NoSuchElementException

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
        try:
            el = self.wait.until(EC.element_to_be_clickable(locator))
        except TimeoutException:
            self._open_dropdown_for(locator)
            el = self.wait.until(EC.element_to_be_clickable(locator))
        return self._click_dismissing_popup(
            el, lambda: self.wait.until(EC.element_to_be_clickable(locator))
        )

    def _click_dismissing_popup(self, el, refetch):
        """Click el, retrying once (via refetch) if the EmailOctopus popup
        happened to pop up over it and intercept the click."""
        try:
            el.click()
        except ElementClickInterceptedException:
            self._dismiss_blocking_popup_if_present()
            el = refetch()
            el.click()
        return el

    def _dismiss_blocking_popup_if_present(self):
        try:
            close_btn = self.driver.find_element(*_BLOCKING_POPUP_CLOSE_BUTTON)
            if close_btn.is_displayed():
                close_btn.click()
        except Exception:
            pass

    def _open_dropdown_for(self, locator):
        """Some nav links (Publications, Blogs, AI In Testing, TIL) live inside
        <details class="nav-dropdown"> menus and are only visible/clickable
        once their <summary> trigger has been clicked. If the plain
        element_to_be_clickable wait timed out, check whether the target sits
        inside a closed dropdown and open it before retrying.
        """
        try:
            target = self.driver.find_element(*locator)
            details = target.find_element(By.XPATH, "ancestor::details[1]")
        except NoSuchElementException:
            return
        if details.get_attribute("open") is None:
            summary_locator = (By.CSS_SELECTOR, "summary")
            summary = details.find_element(*summary_locator)
            self._click_dismissing_popup(
                summary, lambda: details.find_element(*summary_locator)
            )
            WebDriverWait(self.driver, 5).until(
                lambda d: details.get_attribute("open") is not None
            )

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