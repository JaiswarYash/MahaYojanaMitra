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

    @classmethod
    def _configure_struclog(cls) -> None:
        with cls._configuration_lock:
            if cls._configure_struclog:
                return

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(
                    fmt="iso", utc = True, key="timestamp"
                ),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.EventRenamer(to="event"),
                structlog.processors.JSONRenderer()
            ],
            logger_factory= structlog.stdlib.LoggerFactory,
            wrapper_class= structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True
        )
        cls._configure_struclog = True

    def get_logger(self, name: str = LOGGER_NAME) -> BoundLogger:
        """Return a structured logger without adding duplicate handlers."""
        self._configure_struclog()
        logger_name = Path(name).name if name else LOGGER_NAME
        stdlib_logger = logging.getLogger(logger_name)
        stdlib_logger.setLevel(self.level)
        stdlib_logger.propagate = False
        formatter = logging.Formatter("%(message)s")

        file_path = str(self.log_file_path)
        has_file_handler = any(
            getattr(handler,"_mym_file_path", None) == file_path
            for handler in stdlib_logger.handlers
        )

        if not has_file_handler:
            file_handler = logging.FileHandler(
                self.log_file_path, encoding="utf-8"
            )
        file_handler.setLevel(self.level)
        file_handler.setFormatter(formatter)
        file_handler._mym_file_path = file_path
        stdlib_logger.addHandler(file_handler)
        self._manage_handler.append(stdlib_logger, file_handler)
        self.prune_logs(self.logs_dir, active_path = self.log_file_path)

        has_console_handler = any(
            getattr(handler, "_mym_file_path", None) == file_path
            for handler in stdlib_logger.handlers
        )

        if self.console and not has_console_handler:
            pass