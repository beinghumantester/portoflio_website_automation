from selenium.webdriver.common.by import By
from pages.base_page import BasePage


class SubscribeModal(BasePage):
    FORM = (By.CSS_SELECTOR, "form.emailoctopus-form")
    NAME_INPUT = (By.ID, "field_1")
    EMAIL_INPUT = (By.ID, "field_0")
    SUBMIT_BUTTON = (By.CSS_SELECTOR, "form.emailoctopus-form input[type='submit']")
    CLOSE_BUTTON = (By.CSS_SELECTOR, "button.close[aria-label='Close']")

    # Honeypot anti-spam field - present in the real HTML. Automation must
    # NEVER fill this in (that's the whole point of a honeypot: a bot fills
    # every field, a human doesn't see this one).
    HONEYPOT_INPUT = (By.CSS_SELECTOR, "input[name^='hpc4b27b6e']")

    def fill_name(self, name):
        self.find(self.NAME_INPUT).send_keys(name)

    def fill_email(self, email):
        self.find(self.EMAIL_INPUT).send_keys(email)

    def submit(self):
        # NOTE: the real form has an invisible reCAPTCHA
        # (data-recaptcha-widget-id="100000"). A genuine end-to-end submit
        # test will likely be blocked by reCAPTCHA in headless/CI runs -
        # this method is provided for completeness but isn't currently
        # exercised by a test that expects a success state.
        self.click(self.SUBMIT_BUTTON)

    def close(self):
        self.click(self.CLOSE_BUTTON)
