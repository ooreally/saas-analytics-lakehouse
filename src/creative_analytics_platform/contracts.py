from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import load_json_compatible_yaml


@dataclass(frozen=True)
class ColumnContract:
    name: str
    type: str
    description: str
    pii: bool = False


@dataclass(frozen=True)
class SourceContract:
    entity: str
    primary_key: list[str]
    timestamp_columns: list[str]
    required_columns: list[str]
    enums: dict[str, list[str]]
    columns: list[ColumnContract]

    @property
    def column_names(self) -> list[str]:
        return [column.name for column in self.columns]

    @property
    def pii_columns(self) -> list[str]:
        return [column.name for column in self.columns if column.pii]


def load_contract(path: str | Path) -> SourceContract:
    payload = load_json_compatible_yaml(path)
    columns = [ColumnContract(**column) for column in payload["columns"]]
    payload = dict(payload)
    payload["columns"] = columns
    return SourceContract(**payload)


def load_all_contracts(root: str | Path) -> dict[str, SourceContract]:
    contracts_path = Path(root)
    contracts: dict[str, SourceContract] = {}
    for file_path in sorted(contracts_path.glob("*.yml")):
        contract = load_contract(file_path)
        contracts[contract.entity] = contract
    return contracts

