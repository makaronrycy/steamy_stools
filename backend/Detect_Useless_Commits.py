#!/usr/bin/env python3
"""
detect_useless_commits.py

Moduł do analizy repozytorium Git w celu wykrycia commitów
o niskiej wartości merytorycznej.

Wykrywane przypadki:
- commity zawierające wyłącznie zmiany białych znaków
- commity zawierające wyłącznie zmiany w komentarzach
- bardzo małe commity (poniżej ustalonego progu zmian)

Pomijane są:
- merge commity oraz automatyczne merge PR
- commity zmieniające wyłącznie pliki binarne

Moduł zwraca listę słowników opisujących podejrzane commity,
gotową do dalszego przetwarzania lub zapisu do bazy danych.
"""

import subprocess
import re
import os

# =====================
# KONFIGURACJA
# =====================

SMALL_CHANGE_THRESHOLD = int(os.getenv("SMALL_CHANGE_THRESHOLD", "3"))
"""
Minimalna liczba zmienionych linii (dodanych + usuniętych),
poniżej której commit uznawany jest za mało istotny.
"""

COMMENT_REGEX = re.compile(r'^[\+\-]\s*(#|//|/\*|\*|<!--|-->)')
"""
Wyrażenie regularne dopasowujące linie diffów zawierające
wyłącznie komentarze.
"""

MERGE_PR_REGEX = re.compile(r"^Merge (pull request|branch)", re.IGNORECASE)
"""
Wyrażenie regularne wykrywające automatyczne merge PR lub branchy.
"""

BINARY_EXTENSIONS = (
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".ppt", ".pptx", ".zip", ".png", ".jpg",
    ".jpeg", ".gif"
)
"""
Rozszerzenia plików uznawanych za binarne i ignorowanych w analizie.
"""

# =====================
# UTILS
# =====================

def git(cmd: list[str], cwd: str | None = None) -> str:
    """
    Uruchamia polecenie git i zwraca jego standardowe wyjście.

    Parameters
    ----------
    cmd : list[str]
        Lista argumentów przekazywanych do polecenia `git`.
    cwd : str or None
        Ścieżka do repozytorium Git.

    Returns
    -------
    str
        Wynik stdout polecenia git.
    """
    return subprocess.check_output(
        ["git"] + cmd,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stderr=subprocess.DEVNULL
    )


def is_merge_commit(commit: str, repo_path: str) -> bool:
    """
    Sprawdza, czy commit jest merge commitem.

    Commit uznawany jest za merge, jeśli posiada więcej
    niż jednego rodzica.

    Parameters
    ----------
    commit : str
        SHA commita.
    repo_path : str
        Ścieżka do repozytorium Git.

    Returns
    -------
    bool
        True jeśli commit jest merge commitem, w przeciwnym razie False.
    """
    parents = git(
        ["rev-list", "--parents", "-n", "1", commit],
        cwd=repo_path
    ).strip().split()

    return len(parents) > 2


