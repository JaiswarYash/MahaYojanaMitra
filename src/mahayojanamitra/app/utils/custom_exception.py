"""Structured logging format for MahaYojanaMitra application."""

import logging
import re
from datetime import datetime
from pathlib import Path
import structlog
import threading
from structlog.stdlib import BoundLogger

LOG_DIR = Path(__file__).resolve().parent[2]/"logs" # log path
LOGGER_NAME = "MahaYojanaMitra"
RETENTION = 10 # Number of logs to keep
MYM_LOG_FILENAME = re.compile(r"MYM_(?:\d{4}_\d{6}|\d{8}T\d{6}_\d{6}Z)\.jonl") # log format - eg: MYM_2026_112530.jsonl

class MahaYojanaMitraLogger:
    """Write structured JSON lines to disk and to the console."""
    _configuration_lock = threading.Lock() # -> for internal use
    _retention_lock = threading.Lock()
    _structlog_lock = False

    def __init__(self, log_dir: str | Path =LOG_DIR, level: int = logging.INFO, console: bool = True) -> None:
        self.logs_dir = Path(LOG_DIR).expanduser().resolve()
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%d/%m, %H:%M:%S")
        self.log_file_path = self.logs_dir / f"mym_{self.timestamp}.jonsl"
        self.level = level
        self.console = console
        self._manage_handler: list[tuple[logging.Logger, logging.handlers]] = []