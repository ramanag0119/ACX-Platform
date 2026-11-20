"""MessageDispatcher: canonical envelope -> registered handler."""

from __future__ import annotations

import logging

from app.integrations.core.envelope import CanonicalEnvelope
from app.integrations.core.errors import classify
from app.integrations.exchange.registry import HandlerContext, HandlerRegistry, HandlerResult

logger = logging.getLogger("hms.integrations.dispatch")


class MessageDispatcher:
    def __init__(self, handlers: HandlerRegistry) -> None:
        self._handlers = handlers

    def dispatch(self, envelope: CanonicalEnvelope, ctx: HandlerContext) -> HandlerResult:
        handler = self._handlers.get(envelope.message_type)
        try:
            return handler.handle(envelope, ctx)
        except Exception as exc:
            error = classify(exc)
            # Identifiers only -- never the exception text, which may echo payload.
            logger.warning(
                "handler failed message_id=%s type=%s code=%s category=%s",
                envelope.message_id, envelope.message_type, error.code, error.category,
            )
            if error is exc:
                raise
            raise error from exc
