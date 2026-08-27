from selenium.webdriver.common.by import By
from pages.base_page import BasePage


class LandingPage(BasePage):
    # --- Top nav tabs (real hrefs, from /) ---
    NAV_ABOUT_ME = (By.CSS_SELECTOR, "a.nav-link[href='/']")
    NAV_PUBLICATIONS = (By.CSS_SELECTOR, "a.nav-link[href='/publications']")
    NAV_BLOGS = (By.CSS_SELECTOR, "a.nav-link[href='/posts']")
    NAV_SPEAKING = (By.CSS_SELECTOR, "a.nav-link[href='/talks']")
    NAV_PLAYGROUND = (By.CSS_SELECTOR, "a.nav-link[href='/projects']")
    NAV_AI_IN_TESTING = (By.CSS_SELECTOR, "a.nav-link[href='/ai-in-testing']")
    NAV_CV = (By.CSS_SELECTOR, "a.nav-link[href='/cv']")
    NAV_TWIL = (By.CSS_SELECTOR, "a.nav-link[href='/twil']")

    # --- Left sidebar ---
    PROFILE_PICTURE = (By.CSS_SELECTOR, "img.sidebar-avatar")
    SIDEBAR_NAME = (By.CSS_SELECTOR, "h1.sidebar-name")
    GITHUB_LINK = (By.CSS_SELECTOR, "a.social-link[href*='github.com']")
    EMAIL_LINK = (By.CSS_SELECTOR, "a.social-link[href^='mailto:']")
    LINKEDIN_LINK = (By.CSS_SELECTOR, "a.social-link[href*='linkedin.com']")
    YOUTUBE_LINK = (By.CSS_SELECTOR, "a.social-link[href*='youtube.com']")
    MOT_LINK = (By.CSS_SELECTOR, "a.social-link[href*='ministryoftesting.com']")

    # --- Subscribe ---
    SUBSCRIBE_CTA = (By.CSS_SELECTOR, "button.nav-link-btn[data-eo-form-toggle-id]")

    # The modal wrapper. It toggles visibility via the "active" class plus
    # a CSS opacity transition - it's always in the DOM and always has a
    # size (position:fixed; inset:0), so a plain visibility check would
    # report it as "visible" even when closed. Must check the class instead.
    SUBSCRIBE_MODAL = (
        By.CSS_SELECTOR,
        "div.modal-container[data-form='e52035a6-9bad-11f1-a5c8-07656c2bb054']",
    )

    def open_tab(self, locator):
        self.click(locator)

    def get_href(self, locator):
        return self.get_attribute(locator, "href")

    def is_active_tab(self, locator):
        return "active" in self.get_attribute(locator, "class")

    def open_subscribe_modal(self):
        self.click(self.SUBSCRIBE_CTA)

    def subscribe_modal_visible(self, timeout=10):
        try:
            return self.wait_for_class(self.SUBSCRIBE_MODAL, "active", present=True, timeout=timeout)
        except Exception:
            return False

    def subscribe_modal_absent(self, timeout=5):
        try:
            return self.wait_for_class(self.SUBSCRIBE_MODAL, "active", present=False, timeout=timeout)
        except Exception:
            return False
