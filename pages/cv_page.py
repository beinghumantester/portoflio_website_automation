from selenium.webdriver.common.by import By
from pages.base_page import BasePage


class CVPage(BasePage):
    # The real /cv page has no data-testid - the download button is a plain
    # <a href="/_astro/....pdf" download="..."> in the page header. Matched
    # on the "download" attribute + .pdf href since the hashed filename
    # changes on every build.
    DOWNLOAD_CV_BUTTON = (By.CSS_SELECTOR, "a[download][href$='.pdf']")

    def get_download_href(self):
        return self.get_attribute(self.DOWNLOAD_CV_BUTTON, "href")

    def click_download(self):
        self.click(self.DOWNLOAD_CV_BUTTON)
