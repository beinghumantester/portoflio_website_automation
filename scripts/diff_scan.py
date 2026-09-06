"""
Compares the current health_scan.json against the previous scan (if one
exists) to determine what's actually NEW since last time. This is the
piece that decides whether anything is even worth surfacing to a human
or an agent - without it, every run would re-report the same known,
already-seen findings from scratch, forever.

A finding's identity is (page, violation_id) for accessibility, and just
the URL for broken links - deliberately NOT including node counts or
exact HTML snippets, since those can shift slightly (e.g. one more
paragraph added to a page) without representing a genuinely new problem.
"""
import json
import os
import sys
from pathlib import Path


def load_scan(path):
    if not Path(path).exists():
        return None
    with open(path) as f:
        return json.load(f)


def extract_accessibility_keys(scan):
    """Returns the set of (page, violation_id) pairs present in a scan -
    the identity of each finding, independent of node-level detail."""
    keys = set()
    for page, violations in scan.get("accessibility", {}).items():
        for v in violations:
            keys.add((page, v.get("id")))
    return keys


def diff_scans(previous, current):
    prev_a11y = extract_accessibility_keys(previous) if previous else set()
    curr_a11y = extract_accessibility_keys(current)

    prev_links = {link["url"] for link in (previous.get("broken_links", []) if previous else [])}
    curr_links = {link["url"] for link in current.get("broken_links", [])}

    return {
        "new_accessibility": sorted(curr_a11y - prev_a11y),
        "resolved_accessibility": sorted(prev_a11y - curr_a11y),
        "new_broken_links": sorted(curr_links - prev_links),
        "resolved_broken_links": sorted(prev_links - curr_links),
    }


def main():
    previous_path = sys.argv[1] if len(sys.argv) > 1 else "previous_scan.json"
    current_path = sys.argv[2] if len(sys.argv) > 2 else "reports/health_scan.json"

    current = load_scan(current_path)
    if current is None:
        print(f"ERROR: current scan not found at {current_path}")
        sys.exit(1)

    previous = load_scan(previous_path)
    if previous is None:
        print("No previous scan found (first run) - all current findings are new.")

    diff = diff_scans(previous, current)

    with open("scan_diff.json", "w") as f:
        json.dump(diff, f, indent=2)

    has_new = bool(diff["new_accessibility"] or diff["new_broken_links"])

    print(f"New accessibility findings: {diff['new_accessibility']}")
    print(f"Resolved accessibility findings: {diff['resolved_accessibility']}")
    print(f"New broken links: {diff['new_broken_links']}")
    print(f"Resolved broken links: {diff['resolved_broken_links']}")

    # Modern GitHub Actions output mechanism - writes to the file GitHub
    # points GITHUB_OUTPUT at, not the deprecated ::set-output syntax.
    # Exit code stays 0 here regardless of findings - "new findings
    # exist" isn't a script error, it's a real result a later workflow
    # step should react to via this output, not via a failing step.
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"has_new_findings={'true' if has_new else 'false'}\n")


if __name__ == "__main__":
    main()