import pytest
from pages.landing_page import LandingPage
from pages.cv_page import CVPage


@pytest.mark.navigation
def test_cv_download_button_present_and_valid(open_home):
    nav = LandingPage(open_home)
    nav.open_tab(nav.NAV_CV)

    cv = CVPage(open_home)
    assert cv.is_visible(cv.DOWNLOAD_CV_BUTTON), "Download CV button should be visible on CV tab"

    href = cv.get_download_href()
    assert href.endswith(".pdf"), f"Expected a PDF download link, got: {href}"
