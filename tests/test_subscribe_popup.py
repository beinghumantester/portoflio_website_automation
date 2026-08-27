import time
import pytest
from pages.landing_page import LandingPage
from pages.subscribe_modal import SubscribeModal
from utils.config import SUBSCRIBE_POPUP_DELAY_SECONDS, SUBSCRIBE_POPUP_WAIT_BUFFER

WAIT = SUBSCRIBE_POPUP_DELAY_SECONDS + SUBSCRIBE_POPUP_WAIT_BUFFER


@pytest.mark.modal
def test_subscribe_popup_appears_after_delay_on_first_visit(open_home):
    page = LandingPage(open_home)
    assert page.subscribe_modal_visible(timeout=WAIT), (
        f"Subscribe modal did not get the 'active' class within {WAIT}s of first visit"
    )


@pytest.mark.modal
def test_subscribe_popup_has_name_and_email_fields(open_home):
    page = LandingPage(open_home)
    assert page.subscribe_modal_visible(timeout=WAIT)
    modal = SubscribeModal(open_home)
    assert modal.is_visible(modal.NAME_INPUT, timeout=3)
    assert modal.is_visible(modal.EMAIL_INPUT, timeout=3)
    assert modal.is_visible(modal.SUBMIT_BUTTON, timeout=3)


@pytest.mark.modal
def test_honeypot_field_is_never_filled(open_home):
    # Regression guard: our own automation must not accidentally target the
    # honeypot input, or it would look like a bot to the anti-spam check.
    page = LandingPage(open_home)
    assert page.subscribe_modal_visible(timeout=WAIT)
    modal = SubscribeModal(open_home)
    honeypot_value = modal.find(modal.HONEYPOT_INPUT).get_attribute("value")
    assert honeypot_value == "", "Honeypot field should remain empty"


@pytest.mark.modal
@pytest.mark.xfail(
    reason=(
        "Site bug, not a test bug: the EmailOctopus widget has its own "
        "built-in auto-show timer (setTimeout(..., 10000) in the vendor's "
        "form.js) that is completely independent of and ungated by our "
        "custom newsletterAutoShown sessionStorage flag. It reopens the "
        "popup ~10s after page load regardless of whether the user already "
        "dismissed it. Fix belongs in the EmailOctopus popup's own "
        "'auto-open' setting, not in this test suite."
    ),
    strict=True,
)
def test_subscribe_popup_closes_and_does_not_reappear(open_home):
    page = LandingPage(open_home)
    assert page.subscribe_modal_visible(timeout=WAIT)

    modal = SubscribeModal(open_home)
    modal.close()
    assert page.subscribe_modal_absent(timeout=5), "Modal should lose the 'active' class immediately on close"

    # The site's auto-popup only fires once per session (gated by a
    # sessionStorage flag set the moment it first auto-triggers, regardless
    # of whether it's later closed). Waiting out the same delay window again
    # confirms it doesn't come back on its own for the rest of the visit.
    time.sleep(WAIT)
    assert page.subscribe_modal_absent(timeout=2), (
        "Modal reappeared on its own - the auto-trigger should only fire once per session"
    )


@pytest.mark.modal
def test_subscribe_cta_still_opens_modal_manually_after_auto_dismiss(open_home):
    # Important distinction confirmed from the site's script: the
    # sessionStorage flag only blocks the *automatic* 5s popup from firing
    # again. It does NOT disable the Subscribe button in the nav - that
    # should keep working for manual clicks regardless.
    page = LandingPage(open_home)
    assert page.subscribe_modal_visible(timeout=WAIT)
    SubscribeModal(open_home).close()
    assert page.subscribe_modal_absent(timeout=5)

    page.open_subscribe_modal()
    assert page.subscribe_modal_visible(timeout=5), (
        "Manually clicking Subscribe should still open the modal after the auto-popup was dismissed"
    )


@pytest.mark.modal
@pytest.mark.xfail(
    reason=(
        "Same root cause as test_subscribe_popup_closes_and_does_not_reappear: "
        "the EmailOctopus widget's own ungated 10s auto-show timer fires "
        "independently of our sessionStorage gate and reopens the popup. "
        "Site-side fix needed in the widget's own settings, not this test."
    ),
    strict=True,
)
def test_subscribe_popup_does_not_auto_trigger_again_after_reload(open_home):
    # Confirms the sessionStorage gate survives a real page reload, not just
    # in-memory state within the same DOM. Relies on Astro firing its
    # "astro:page-load" event again after a hard refresh, which the site's
    # script listens for - worth a second look if this test is ever flaky.
    page = LandingPage(open_home)
    assert page.subscribe_modal_visible(timeout=WAIT)
    SubscribeModal(open_home).close()

    open_home.refresh()
    time.sleep(WAIT)
    assert page.subscribe_modal_absent(timeout=2), (
        "Modal auto-triggered again after reload - sessionStorage flag may not be persisting as expected"
    )
