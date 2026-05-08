from __future__ import annotations

from pathlib import Path
import csv
from typing import Any

from .audit import AuditRecord


def locate_repo_root(start_path: str | Path | None = None) -> Path:
    current = Path(start_path or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "conf" / "project_config.yml").exists():
            return candidate
    raise FileNotFoundError("Could not locate repo root from the current working directory.")


def read_drop_records(repo_root: str | Path, batch_id: str, entity: str) -> list[dict[str, Any]]:
    file_path = Path(repo_root) / "data" / "raw" / batch_id / f"{entity}.csv"
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def spark_table_exists(spark: Any, full_table_name: str) -> bool:
    catalog, schema, table = full_table_name.split(".", 2)
    return bool(spark.catalog.tableExists(f"{catalog}.{schema}.{table}"))


def merge_into_delta(spark: Any, target_table: str, updates_df: Any, merge_keys: list[str]) -> None:
    from delta.tables import DeltaTable

    if not spark_table_exists(spark, target_table):
        updates_df.write.format("delta").mode("overwrite").saveAsTable(target_table)
        return

    condition = " AND ".join([f"target.{key} = source.{key}" for key in merge_keys])
    (
        DeltaTable.forName(spark, target_table)
        .alias("target")
        .merge(updates_df.alias("source"), condition)
        .whenMatchedUpdateAll()
        .whenNotMatchedInsertAll()
        .execute()
    )


def append_rows(spark: Any, target_table: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    spark.createDataFrame(rows).write.format("delta").mode("append").saveAsTable(target_table)


def append_audit_record(spark: Any, target_table: str, record: AuditRecord) -> None:
    append_rows(spark, target_table, [record.as_dict()])
