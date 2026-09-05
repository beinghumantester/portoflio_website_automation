"""
Sits alongside the existing nav/subscribe/CV-download suite. Deliberately
NOT a new Jenkins stage: these reuse the 'driver' fixture conftest.py
already provides, so they ride the existing JUnit -> Allure -> HTML/email
pipeline with zero Jenkinsfile changes.

Severity philosophy matches the Trivy stage: report everything, but only
hard-fail on the tier that actually matters (critical/serious a11y
violations) - same as filtering Trivy to CRITICAL,HIGH and leaving the
rest visible-but-non-blocking. Performance/links/headers are pure
`requests` calls, no driver needed.

NOTE: these currently test whatever BASE_URL points at (production by
default) - there is no PR-specific preview yet. That would require the
website's own separate repo to be checked out and built inside this
pipeline, which is a bigger, separate piece of work, not part of this.

STRUCTURED OUTPUT: every test also writes its findings into SCAN_RESULTS,
which gets dumped to reports/health_scan.json at the end of the session
(see _write_scan_report fixture below), regardless of pass/fail. This is
the bridge to eventually feeding scan results to an AI agent - pytest's
own pass/fail output isn't structured enough for that (a violation's
`id`, `impact`, `helpUrl`, and affected-node count aren't recoverable
from a failure message alone). This file writes the report; nothing yet
reads it - that's a deliberately separate, later piece of work.

Since reports/** is already archived by the Jenkinsfile's
`archiveArtifacts artifacts: 'reports/**'`, this JSON is automatically
picked up as a build artifact with zero Jenkinsfile changes, same as
the HTML/Allure reports.
"""
import os
import re
import json
from pathlib import Path
from datetime import datetime, timezone
import requests
import pytest
from urllib.parse import urljoin, urlparse

BASE_URL = os.environ.get("BASE_URL", "https://beinghumantester.com")

# Key pages worth an accessibility pass. Kept short and explicit rather
# than crawling everything, same spirit as the TEST_MARKER subset option.
A11Y_PAGES = ["/", "/projects", "/posts", "/talks", "/publications"]

# Collected throughout the session, written out once at the end. Keyed by
# page (not a plain list) specifically so a pytest-rerunfailures retry
# overwrites that page's entry instead of duplicating it - confirmed
# necessary in practice, since these tests have actually been rerun by
# that plugin in real builds.
SCAN_RESULTS = {
    "scanned_at": None,
    "base_url": BASE_URL,
    "accessibility": {},   # path -> list of violation dicts
    "broken_links": [],
    "security_headers": {"missing": []},
    "performance": {},
}


@pytest.fixture(scope="session", autouse=True)
def _write_scan_report():
    """Writes SCAN_RESULTS to reports/health_scan.json once the whole
    session finishes, whether tests passed or failed. try/finally so a
    partial report still gets written even if something errors out
    mid-session, rather than losing everything collected so far."""
    SCAN_RESULTS["scanned_at"] = datetime.now(timezone.utc).isoformat()
    try:
        yield
    finally:
        Path("reports").mkdir(exist_ok=True)
        with open("reports/health_scan.json", "w") as f:
            json.dump(SCAN_RESULTS, f, indent=2)


# ---------------------------------------------------------------------
# Accessibility - reuses the existing Grid-connected driver fixture
# ---------------------------------------------------------------------

@pytest.mark.parametrize("path", A11Y_PAGES)
def test_accessibility(driver, path):
    """Requires selenium-axe-python (not axe-selenium-python, which has
    no tagged releases since 2018 and predates modern axe-core)."""
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

    # Every violation recorded, not just the blocking ones - an AI acting
    # on this later needs the full picture (a "minor" advisory today is
    # still a real, fixable finding), not just what failed the build.
    SCAN_RESULTS["accessibility"][path] = [
        {
            "id": v.get("id"),
            "impact": v.get("impact"),
            "description": v.get("description"),
            "help": v.get("help"),
            "helpUrl": v.get("helpUrl"),
            "nodes_affected": len(v.get("nodes", [])),
        }
        for v in violations
    ]

    assert not blocking, (
        f"{path}: {len(blocking)} critical/serious accessibility "
        f"violation(s): {[v['id'] for v in blocking]}"
    )


# ---------------------------------------------------------------------
# Broken internal links - plain requests, no driver/Grid needed
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
    # non-http(s) scheme - landing a link this site's own
    # test_social_links.py already confirms is fine in the "broken" list.
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

    SCAN_RESULTS["broken_links"] = [
        {"url": link, "status": status} for link, status in broken
    ]

    assert not broken, f"{len(broken)} broken internal link(s): {broken}"


# ---------------------------------------------------------------------
# Security headers - advisory only for now, matching Trivy's
# exit-code-0-first-rollout philosophy: report, don't block, until
# there's a baseline for what's reasonable on a static, GitHub-Pages-
# hosted personal site, where some of these are the host's call, not
# this repo's, to set.
# ---------------------------------------------------------------------

def test_security_headers_reported():
    expected = ["content-security-policy", "strict-transport-security",
                "x-content-type-options", "referrer-policy"]
    headers = {k.lower(): v for k, v in requests.get(BASE_URL, timeout=15).headers.items()}
    missing = [h for h in expected if h not in headers]
    if missing:
        print(f"[security headers advisory, non-blocking] missing: {missing}")

    SCAN_RESULTS["security_headers"]["missing"] = missing
    # Deliberately no assert - see docstring above.


# ---------------------------------------------------------------------
# Performance/SEO score via PageSpeed Insights - also advisory-only,
# same reason: no established baseline yet for this site.
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
        SCAN_RESULTS["performance"] = scores
    except Exception as e:
        pytest.skip(f"PageSpeed Insights unavailable this run: {e}")