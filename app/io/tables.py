from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from app.config.settings import CSV_ENCODINGS, DEFAULT_PREVIEW_ROWS


class TableLoadError(ValueError):
    """Raised when a user-provided table cannot be loaded."""


def _detect_csv_separator(path: Path, encoding: str) -> str | None:
    with path.open("r", encoding=encoding, newline="") as handle:
        sample = handle.read(8192)
    if not sample:
        return None
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        return None


def load_table(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    suffix = source.suffix.lower()
    if not source.exists():
        raise TableLoadError(f"Fichier introuvable : {source}")

    try:
        if suffix == ".csv":
            last_error: Exception | None = None
            for encoding in CSV_ENCODINGS:
                try:
                    separator = _detect_csv_separator(source, encoding)
                    return pd.read_csv(source, sep=separator, engine="python", encoding=encoding)
                except UnicodeDecodeError as exc:
                    last_error = exc
                except Exception as exc:
                    last_error = exc
            raise TableLoadError(f"Impossible de lire le CSV. Derniere erreur : {last_error}")

        if suffix in {".xlsx", ".xlsm"}:
            return pd.read_excel(source, engine="openpyxl")
    except TableLoadError:
        raise
    except Exception as exc:
        raise TableLoadError(f"Impossible de lire le fichier : {exc}") from exc

    raise TableLoadError("Format non supporte. Utilisez CSV, XLSX ou XLSM.")


def preview_rows(dataframe: pd.DataFrame, limit: int = DEFAULT_PREVIEW_ROWS) -> pd.DataFrame:
    return dataframe.head(limit).copy()

