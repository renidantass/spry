from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ColumnType:
    sql_type: str
    auto_increment_keyword: str = ""
