"""
New pytest tests, meant to sit alongside the existing nav/subscribe/
CV-download suite. Deliberately NOT a new Jenkins stage: these reuse the
'driver' fixture your conftest.py already provides (parametrized by
BROWSER, connected to the Selenium Grid hub), so they ride the existing
JUnit -> Allure -> HTML-email pipeline with zero Jenkinsfile changes.

Adjust the fixture import/name below to match your actual conftest.py --
written against the standard pattern (a session- or function-scoped
`driver` fixture yielding a connected webdriver.Remote), but I haven't
seen your real conftest so the fixture name/scope may need a tweak.

Severity philosophy matches your own Trivy stage: report everything, but
only hard-fail on the tier that actually matters (critical/serious a11y
violations), same as you filter Trivy to CRITICAL,HIGH and leave the rest
as visible-but-non-blocking. Performance/links/headers are pure `requests`
calls -- no driver needed, so they'll run even if BROWSER/Grid setup ever
changes.
"""
import os
import re
import requests
import pytest
from urllib.parse import urljoin, urlparse

BASE_URL = os.environ.get("BASE_URL", "https://beinghumantester.com")

# Key pages worth an accessibility pass -- adjust to your real route list
# (src/pages/** in the Astro repo). Kept short and explicit rather than
# crawling everything, same spirit as your TEST_MARKER subset option.
A11Y_PAGES = ["/", "/projects", "/posts", "/talks", "/publications"]


# ---------------------------------------------------------------------
# Accessibility -- reuses the existing Grid-connected driver fixture
# ---------------------------------------------------------------------

@pytest.mark.parametrize("path", A11Y_PAGES)
def test_accessibility(driver, path):
    """Requires selenium-axe-python (NOT axe-selenium-python, which has no
    tagged releases and predates modern axe-core): pip install selenium-axe-python
    https://github.com/bandophahita/selenium-axe-python -- last released
    2.2.0 (Feb 2025), requires selenium>=4.7.0 (matches your 4.27.1),
    bundles axe-core 4.9.1."""
    from selenium_axe_python import Axe

    driver.get(urljoin(BASE_URL, path))
    axe = Axe(driver)
    axe.inject()
    results = axe.run()
    violations = results.get("violations", [])

    blocking = [v for v in violations if v.get("impact") in ("critical", "serious")]
    advisory = [v for v in violations if v.get("impact") in ("moderate", "minor")]

    if advisory:
        print(f"[a11y advisory, non-blocking] {path}: "
              f"{[v['id'] for v in advisory]}")

    assert not blocking, (
        f"{path}: {len(blocking)} critical/serious accessibility "
        f"violation(s): {[v['id'] for v in blocking]}"
    )


# ---------------------------------------------------------------------
# Broken internal links -- plain requests, no driver/Grid needed
# ---------------------------------------------------------------------

NON_HTTP_SCHEMES = ("mailto:", "tel:", "javascript:", "#")


def test_no_broken_internal_links():
    resp = requests.get(BASE_URL, timeout=15)
    resp.raise_for_status()
    domain = urlparse(BASE_URL).netloc

    hrefs = set(re.findall(r'href=["\']([^"\']+)["\']', resp.text))
    # Excluded before the netloc check, not after: a bare `mailto:` has an
    # empty netloc too, so it would otherwise match the internal-link
    # filter below and get handed to requests.head(), which throws on a
    # non-http(s) scheme -- landing a link you already know is fine (your
    # own test_social_links.py exercises it) in the "broken" list. Caught
    # against this exact site's markup, not hypothetically.
    hrefs = {h for h in hrefs if not h.startswith(NON_HTTP_SCHEMES)}
    internal = {
        urljoin(BASE_URL, h) for h in hrefs
        if urlparse(urljoin(BASE_URL, h)).netloc in (domain, "")
    }

    broken = []
    for link in internal:
        try:
            status = requests.head(link, timeout=10, allow_redirects=True).status_code
            if status >= 400:
                broken.append((link, status))
        except requests.RequestException as e:
            broken.append((link, str(e)))

    assert not broken, f"{len(broken)} broken internal link(s): {broken}"


# ---------------------------------------------------------------------
# Security headers -- advisory only for now (matches Trivy's
# exit-code-0-first-rollout philosophy: report, don't block, until
# there's a baseline for what's actually reasonable on a static
# GitHub-Pages-hosted personal site, where some of these are the host's
# call, not yours, to set).
# ---------------------------------------------------------------------

def test_security_headers_reported():
    expected = ["content-security-policy", "strict-transport-security",
                "x-content-type-options", "referrer-policy"]
    headers = {k.lower(): v for k, v in requests.get(BASE_URL, timeout=15).headers.items()}
    missing = [h for h in expected if h not in headers]
    if missing:
        print(f"[security headers advisory, non-blocking] missing: {missing}")
    # Deliberately no assert -- see docstring above.


# ---------------------------------------------------------------------
# Performance/SEO score via PageSpeed Insights -- also advisory-only
# for the same reason: no established baseline yet for this site.
# ---------------------------------------------------------------------

def test_performance_score_reported():
    try:
        resp = requests.get(
            "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
            params={"url": BASE_URL, "category": ["PERFORMANCE", "SEO", "ACCESSIBILITY"]},
            timeout=60,
        )
        resp.raise_for_status()
        categories = resp.json()["lighthouseResult"]["categories"]
        scores = {k: round(v["score"] * 100) for k, v in categories.items()}
        print(f"[performance] {scores}")
    except Exception as e:
        pytest.skip(f"PageSpeed Insights unavailable this run: {e}")