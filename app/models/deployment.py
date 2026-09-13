from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import pandas as pd


AssignmentMode = Literal["simple", "progressive", "custom", "pilot"]
ExportFormat = Literal["csv", "xlsx"]


@dataclass(frozen=True)
class RingDefinition:
    name: str
    percentage: float | None = None
    size: int | None = None
    is_remaining: bool = False


@dataclass(frozen=True)
class ExclusionReport:
    requested_count: int
    excluded_count: int
    not_found: tuple[str, ...] = ()
    duplicate_values: tuple[str, ...] = ()
    duplicate_rows: int = 0


@dataclass(frozen=True)
class RingSummary:
    name: str
    rows: int
    percentage: float
    distinct_values: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class PilotDistribution:
    column: str
    global_distribution: dict[str, float]
    pilot_distribution: dict[str, float]
    coverage: float
    max_delta: float


@dataclass(frozen=True)
class PilotSummary:
    population_rows: int
    pilot_rows: int
    criteria: tuple[str, ...]
    coverage_by_column: dict[str, float]
    distributions: tuple[PilotDistribution, ...]
    representativity_score: float
    formula: str


@dataclass
class RingResult:
    dataframe: pd.DataFrame
    ring_names: list[str]
    summaries: list[RingSummary]
    assignment_mode: AssignmentMode
    excluded_dataframe: pd.DataFrame | None = None
    exclusion_report: ExclusionReport | None = None
    pilot_summary: PilotSummary | None = None


@dataclass(frozen=True)
class ExportOptions:
    output_dir: Path
    prefix: str
    file_format: ExportFormat
    split_by_ring: bool = True
    include_global: bool = True


@dataclass(frozen=True)
class ExportedFiles:
    paths: tuple[Path, ...]

