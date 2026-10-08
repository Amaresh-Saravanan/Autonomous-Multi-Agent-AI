"""Structured logging (Phase 24). Every log record gets a consistent set
of correlation fields when present in `extra=` — request_id, event_id,
incident_id, agent_id, user_id — so logs from one ingestion request can be
grepped together across the sync HTTP path and the async queue worker."""

import logging

CORRELATION_FIELDS = ("request_id", "event_id", "incident_id", "agent_id", "user_id")


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for field in CORRELATION_FIELDS:
            if not hasattr(record, field):
                setattr(record, field, "-")
        return True


def configure_logging(level: str = "INFO") -> None:
    fmt = (
        "%(asctime)s %(levelname)-8s %(name)s "
        "[request_id=%(request_id)s event_id=%(event_id)s incident_id=%(incident_id)s "
        "agent_id=%(agent_id)s user_id=%(user_id)s] %(message)s"
    )
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt))
    handler.addFilter(CorrelationFilter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
