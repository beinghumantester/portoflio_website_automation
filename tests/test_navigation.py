import pytest
from pages.landing_page import LandingPage


@pytest.mark.smoke
def test_landing_page_loads(open_home):
    page = LandingPage(open_home)
    assert page.title() != "", "Page title should not be empty"


@pytest.mark.navigation
@pytest.mark.parametrize(
    "tab_locator_name, expected_href_fragment",
    [
        ("NAV_PUBLICATIONS", "/publications"),
        ("NAV_BLOGS", "/posts"),
        ("NAV_SPEAKING", "/talks"),
        ("NAV_PLAYGROUND", "/projects"),
        ("NAV_AI_IN_TESTING", "/ai-in-testing"),
        ("NAV_CV", "/cv"),
        ("NAV_TWIL", "/twil"),
    ],
)
def test_nav_tab_opens_correct_page(open_home, tab_locator_name, expected_href_fragment):
    page = LandingPage(open_home)
    locator = getattr(page, tab_locator_name)
    page.open_tab(locator)
    # Astro navigates via a client-side page transition, so the URL updates
    # ~0.5-0.6s after the click - not synchronously with it.
    assert page.wait_for_url_contains(expected_href_fragment), (
        f"URL never changed to include {expected_href_fragment!r}, "
        f"stayed at {open_home.current_url!r}"
    )


@pytest.mark.navigation
def test_about_me_is_landing_page(open_home):
    page = LandingPage(open_home)
    assert page.is_active_tab(page.NAV_ABOUT_ME), "About tab should be marked active on landing"
