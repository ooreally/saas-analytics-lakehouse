from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any


def load_json_compatible_yaml(path: str | Path) -> dict[str, Any]:
    """Load a JSON-compatible YAML file using the standard library."""
    file_path = Path(path)
    return json.loads(file_path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class ProjectConfig:
    project_name: str
    catalog: str
    database_prefix: str
    layers: dict[str, str]
    paths: dict[str, str]
    table_prefix: str
    batch_window_days: int
    feature_flags: dict[str, Any]
    gold_tables: list[str]

    @classmethod
    def from_path(cls, path: str | Path) -> "ProjectConfig":
        payload = load_json_compatible_yaml(path)
        return cls(**payload)

    def schema_name(self, layer: str) -> str:
        suffix = self.layers[layer]
        return f"{self.database_prefix}_{suffix}"

    def full_table_name(self, layer: str, entity: str) -> str:
        if layer in {"gold", "ops", "quarantine"} or entity.startswith(f"{layer}_"):
            table_name = entity
        else:
            table_name = f"{layer}_{entity}"
        return f"{self.catalog}.{self.schema_name(layer)}.{table_name}"

    def audit_table_name(self) -> str:
        return self.full_table_name("ops", "pipeline_audit")

    def quality_table_name(self) -> str:
        return self.full_table_name("ops", "data_quality_results")

    def summary_table_name(self) -> str:
        return self.full_table_name("ops", "pipeline_run_summary")

    def quarantine_table_name(self, entity: str) -> str:
        return self.full_table_name("quarantine", f"quarantine_{entity}")

    def raw_root(self, repo_root: str | Path) -> Path:
        return Path(repo_root) / self.paths["raw_root"]

    def exports_root(self, repo_root: str | Path) -> Path:
        return Path(repo_root) / self.paths["exports_root"]
