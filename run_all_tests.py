"""
Single entry point to run every test file together, in one go, in a
fixed order - instead of calling pytest separately per file.

Usage:
    python run_all_tests.py

This is a thin wrapper around pytest.main() - it doesn't reimplement
test discovery, it just gives you one file to run and one place to
control ordering, shared flags, and exit-code handling.
"""

import sys
import pytest

# Order matters here: cheapest/fastest checks first so a broken build
# fails fast, before burning time on the popup tests (which have a
# built-in ~5-10s wait each).
TEST_ORDER = [
    "tests/test_navigation.py",
    "tests/test_social_links.py",
    "tests/test_cv_download.py",
    "tests/test_subscribe_popup.py",
    "tests/test_health_and_quality.py",
]


def main():
    args = [
        *TEST_ORDER,
        "-v",
    ]
    # NOTE: --html/--self-contained-html aren't repeated here - pytest.ini's
    # addopts already sets them, and pytest errors on duplicate flags.

    # Pass through any extra args, e.g.:
    #   python run_all_tests.py -m navigation
    #   python run_all_tests.py -k "cv"
    args.extend(sys.argv[1:])

    exit_code = pytest.main(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()