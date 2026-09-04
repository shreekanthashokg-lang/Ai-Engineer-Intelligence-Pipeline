"""Structured JSON logging. Every pipeline-stage log line should include:
run_id, source, url, record_type, attempt, status, duration_ms, error_type,
provider, retry_count — pass these via the `extra=` dict on log calls.
"""
from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar

RUN_ID: ContextVar[str] = ContextVar("run_id", default="")


class JsonFormatter(logging.Formatter):
    _std_keys = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "run_id": RUN_ID.get(),
        }
        for k, v in record.__dict__.items():
            if k not in self._std_keys and k != "message":
                payload[k] = v
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def new_run_id() -> str:
    rid = str(uuid.uuid4())
    RUN_ID.set(rid)
    return rid
