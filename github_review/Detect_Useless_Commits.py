#!/usr/bin/env python3
"""
detect_useless_commits.py

Funkcja do analizy repozytorium Git w celu wykrycia commitów o małej wartości:
 - whitespace-only commits
 - comment-only commits
 - small commits
 - pomija merge commits i PR merges
 - ignoruje binarne pliki (PDF, DOC, obrazy)
 - zwraca dane jako listę słowników
"""

import subprocess
import re
import os
# ==== KONFIGURACJA ====
SMALL_CHANGE_THRESHOLD = int(os.getenv("SMALL_CHANGE_THRESHOLD", "3"))  # total lines changed (added + removed)
COMMENT_REGEX = re.compile(r'^[\+\-]\s*(#|//|/\*|\*|<!--|-->)')
MERGE_PR_REGEX = re.compile(r"^Merge (pull request|branch)", re.IGNORECASE)
BINARY_EXTENSIONS = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".png", ".jpg", ".jpeg", ".gif")
# ========================


def git(cmd):
    """Uruchamia komendę git i zwraca wynik jako string."""
    return subprocess.check_output(
        ["git"] + cmd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stderr=subprocess.DEVNULL
    )


def is_merge_commit(commit):
    parents = git(["rev-list", "--parents", "-n", "1", commit]).strip().split()
    return len(parents) > 2


def is_whitespace_only(commit):
    result = subprocess.run(
        ["git", "diff", "-w", "--quiet", f"{commit}^!", "--no-color"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def count_lines_changed(commit):
    try:
        out = git(["diff-tree", "--no-commit-id", "--numstat", "-r", commit])
    except subprocess.CalledProcessError:
        return 0
    total = 0
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            total += int(parts[0]) + int(parts[1])
    return total


def is_comment_only(commit):
    diff = git(["show", commit, "--unified=0", "--no-color"])
    lines = [l for l in diff.splitlines() if l.startswith(('+', '-'))]
    if not lines:
        return True
    return all(COMMENT_REGEX.match(l) or l.strip() in ('+', '-') for l in lines)


def is_binary_only(commit):
    try:
        files = git(["diff-tree", "--no-commit-id", "--name-only", "-r", commit]).splitlines()
    except subprocess.CalledProcessError:
        return False
    if not files:
        return False
    return all(f.lower().endswith(BINARY_EXTENSIONS) for f in files)


def get_commit_info(commit):
    info = git(["show", "-s", "--format=%an|%ad", "--date=short", commit]).strip()
    author, date = info.split("|", 1)
    return author, date


def detect_useless_commits():
    """
    Przeskanuj wszystkie commity i zwróć listę słowników:
    [
      {"sha": "abcd123", "author": "Jan", "problem": "WHITESPACE_ONLY"},
      {"sha": "efgh456", "author": "Anna", "problem": "TOO_LITTLE_CHANGES"},
    ]
    """
    commits = git(["rev-list", "--all"]).splitlines()
    results = []

    for sha in commits:
        msg = git(["log", "-1", "--pretty=%s", sha]).strip()
        author, _ = get_commit_info(sha)

        # Pomiń merge lub PR merge
        if is_merge_commit(sha) or MERGE_PR_REGEX.match(msg):
            continue

        # Pomiń binarne commity
        if is_binary_only(sha):
            continue

        lines_changed = count_lines_changed(sha)

        if is_whitespace_only(sha):
            results.append({"sha": sha, "author": author, "problem": "WHITESPACE_ONLY"})
        elif is_comment_only(sha):
            results.append({"sha": sha, "author": author, "problem": "COMMENT_ONLY"})
        elif lines_changed < SMALL_CHANGE_THRESHOLD:
            results.append({"sha": sha, "author": author, "problem": "TOO_LITTLE_CHANGES"})

    return results