def is_whitespace_only(commit: str, repo_path: str) -> bool:
    """
    Sprawdza, czy commit zawiera wyłącznie zmiany białych znaków.

    Wykorzystuje `git diff -w --quiet`, który ignoruje whitespace
    i zwraca kod 0, jeśli nie wykryto istotnych zmian.

    Parameters
    ----------
    commit : str
        SHA commita.
    repo_path : str
        Ścieżka do repozytorium Git.

    Returns
    -------
    bool
        True jeśli commit zmienia tylko whitespace.
    """
    result = subprocess.run(
        ["git", "diff", "-w", "--quiet", f"{commit}^!", "--no-color"],
        cwd=repo_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return result.returncode == 0


def count_lines_changed(commit: str, repo_path: str) -> int:
    """
    Zlicza łączną liczbę zmienionych linii w commicie.

    Liczone są zarówno linie dodane, jak i usunięte,
    z wyłączeniem plików binarnych.

    Parameters
    ----------
    commit : str
        SHA commita.
    repo_path : str
        Ścieżka do repozytorium Git.

    Returns
    -------
    int
        Liczba zmienionych linii.
    """
    try:
        out = git(
            ["diff-tree", "--no-commit-id", "--numstat", "-r", commit],
            cwd=repo_path
        )
    except subprocess.CalledProcessError:
        return 0

    total = 0
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            total += int(parts[0]) + int(parts[1])

    return total


def is_comment_only(commit: str, repo_path: str) -> bool:
    """
    Sprawdza, czy commit zawiera wyłącznie zmiany komentarzy.

    Analizowany jest diff bez kontekstu, a każda linia
    dodana lub usunięta musi być komentarzem.

    Parameters
    ----------
    commit : str
        SHA commita.
    repo_path : str
        Ścieżka do repozytorium Git.

    Returns
    -------
    bool
        True jeśli commit zmienia tylko komentarze.
    """
    diff = git(
        ["show", commit, "--unified=0", "--no-color"],
        cwd=repo_path
    )

    lines = [l for l in diff.splitlines() if l.startswith(("+", "-"))]

    if not lines:
        return True

    return all(
        COMMENT_REGEX.match(l) or l.strip() in ("+", "-")
        for l in lines
    )


def is_binary_only(commit: str, repo_path: str) -> bool:
    """
    Sprawdza, czy commit dotyczy wyłącznie plików binarnych.

    Weryfikacja odbywa się na podstawie rozszerzeń plików.

    Parameters
    ----------
    commit : str
        SHA commita.
    repo_path : str
        Ścieżka do repozytorium Git.

    Returns
    -------
    bool
        True jeśli commit zmienia tylko pliki binarne.
    """
    try:
        files = git(
            ["diff-tree", "--no-commit-id", "--name-only", "-r", commit],
            cwd=repo_path
        ).splitlines()
    except subprocess.CalledProcessError:
        return False

    if not files:
        return False

    return all(f.lower().endswith(BINARY_EXTENSIONS) for f in files)


def get_commit_info(commit: str, repo_path: str) -> tuple[str, str]:
    """
    Pobiera podstawowe informacje o commicie.

    Parameters
    ----------
    commit : str
        SHA commita.
    repo_path : str
        Ścieżka do repozytorium Git.

    Returns
    -------
    tuple[str, str]
        Krotka (autor, data).
    """
    info = git(
        ["show", "-s", "--format=%an|%ad", "--date=short", commit],
        cwd=repo_path
    ).strip()

    author, date = info.split("|", 1)
    return author, date


def detect_useless_commits(repo_path: str) -> list[dict]:
    """
    Analizuje wszystkie commity w repozytorium i wykrywa te,
    które mogą być uznane za mało wartościowe.

    Wykrywane problemy:
    - WHITESPACE_ONLY
    - COMMENT_ONLY
    - TOO_LITTLE_CHANGES

    Parameters
    ----------
    repo_path : str
        Ścieżka do repozytorium Git.

    Returns
    -------
    list[dict]
        Lista commitów o niskiej wartości.
        Każdy element zawiera:
        - sha (str)
        - author (str)
        - problem (str)
    """
    if not os.path.exists(repo_path):
        print(f"[ERROR] Repo path does not exist: {repo_path}")
        return []

    try:
        commits = git(["rev-list", "--all"], cwd=repo_path).splitlines()
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to list commits in {repo_path}: {e}")
        return []

    results = []

    for sha in commits:
        try:
            msg = git(
                ["log", "-1", "--pretty=%s", sha],
                cwd=repo_path
            ).strip()

            author, _ = get_commit_info(sha, repo_path)

            if is_merge_commit(sha, repo_path) or MERGE_PR_REGEX.match(msg):
                continue

            if is_binary_only(sha, repo_path):
                continue

            lines_changed = count_lines_changed(sha, repo_path)

            if is_whitespace_only(sha, repo_path):
                results.append({
                    "sha": sha,
                    "author": author,
                    "problem": "WHITESPACE_ONLY"
                })
            elif is_comment_only(sha, repo_path):
                results.append({
                    "sha": sha,
                    "author": author,
                    "problem": "COMMENT_ONLY"
                })
            elif lines_changed < SMALL_CHANGE_THRESHOLD:
                results.append({
                    "sha": sha,
                    "author": author,
                    "problem": "TOO_LITTLE_CHANGES"
                })

        except Exception as e:
            print(f"[WARNING] Error analyzing commit {sha}: {e}")

    return results