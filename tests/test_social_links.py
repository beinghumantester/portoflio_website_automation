import pytest
from pages.landing_page import LandingPage


@pytest.mark.links
def test_profile_picture_visible(open_home):
    page = LandingPage(open_home)
    assert page.is_visible(page.PROFILE_PICTURE)


@pytest.mark.links
def test_sidebar_name_matches(open_home):
    page = LandingPage(open_home)
    name_el = page.find(page.SIDEBAR_NAME)
    assert name_el.text.strip() == "Ujjwal Kumar Singh"


@pytest.mark.links
@pytest.mark.parametrize(
    "link_locator_name, expected_domain",
    [
        ("GITHUB_LINK", "github.com"),
        ("YOUTUBE_LINK", "youtube.com"),
        ("MOT_LINK", "ministryoftesting.com"),
        ("LINKEDIN_LINK", "linkedin.com"),
    ],
)
def test_social_link_points_to_correct_domain(open_home, link_locator_name, expected_domain):
    page = LandingPage(open_home)
    locator = getattr(page, link_locator_name)
    href = page.get_href(locator)
    assert expected_domain in href, f"Expected {expected_domain} in href, got {href}"


@pytest.mark.links
def test_email_link_uses_mailto(open_home):
    page = LandingPage(open_home)
    href = page.get_href(page.EMAIL_LINK)
    assert href == "mailto:thebeinghumantester@gmail.com"
