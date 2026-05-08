from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any


def parse_iso_datetime(value: str | None) -> datetime:
    if not value:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize_plan_tier(plan_tier: str | None) -> str:
    mapping = {
        "pro": "professional",
        "professional": "professional",
        "starter": "starter",
        "enterprise": "enterprise",
        "trial": "trial",
    }
    normalized = (plan_tier or "").strip().lower()
    return mapping.get(normalized, normalized)


def mask_email(email: str | None) -> str:
    if not email or "@" not in email:
        return ""
    local_part, domain = email.split("@", 1)
    prefix = local_part[:1] or "u"
    return f"{prefix}***@{domain}"


def pseudonymize_name(name: str | None, user_id: str | None) -> str:
    if not user_id:
        return "anonymous_user"
    return f"user_{user_id.lower()}"


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def stable_text_hash(value: str | None) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:16]


def add_ingestion_metadata(
    records: list[dict[str, Any]],
    batch_id: str,
    source_file: str,
    loaded_at: str,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for record in records:
        updated = dict(record)
        updated["_batch_id"] = batch_id
        updated["_source_file"] = source_file
        updated["_loaded_at"] = loaded_at
        enriched.append(updated)
    return enriched


def dedupe_records(
    records: list[dict[str, Any]],
    key_fields: list[str],
    order_field: str,
) -> list[dict[str, Any]]:
    ordered = sorted(
        records,
        key=lambda record: (
            tuple(record.get(field, "") for field in key_fields),
            parse_iso_datetime(record.get(order_field)),
        ),
        reverse=True,
    )
    seen: set[tuple[Any, ...]] = set()
    deduped: list[dict[str, Any]] = []
    for record in ordered:
        key = tuple(record.get(field, "") for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return list(reversed(deduped))


def sanitize_user_record(record: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(record)
    cleaned["email"] = mask_email(record.get("email"))
    cleaned["full_name"] = pseudonymize_name(record.get("full_name"), record.get("user_id"))
    cleaned["acquisition_channel"] = normalize_text(record.get("acquisition_channel")).lower()
    return cleaned


def normalize_subscription_record(record: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(record)
    cleaned["plan_tier"] = normalize_plan_tier(record.get("plan_tier"))
    cleaned["status"] = normalize_text(record.get("status")).lower()
    return cleaned


def normalize_support_record(record: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(record)
    cleaned["feedback_text"] = normalize_text(record.get("feedback_text"))
    cleaned["user_comment"] = normalize_text(record.get("user_comment"))
    cleaned["feedback_hash"] = stable_text_hash(cleaned["feedback_text"])
    return cleaned

