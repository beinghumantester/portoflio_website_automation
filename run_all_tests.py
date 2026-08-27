"""
Single entry point to run every test file together, in one go, in a
fixed order - instead of calling pytest separately per file.

Usage:
    python run_all_tests.py
"""
import sys
from pathlib import Path
import pytest

TESTS_DIR = Path(__file__).resolve().parent / "tests"

TEST_ORDER = [
    str(TESTS_DIR / "test_navigation.py"),
    str(TESTS_DIR / "test_social_links.py"),
    str(TESTS_DIR / "test_cv_download.py"),
    str(TESTS_DIR / "test_subscribe_popup.py"),
]

def main():
    args = [*TEST_ORDER, "-v"]
    args.extend(sys.argv[1:])
    exit_code = pytest.main(args)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
