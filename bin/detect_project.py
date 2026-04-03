#!/usr/bin/env python3
"""Detect project language, framework, and context."""

import glob
import json
import os
import subprocess

# Map project files to (language, framework) pairs.
# First match wins, so order by specificity.
PROJECT_SIGNATURES = [
    ("package.json", "TypeScript", ""),  # refined below if tsconfig exists
    ("Cargo.toml", "Rust", ""),
    ("go.mod", "Go", ""),
    ("pyproject.toml", "Python", ""),
    ("requirements.txt", "Python", ""),
    ("Gemfile", "Ruby", ""),
    ("pom.xml", "Java", ""),
    ("build.gradle", "Java", ""),
    ("*.csproj", "C#", ""),
    ("mix.exs", "Elixir", ""),
    ("composer.json", "PHP", ""),
]

FRAMEWORK_HINTS = {
    "Python": {
        "fastapi": "FastAPI",
        "flask": "Flask",
        "django": "Django",
        "streamlit": "Streamlit",
    },
    "TypeScript": {
        "react": "React",
        "next": "Next.js",
        "vue": "Vue",
        "angular": "Angular",
        "express": "Express",
    },
    "JavaScript": {
        "react": "React",
        "next": "Next.js",
        "vue": "Vue",
        "angular": "Angular",
        "express": "Express",
    },
    "Ruby": {
        "rails": "Rails",
        "sinatra": "Sinatra",
    },
}


def detect_language(working_dir):
    """Detect language and framework from project files."""
    language = ""
    framework = ""

    for pattern, lang, fw in PROJECT_SIGNATURES:
        if glob.glob(os.path.join(working_dir, pattern)):
            language = lang
            framework = fw
            break

    if not language:
        return language, framework

    # package.json defaults to TypeScript; downgrade to JavaScript if no tsconfig
    if language == "TypeScript" and not os.path.exists(
        os.path.join(working_dir, "tsconfig.json")
    ):
        language = "JavaScript"

    # Try to detect framework from dependency files
    hints = FRAMEWORK_HINTS.get(language, {})
    if hints:
        dep_content = ""
        if language == "Python":
            for f in ("pyproject.toml", "requirements.txt"):
                path = os.path.join(working_dir, f)
                if os.path.exists(path):
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        dep_content = fh.read().lower()
                    break
        elif language in ("TypeScript", "JavaScript"):
            path = os.path.join(working_dir, "package.json")
            if os.path.exists(path):
                with open(path, encoding="utf-8", errors="replace") as fh:
                    dep_content = fh.read().lower()
        elif language == "Ruby":
            path = os.path.join(working_dir, "Gemfile")
            if os.path.exists(path):
                with open(path, encoding="utf-8", errors="replace") as fh:
                    dep_content = fh.read().lower()

        for key, fw_name in hints.items():
            if key in dep_content:
                framework = fw_name
                break

    return language, framework


def git_status(working_dir):
    """Get git status summary."""
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            cwd=working_dir,
            timeout=10,
        )
        lines = result.stdout.strip().splitlines() if result.stdout.strip() else []
        return f"{len(lines)} changed files" if lines else "clean"
    except Exception:
        return "not a git repo"


def main():
    working_dir = os.getcwd()

    language, framework = detect_language(working_dir)
    status = git_status(working_dir)

    result = {
        "language": language or "unknown",
        "framework": framework,
        "working_dir": working_dir,
        "git_status": status,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
