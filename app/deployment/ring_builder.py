from __future__ import annotations

from collections import Counter
from decimal import Decimal, ROUND_FLOOR
from typing import Iterable, Literal

import pandas as pd

from app.config.settings import DEFAULT_RANDOM_SEED, DEFAULT_RING_COLUMN
from app.io.exporters import export_rings
from app.io.tables import load_table
from app.models.deployment import (
    ExclusionReport,
    PilotDistribution,
    PilotSummary,
    RingDefinition,
    RingResult,
    RingSummary,
)


AssignmentMode = Literal["simple", "progressive", "custom", "pilot"]


def build_equal_rings(
    dataframe: pd.DataFrame,
    ring_count: int,
    *,
    shuffle: bool = True,
    seed: int = DEFAULT_RANDOM_SEED,
    stratify_columns: Iterable[str] | None = None,
) -> RingResult:
    if ring_count < 1:
        raise ValueError("Le nombre de rings doit etre superieur a 0.")
    ring_names = [f"Ring {index}" for index in range(1, ring_count + 1)]
    sizes = _balanced_sizes(len(dataframe), ring_count)
    return assign_to_rings(
        dataframe,
        ring_names,
        sizes,
        shuffle=shuffle,
        seed=seed,
        stratify_columns=tuple(stratify_columns or ()),
        assignment_mode="simple",
    )


def build_progressive_rings(
    dataframe: pd.DataFrame,
    definitions: Iterable[RingDefinition],
    *,
    shuffle: bool = True,
    seed: int = DEFAULT_RANDOM_SEED,
    stratify_columns: Iterable[str] | None = None,
) -> RingResult:
    ring_definitions = list(definitions)
    _validate_ring_names(ring_definitions)
    percentages = [definition.percentage for definition in ring_definitions]
    if any(value is None or value < 0 for value in percentages):
        raise ValueError("Chaque ring progressif doit avoir un pourcentage positif.")
    total = sum(float(value or 0) for value in percentages)
    if abs(total - 100.0) > 0.0001:
        raise ValueError("La somme des pourcentages doit etre egale a 100.")
    sizes = _sizes_from_percentages(len(dataframe), [float(value or 0) for value in percentages])
    return assign_to_rings(
        dataframe,
        [definition.name for definition in ring_definitions],
        sizes,
        shuffle=shuffle,
        seed=seed,
        stratify_columns=tuple(stratify_columns or ()),
        assignment_mode="progressive",
    )


def build_custom_size_rings(
    dataframe: pd.DataFrame,
    definitions: Iterable[RingDefinition],
    *,
    shuffle: bool = True,
    seed: int = DEFAULT_RANDOM_SEED,
    stratify_columns: Iterable[str] | None = None,
) -> RingResult:
    ring_definitions = list(definitions)
    _validate_ring_names(ring_definitions)
    remaining_definitions = [definition for definition in ring_definitions if definition.is_remaining]
    if len(remaining_definitions) > 1:
        raise ValueError("Un seul ring peut utiliser le reste.")

    explicit_total = 0
    sizes: list[int | None] = []
    for definition in ring_definitions:
        if definition.is_remaining:
            sizes.append(None)
            continue
        if definition.size is None or definition.size < 0:
            raise ValueError("Chaque ring custom doit avoir une taille positive ou etre marque Remaining.")
        explicit_total += definition.size
        sizes.append(definition.size)

    if explicit_total > len(dataframe):
        raise ValueError("Les tailles demandees depassent la population disponible.")
    if remaining_definitions:
        remaining = len(dataframe) - explicit_total
        final_sizes = [remaining if size is None else size for size in sizes]
    else:
        if explicit_total != len(dataframe):
            raise ValueError("Sans ring Remaining, la somme des tailles doit egaler la population.")
        final_sizes = [int(size or 0) for size in sizes]

    return assign_to_rings(
        dataframe,
        [definition.name for definition in ring_definitions],
        final_sizes,
        shuffle=shuffle,
        seed=seed,
        stratify_columns=tuple(stratify_columns or ()),
        assignment_mode="custom",
    )


