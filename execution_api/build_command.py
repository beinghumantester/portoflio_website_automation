
"""
Execution API - plays the role described in the confirmed pipeline
architecture: "accepts parameters such as lender, merchant, environment,
timestamp, etc., and then updates the command and executes it inside Docker."

This is intentionally a plain script rather than a running HTTP server -
it does the same job (turn parameters into the actual test command) without
adding a persistent process, an open port, or another Jenkins plugin
dependency to manage. If this were extended into a real always-on API later,
this function is the part that would move behind an HTTP endpoint.

Reads parameters from environment variables (set by the Jenkins "Execution
Job" stage) and writes the resulting pytest arguments to a file that the
"Run Tests" stage picks up.
"""

import os

TEST_MARKER = os.getenv("TEST_MARKER", "").strip()
OUTPUT_FILE = os.getenv("COMMAND_OUTPUT_FILE", "docker_run_args.txt")


def build_pytest_args():
    """Constructs the pytest argument string based on the requested params.
    Mirrors the "execution job -> API -> command construction" step from the
    confirmed architecture, scaled down to what this project actually needs
    (a test marker) rather than the lender/merchant/env params from the
    original transcript, which don't apply to a portfolio site.
    """
    if TEST_MARKER:
        return f"-m {TEST_MARKER}"
    return ""


def main():
    args = build_pytest_args()
    with open(OUTPUT_FILE, "w") as f:
        f.write(args)
    print(f"Execution API: constructed command args = '{args}'")
    print(f"Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()