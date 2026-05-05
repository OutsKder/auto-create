import logging
import os
import datetime
from typing import Optional


def setup_logging(log_dir: Optional[str] = None, level: int = logging.INFO) -> str:
    """Configure root logger to write to a daily log file in `log_dir`.

    - log_dir: directory to write logs to (defaults to backend/agent/log)
    - level: logging level

    Returns the path to the log file.
    """
    # Default log directory is backend/agent/log relative to this file
    if log_dir is None:
        base = os.path.dirname(__file__)
        log_dir = os.path.join(base, "log")

    os.makedirs(log_dir, exist_ok=True)

    today = datetime.date.today().isoformat()
    log_path = os.path.join(log_dir, f"{today}.txt")

    root = logging.getLogger()
    root.setLevel(level)

    # Avoid adding duplicate file handler for same log file
    abs_log_path = os.path.abspath(log_path)
    for h in list(root.handlers):
        try:
            if (
                isinstance(h, logging.FileHandler)
                and os.path.abspath(h.baseFilename) == abs_log_path
            ):
                return abs_log_path
        except Exception:
            continue

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Ensure at least one console handler exists
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(fmt)
        root.addHandler(ch)

    return abs_log_path


def get_agent_logger(name: str) -> logging.Logger:
    """Return a logger that writes to backend/agent/log/YYYY-MM-DD.txt."""
    setup_logging()
    return logging.getLogger(name)
