from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import SourceContract


@dataclass(frozen=True)
class QualityCheckResult:
    check_name: str
    target_name: str
    status: str
    observed_value: str
    details: str

    def as_dict(self) -> dict[str, str]:
        return {
            "check_name": self.check_name,
            "target_name": self.target_name,
            "status": self.status,
            "observed_value": self.observed_value,
            "details": self.details,
        }


def _blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def split_valid_invalid(
    contract: SourceContract,
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    valid_records: list[dict[str, Any]] = []
    invalid_records: list[dict[str, Any]] = []

    for record in records:
        errors: list[str] = []
        for required_column in contract.required_columns:
            if _blank(record.get(required_column)):
                errors.append(f"missing_required:{required_column}")

        for column_name, allowed_values in contract.enums.items():
            if column_name not in record:
                continue
            value = "" if record.get(column_name) is None else str(record.get(column_name)).strip()
            if value and value not in allowed_values:
                errors.append(f"invalid_enum:{column_name}={value}")

        if errors:
            invalid_record = dict(record)
            invalid_record["_validation_errors"] = ";".join(errors)
            invalid_records.append(invalid_record)
        else:
            valid_records.append(record)

    return valid_records, invalid_records


def find_duplicate_keys(records: list[dict[str, Any]], key_fields: list[str]) -> dict[tuple[Any, ...], int]:
    counts: dict[tuple[Any, ...], int] = {}
    for record in records:
        key = tuple(record.get(field) for field in key_fields)
        counts[key] = counts.get(key, 0) + 1
    return {key: count for key, count in counts.items() if count > 1}


def count_nulls(records: list[dict[str, Any]], columns: list[str]) -> dict[str, int]:
    results = {column: 0 for column in columns}
    for record in records:
        for column in columns:
            if _blank(record.get(column)):
                results[column] += 1
    return results


def reconcile_metric_total(component_total: int, expected_total: int, tolerance: int = 0) -> bool:
    return abs(component_total - expected_total) <= tolerance

