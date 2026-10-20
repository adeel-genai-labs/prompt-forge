"""Scan the whole git history for leaked secrets.

Two checks, and no secret is ever printed in full:
1. Your real values from .env (keys, tokens, secrets) must not appear anywhere in git history.
2. Common secret formats (Groq, Anthropic, OpenAI, GitHub, AWS, private keys) must not appear either.

Run from the project root:  python scripts/check_secrets.py
"""

import re
import subprocess
import sys

from dotenv import dotenv_values

PATTERNS = {
    "Groq key": r"gsk_[A-Za-z0-9]{20,}",
    "Anthropic key": r"sk-ant-[A-Za-z0-9_\-]{20,}",
    "OpenAI-style key": r"sk-(?:proj-)?[A-Za-z0-9]{32,}",
    "GitHub token": r"(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})",
    "AWS access key": r"AKIA[0-9A-Z]{16}",
    "Private key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
}

SECRET_WORDS = ("KEY", "TOKEN", "SECRET", "PASSWORD")


def mask(value: str) -> str:
    """Show only the first 4 characters."""
    return value[:4] + "***"


def git_history() -> str:
    """Every change in every commit, branch and tag."""
    result = subprocess.run(
        ["git", "log", "-p", "--all"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore",
    )
    return result.stdout


def real_secrets() -> list[str]:
    """Real secret values from .env, skipping empty values and placeholders."""
    values = dotenv_values(".env")
    return [
        value for name, value in values.items()
        if value
        and any(word in name.upper() for word in SECRET_WORDS)
        and "your-" not in value
        and len(value) >= 12
    ]


def main() -> int:
    history = git_history()
    if not history:
        print("Could not read git history. Run this from the project folder.")
        return 2

    problems = 0

    secrets = real_secrets()
    for value in secrets:
        if value in history:
            print(f"LEAK: a value from .env ({mask(value)}) appears in git history")
            problems += 1
    print(f"Check 1: compared {len(secrets)} real secret value(s) from .env with git history.")

    for label, pattern in PATTERNS.items():
        found = set(re.findall(pattern, history))
        for match in found:
            print(f"WARNING: possible {label} in git history: {mask(match)}")
            problems += 1
    print("Check 2: scanned git history for common secret formats.")

    if problems:
        print(f"\n{problems} problem(s) found. Do NOT post yet: revoke the key, then ask for help cleaning history.")
        return 1
    print("\nClean: no secrets found in git history.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
