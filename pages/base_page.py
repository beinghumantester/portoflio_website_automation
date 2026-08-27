from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BasePage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def click(self, locator):
        el = self.wait.until(EC.element_to_be_clickable(locator))
        el.click()
        return el

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

    def wait_for_url_contains(self, fragment, timeout=10):
        try:
            WebDriverWait(self.driver, timeout).until(EC.url_contains(fragment))
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

    def title(self):
        return self.driver.title
