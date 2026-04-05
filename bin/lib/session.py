"""Session-scoped paths for peer review.

Derives a deterministic temp file path from the working directory so that
all commands in the same session find the same log file without passing
paths around. Concurrent sessions in different directories get different files.
"""

import hashlib
import os


def session_log_path():
    """Return the session log file path, derived from cwd."""
    cwd_hash = hashlib.md5(os.getcwd().encode()).hexdigest()[:12]
    return f"/tmp/peer-review-{cwd_hash}.json"
