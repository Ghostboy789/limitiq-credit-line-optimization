"""In-memory maker-checker demonstration for synthetic manual-review cases."""

from __future__ import annotations

import hashlib
import json
import re
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

ACCOUNT_PATTERN = re.compile(r"^LIQ-\d{6}$")
DECISIONS = {"Approve proposed action", "Hold current limit", "Freeze increases"}
REASONS = {
    "Verified additional information",
    "Affordability concern",
    "Recent repayment deterioration",
    "Policy exception declined",
    "Escalated for specialist review",
}


@dataclass(frozen=True)
class ReviewEvent:
    review_id: str
    account_id: str
    event: str
    actor: str
    decision: str
    reason: str
    created_at: str
    previous_hash: str
    event_hash: str


class ReviewLedger:
    """Process-local educational ledger; no uploaded or real customer data is retained."""

    def __init__(self) -> None:
        self._events: list[ReviewEvent] = []
        self._lock = threading.Lock()

    def _append(
        self, review_id: str, account_id: str, event: str, actor: str, decision: str, reason: str
    ) -> ReviewEvent:
        previous_hash = self._events[-1].event_hash if self._events else "GENESIS"
        created_at = datetime.now(UTC).isoformat()
        values = {
            "review_id": review_id,
            "account_id": account_id,
            "event": event,
            "actor": actor,
            "decision": decision,
            "reason": reason,
            "created_at": created_at,
            "previous_hash": previous_hash,
        }
        event_hash = hashlib.sha256(
            json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        item = ReviewEvent(**values, event_hash=event_hash)
        self._events.append(item)
        return item

    def submit(self, account_id: str, actor: str, decision: str, reason: str) -> ReviewEvent:
        if not ACCOUNT_PATTERN.fullmatch(account_id):
            raise ValueError("Only synthetic LIQ-###### accounts can enter the demo review ledger")
        if not actor.strip() or len(actor) > 80:
            raise ValueError("Maker identity is required and limited to 80 characters")
        if decision not in DECISIONS or reason not in REASONS:
            raise ValueError("Decision and reason must use governed values")
        with self._lock:
            review_id = f"REV-{len({event.review_id for event in self._events}) + 1:06d}"
            return self._append(review_id, account_id, "submitted", actor.strip(), decision, reason)

    def approve(self, review_id: str, checker: str) -> ReviewEvent:
        with self._lock:
            history = [event for event in self._events if event.review_id == review_id]
            if not history or history[-1].event != "submitted":
                raise ValueError("Review is not awaiting checker approval")
            maker = history[0]
            if not checker.strip() or checker.strip().casefold() == maker.actor.casefold():
                raise ValueError("Checker must be a different identified reviewer")
            return self._append(
                review_id,
                maker.account_id,
                "approved",
                checker.strip(),
                maker.decision,
                maker.reason,
            )

    def events(self, review_id: str | None = None) -> list[dict[str, str]]:
        with self._lock:
            return [
                asdict(event)
                for event in self._events
                if review_id is None or event.review_id == review_id
            ]
