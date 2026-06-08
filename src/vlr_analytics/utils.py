import json
import re
from pathlib import Path
from typing import Any

import pandas as pd


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_map_name(raw_map: object) -> str:
    value = clean_text(raw_map)
    if value == "" or value.lower() == "nan":
        return "All Maps"
    parts = value.split(" ", 1)
    if len(parts) == 2 and len(parts[0]) == 1:
        return parts[1]
    return value


def percent_to_float(value: object) -> float | None:
    value = clean_text(value).replace("%", "")
    if value == "" or value.lower() == "nan":
        return None
    return float(value) / 100


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    ensure_parent(path)
    df.to_csv(path, index=False)


def write_json(payload: dict[str, Any], path: Path) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_csv_required(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}. Run the previous pipeline step first.")
    return pd.read_csv(path)


def require_columns(df: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns - set(df.columns)
    if missing:
        raise ValueError(f"{name} is missing columns: {sorted(missing)}")
