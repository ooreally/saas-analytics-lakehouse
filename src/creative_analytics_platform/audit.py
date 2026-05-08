from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class AuditRecord:
    step_name: str
    batch_id: str
    status: str
    input_count: int
    output_count: int
    message: str
    started_at: str
    ended_at: str
    duration_seconds: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "step_name": self.step_name,
            "batch_id": self.batch_id,
            "status": self.status,
            "input_count": self.input_count,
            "output_count": self.output_count,
            "message": self.message,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
        }


def build_audit_record(
    step_name: str,
    batch_id: str,
    status: str,
    input_count: int,
    output_count: int,
    message: str = "",
    started_at: str | None = None,
    ended_at: str | None = None,
) -> AuditRecord:
    started_value = started_at or utc_now_iso()
    ended_value = ended_at or utc_now_iso()
    start_dt = datetime.fromisoformat(started_value.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(ended_value.replace("Z", "+00:00"))
    duration = int((end_dt - start_dt).total_seconds())
    return AuditRecord(
        step_name=step_name,
        batch_id=batch_id,
        status=status,
        input_count=input_count,
        output_count=output_count,
        message=message,
        started_at=started_value,
        ended_at=ended_value,
        duration_seconds=max(duration, 0),
    )