def build_representative_pilot(
    dataframe: pd.DataFrame,
    pilot_size: int,
    criteria: Iterable[str],
    *,
    seed: int = DEFAULT_RANDOM_SEED,
) -> RingResult:
    _validate_dataframe(dataframe)
    if pilot_size < 1:
        raise ValueError("La taille du pilote doit etre superieure a 0.")
    if pilot_size > len(dataframe):
        raise ValueError("La taille du pilote depasse la population disponible.")

    criteria_tuple = tuple(criteria)
    _validate_columns(dataframe, criteria_tuple)
    result = assign_to_rings(
        dataframe,
        ["Pilot", "Remaining"],
        [pilot_size, len(dataframe) - pilot_size],
        shuffle=True,
        seed=seed,
        stratify_columns=criteria_tuple,
        assignment_mode="pilot",
    )
    pilot_frame = result.dataframe[result.dataframe[DEFAULT_RING_COLUMN] == "Pilot"]
    result.pilot_summary = summarize_pilot(dataframe, pilot_frame, criteria_tuple)
    return result


def apply_exclusions(
    dataframe: pd.DataFrame,
    identifier_column: str,
    exclusions: Iterable[str],
) -> tuple[pd.DataFrame, pd.DataFrame, ExclusionReport]:
    _validate_dataframe(dataframe)
    _validate_columns(dataframe, (identifier_column,))

    requested = [_normalize_identifier(value) for value in exclusions if _normalize_identifier(value)]
    requested_counter = Counter(requested)
    requested_unique = set(requested_counter)

    identifiers = dataframe[identifier_column].map(_normalize_identifier)
    duplicate_values = tuple(sorted(value for value, count in Counter(identifiers).items() if value and count > 1))
    duplicate_rows = int(identifiers.duplicated(keep=False).sum())
    matched_mask = identifiers.isin(requested_unique)

    filtered = dataframe.loc[~matched_mask].copy()
    excluded = dataframe.loc[matched_mask].copy()
    found = set(identifiers.loc[matched_mask])
    report = ExclusionReport(
        requested_count=len(requested),
        excluded_count=len(excluded),
        not_found=tuple(sorted(requested_unique - found)),
        duplicate_values=duplicate_values,
        duplicate_rows=duplicate_rows,
    )
    return filtered.reset_index(drop=True), excluded.reset_index(drop=True), report


def assign_to_rings(
    dataframe: pd.DataFrame,
    ring_names: list[str],
    sizes: list[int],
    *,
    shuffle: bool,
    seed: int,
    stratify_columns: tuple[str, ...],
    assignment_mode: AssignmentMode,
) -> RingResult:
    _validate_dataframe(dataframe)
    if len(ring_names) != len(sizes):
        raise ValueError("Le nombre de rings et de tailles ne correspond pas.")
    if sum(sizes) != len(dataframe):
        raise ValueError("Les tailles de rings doivent couvrir exactement toutes les lignes.")
    if any(size < 0 for size in sizes):
        raise ValueError("Les tailles de rings ne peuvent pas etre negatives.")
    _validate_columns(dataframe, stratify_columns)

    work = dataframe.copy().reset_index(drop=True)
    if stratify_columns:
        ordered_indices = _stratified_order(work, stratify_columns, seed)
    elif shuffle:
        ordered_indices = list(work.sample(frac=1, random_state=seed).index)
    else:
        ordered_indices = list(work.index)

    assignments: dict[int, str] = {}
    cursor = 0
    for ring_name, size in zip(ring_names, sizes):
        for index in ordered_indices[cursor : cursor + size]:
            assignments[index] = ring_name
        cursor += size

    work[DEFAULT_RING_COLUMN] = work.index.map(assignments)
    summaries = summarize_rings(work, ring_names, stratify_columns)
    return RingResult(work, ring_names, summaries, assignment_mode=assignment_mode)


def summarize_rings(
    dataframe: pd.DataFrame,
    ring_names: Iterable[str],
    criteria_columns: Iterable[str] = (),
) -> list[RingSummary]:
    total = len(dataframe)
    summaries: list[RingSummary] = []
    for ring_name in ring_names:
        ring_frame = dataframe[dataframe[DEFAULT_RING_COLUMN] == ring_name]
        distinct_values = {
            column: int(ring_frame[column].fillna("<empty>").astype(str).nunique())
            for column in criteria_columns
            if column in ring_frame.columns
        }
        percentage = (len(ring_frame) / total * 100) if total else 0
        summaries.append(RingSummary(ring_name, len(ring_frame), percentage, distinct_values))
    return summaries


