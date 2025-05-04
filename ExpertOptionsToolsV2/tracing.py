import io
import sys
import logging
from typing import Optional, List

class Logger:
    def __init__(self, name: str = "ExpertOption"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.handlers: List[logging.Handler] = []

    def info(self, msg: str, extra: dict = None) -> None:
        self.logger.info(msg, extra=extra)

    def error(self, msg: str, extra: dict = None) -> None:
        self.logger.error(msg, extra=extra, exc_info=True)

    def debug(self, msg: str, extra: dict = None) -> None:
        self.logger.debug(msg, extra=extra)

    def warning(self, msg: str, extra: dict = None) -> None:
        self.logger.warning(msg, extra=extra)

class LogBuilder:
    def __init__(self):
        self.logger = Logger()
        self.file_handler: Optional[logging.FileHandler] = None
        self.stream_handler: Optional[logging.StreamHandler] = None

    def log_file(self, file_path: str, level: str) -> 'LogBuilder':
        self.file_handler = logging.FileHandler(file_path, encoding='utf-8')
        self.file_handler.setLevel(getattr(logging, level.upper()))
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.file_handler.setFormatter(formatter)
        self.logger.handlers.append(self.file_handler)
        return self

    def terminal(self, level: str) -> 'LogBuilder':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        self.stream_handler = logging.StreamHandler(sys.stdout)
        self.stream_handler.setLevel(getattr(logging, level.upper()))
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.stream_handler.setFormatter(formatter)
        self.logger.handlers.append(self.stream_handler)
        return self

    def build(self) -> Logger:
        for handler in self.logger.handlers:
            self.logger.logger.addHandler(handler)
        return self.logger
