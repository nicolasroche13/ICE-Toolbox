from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.config.settings import DEFAULT_RING_COLUMN
from app.models.deployment import ExportedFiles, ExportOptions, RingResult
from app.utils.files import non_overwriting_path, safe_filename


def _write_dataframe(dataframe: pd.DataFrame, path: Path, file_format: str) -> None:
    if file_format == "csv":
        dataframe.to_csv(path, index=False, encoding="utf-8-sig")
        return
    if file_format == "xlsx":
        dataframe.to_excel(path, index=False, engine="openpyxl")
        return
    raise ValueError("Format d'export non supporte.")


def export_rings(result: RingResult, options: ExportOptions) -> ExportedFiles:
    options.output_dir.mkdir(parents=True, exist_ok=True)
    suffix = f".{options.file_format}"
    created: list[Path] = []

    if options.include_global:
        path = non_overwriting_path(options.output_dir / f"{safe_filename(options.prefix)}_all_rings{suffix}")
        _write_dataframe(result.dataframe, path, options.file_format)
        created.append(path)

    if options.split_by_ring:
        for ring in result.ring_names:
            ring_frame = result.dataframe[result.dataframe[DEFAULT_RING_COLUMN] == ring]
            path = non_overwriting_path(
                options.output_dir / f"{safe_filename(options.prefix)}_{safe_filename(ring)}{suffix}"
            )
            _write_dataframe(ring_frame, path, options.file_format)
            created.append(path)

    return ExportedFiles(tuple(created))