def summarize_pilot(
    population: pd.DataFrame,
    pilot: pd.DataFrame,
    criteria: tuple[str, ...],
) -> PilotSummary:
    distributions: list[PilotDistribution] = []
    coverage_by_column: dict[str, float] = {}
    deltas: list[float] = []

    for column in criteria:
        global_distribution = _distribution(population[column])
        pilot_distribution = _distribution(pilot[column])
        global_values = set(global_distribution)
        pilot_values = set(pilot_distribution)
        coverage = (len(global_values & pilot_values) / len(global_values) * 100) if global_values else 100.0
        max_delta = max(
            (
                abs(global_distribution.get(value, 0.0) - pilot_distribution.get(value, 0.0))
                for value in global_values | pilot_values
            ),
            default=0.0,
        )
        coverage_by_column[column] = round(coverage, 2)
        deltas.append(max_delta)
        distributions.append(
            PilotDistribution(
                column=column,
                global_distribution=global_distribution,
                pilot_distribution=pilot_distribution,
                coverage=round(coverage, 2),
                max_delta=round(max_delta, 4),
            )
        )

    average_delta = sum(deltas) / len(deltas) if deltas else 0.0
    score = max(0.0, 100.0 - average_delta * 100.0)
    return PilotSummary(
        population_rows=len(population),
        pilot_rows=len(pilot),
        criteria=criteria,
        coverage_by_column=coverage_by_column,
        distributions=tuple(distributions),
        representativity_score=round(score, 2),
        formula="100 - moyenne des ecarts absolus maximum par critere, exprimes en points de pourcentage.",
    )


def _stratified_order(dataframe: pd.DataFrame, columns: tuple[str, ...], seed: int) -> list[int]:
    work = dataframe.copy()
    work["_stratum_key"] = work[list(columns)].fillna("<empty>").astype(str).agg(" | ".join, axis=1)
    shuffled = work.sample(frac=1, random_state=seed)
    groups = {str(key): list(group.index) for key, group in shuffled.groupby("_stratum_key", sort=True)}
    totals = {key: len(indices) for key, indices in groups.items()}
    taken = {key: 0 for key in groups}
    total_rows = len(work)
    ordered: list[int] = []
    for position in range(total_rows):
        candidates = [key for key, indices in groups.items() if indices]
        key = max(
            candidates,
            key=lambda candidate: (
                ((position + 1) * totals[candidate] / total_rows) - taken[candidate],
                totals[candidate],
                candidate,
            ),
        )
        ordered.append(groups[key].pop(0))
        taken[key] += 1
    return ordered


def _balanced_sizes(total_rows: int, buckets: int) -> list[int]:
    base = total_rows // buckets
    remainder = total_rows % buckets
    return [base + (1 if index < remainder else 0) for index in range(buckets)]


def _sizes_from_percentages(total_rows: int, percentages: list[float]) -> list[int]:
    exact_values = [Decimal(str(total_rows)) * Decimal(str(percentage)) / Decimal("100") for percentage in percentages]
    floors = [int(value.to_integral_value(rounding=ROUND_FLOOR)) for value in exact_values]
    missing = total_rows - sum(floors)
    remainders = sorted(
        enumerate(exact_values),
        key=lambda item: (item[1] - int(item[1].to_integral_value(rounding=ROUND_FLOOR)), -item[0]),
        reverse=True,
    )
    for index, _ in remainders[:missing]:
        floors[index] += 1
    return floors


def _distribution(series: pd.Series) -> dict[str, float]:
    normalized = series.fillna("<empty>").astype(str)
    total = len(normalized)
    if total == 0:
        return {}
    counts = normalized.value_counts(normalize=True)
    return {str(index): round(float(value), 4) for index, value in counts.items()}


def _validate_dataframe(dataframe: pd.DataFrame) -> None:
    if dataframe.empty:
        raise ValueError("Le fichier ne contient aucune ligne.")


def _validate_ring_names(definitions: list[RingDefinition]) -> None:
    if not definitions:
        raise ValueError("Ajoutez au moins un ring.")
    names = [definition.name.strip() for definition in definitions]
    if any(not name for name in names):
        raise ValueError("Chaque ring doit avoir un nom.")
    if len(set(names)) != len(names):
        raise ValueError("Les noms de rings doivent etre uniques.")


def _validate_columns(dataframe: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Colonnes introuvables : {', '.join(missing)}")


def _normalize_identifier(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().casefold()


__all__ = [
    "RingDefinition",
    "apply_exclusions",
    "build_custom_size_rings",
    "build_equal_rings",
    "build_progressive_rings",
    "build_representative_pilot",
    "export_rings",
    "load_table",
    "summarize_pilot",
    "summarize_rings",
]
