from __future__ import annotations

import pandas as pd
import pytest

from app.config.settings import DEFAULT_RING_COLUMN
from app.deployment.ring_builder import (
    apply_exclusions,
    build_custom_size_rings,
    build_equal_rings,
    build_progressive_rings,
    build_representative_pilot,
)
from app.io.exporters import export_rings
from app.io.tables import load_table
from app.models.deployment import ExportOptions, RingDefinition


def devices(count: int = 1000) -> pd.DataFrame:
    manufacturers = ["Dell"] * 30 + ["HP"] * 50 + ["Lenovo"] * 20
    sites = ["Paris", "Lyon", "Nantes", "Lille"]
    models = ["Latitude", "EliteBook", "ThinkPad", "Surface"]
    return pd.DataFrame(
        {
            "DeviceName": [f"PC-{index:04d}" for index in range(count)],
            "Site": [sites[index % len(sites)] for index in range(count)],
            "Manufacturer": [manufacturers[index % len(manufacturers)] for index in range(count)],
            "Model": [models[index % len(models)] for index in range(count)],
            "OSVersion": [f"23H2-{index % 5}" for index in range(count)],
        }
    )


def assert_complete_assignment(source: pd.DataFrame, assigned: pd.DataFrame) -> None:
    assert len(assigned) == len(source)
    assert assigned[DEFAULT_RING_COLUMN].isna().sum() == 0
    assert set(assigned["DeviceName"]) == set(source["DeviceName"])
    assert assigned["DeviceName"].duplicated().sum() == 0


def test_equal_rings_are_balanced() -> None:
    df = devices(1000)
    result = build_equal_rings(df, 5, shuffle=False)
    counts = result.dataframe[DEFAULT_RING_COLUMN].value_counts()
    assert counts.min() == 200
    assert counts.max() == 200
    assert_complete_assignment(df, result.dataframe)


def test_equal_rings_non_divisible_differ_by_at_most_one() -> None:
    df = devices(1003)
    result = build_equal_rings(df, 5, shuffle=False)
    counts = result.dataframe[DEFAULT_RING_COLUMN].value_counts()
    assert counts.max() - counts.min() <= 1
    assert counts.sum() == 1003


def test_progressive_rings_apply_percentages_and_rounding() -> None:
    df = devices(101)
    result = build_progressive_rings(
        df,
        [
            RingDefinition("Pilot", percentage=2),
            RingDefinition("Ring 1", percentage=8),
            RingDefinition("Ring 2", percentage=20),
            RingDefinition("Ring 3", percentage=30),
            RingDefinition("Broad", percentage=40),
        ],
        shuffle=False,
    )
    counts = result.dataframe[DEFAULT_RING_COLUMN].value_counts().to_dict()
    assert counts == {"Broad": 41, "Ring 3": 30, "Ring 2": 20, "Ring 1": 8, "Pilot": 2}
    assert_complete_assignment(df, result.dataframe)


def test_progressive_rings_reject_non_100_percent_total() -> None:
    with pytest.raises(ValueError, match="100"):
        build_progressive_rings(
            devices(10),
            [RingDefinition("Pilot", percentage=10), RingDefinition("Broad", percentage=80)],
        )


def test_custom_sizes_with_remaining_ring() -> None:
    df = devices(1000)
    result = build_custom_size_rings(
        df,
        [
            RingDefinition("Pilot", size=50),
            RingDefinition("Ring 1", size=200),
            RingDefinition("Ring 2", size=500),
            RingDefinition("Broad", is_remaining=True),
        ],
        shuffle=False,
    )
    counts = result.dataframe[DEFAULT_RING_COLUMN].value_counts().to_dict()
    assert counts == {"Ring 2": 500, "Ring 1": 200, "Broad": 250, "Pilot": 50}
    assert_complete_assignment(df, result.dataframe)


def test_custom_sizes_without_remaining_must_match_population() -> None:
    with pytest.raises(ValueError, match="somme"):
        build_custom_size_rings(devices(20), [RingDefinition("Pilot", size=5)])


def test_exclusions_report_not_found_and_duplicates() -> None:
    df = pd.DataFrame({"DeviceName": ["PC-001", "PC-002", "PC-002", "PC-003"]})
    filtered, excluded, report = apply_exclusions(df, "DeviceName", ["pc-002", "missing"])
    assert list(filtered["DeviceName"]) == ["PC-001", "PC-003"]
    assert len(excluded) == 2
    assert report.requested_count == 2
    assert report.excluded_count == 2
    assert report.not_found == ("missing",)
    assert report.duplicate_values == ("pc-002",)
    assert report.duplicate_rows == 2


def test_stratified_split_keeps_distribution_close() -> None:
    df = devices(1000)
    result = build_equal_rings(df, 5, seed=7, stratify_columns=["Manufacturer"])
    for _, ring_frame in result.dataframe.groupby(DEFAULT_RING_COLUMN):
        distribution = ring_frame["Manufacturer"].value_counts(normalize=True).to_dict()
        assert distribution["Dell"] == pytest.approx(0.30, abs=0.03)
        assert distribution["HP"] == pytest.approx(0.50, abs=0.03)
        assert distribution["Lenovo"] == pytest.approx(0.20, abs=0.03)


def test_seed_stability_and_variation() -> None:
    df = devices(200)
    first = build_equal_rings(df, 4, seed=11).dataframe[["DeviceName", DEFAULT_RING_COLUMN]]
    second = build_equal_rings(df, 4, seed=11).dataframe[["DeviceName", DEFAULT_RING_COLUMN]]
    third = build_equal_rings(df, 4, seed=12).dataframe[["DeviceName", DEFAULT_RING_COLUMN]]
    pd.testing.assert_frame_equal(first, second)
    assert not first.equals(third)


def test_representative_pilot_summary_and_assignment() -> None:
    df = devices(1000)
    result = build_representative_pilot(df, 100, ["Manufacturer", "Site"], seed=9)
    counts = result.dataframe[DEFAULT_RING_COLUMN].value_counts().to_dict()
    assert counts == {"Remaining": 900, "Pilot": 100}
    assert result.pilot_summary is not None
    assert result.pilot_summary.population_rows == 1000
    assert result.pilot_summary.pilot_rows == 100
    assert result.pilot_summary.representativity_score >= 95
    assert result.pilot_summary.coverage_by_column["Manufacturer"] == 100
    assert_complete_assignment(df, result.dataframe)


def test_csv_and_xlsx_import_export_roundtrip(tmp_path) -> None:
    df = devices(12)
    csv_path = tmp_path / "devices.csv"
    xlsx_path = tmp_path / "devices.xlsx"
    df.to_csv(csv_path, index=False, sep=";", encoding="utf-8-sig")
    df.to_excel(xlsx_path, index=False)

    assert len(load_table(csv_path)) == 12
    assert len(load_table(xlsx_path)) == 12

    result = build_equal_rings(df, 3, shuffle=False)
    exported = export_rings(
        result,
        ExportOptions(output_dir=tmp_path, prefix="rings", file_format="csv", split_by_ring=True, include_global=True),
    )
    assert len(exported.paths) == 4
    assert all(path.exists() for path in exported.paths)


def test_export_does_not_overwrite_existing_file(tmp_path) -> None:
    df = devices(6)
    result = build_equal_rings(df, 2, shuffle=False)
    first = export_rings(result, ExportOptions(tmp_path, "deployment", "xlsx"))
    second = export_rings(result, ExportOptions(tmp_path, "deployment", "xlsx"))
    assert set(first.paths).isdisjoint(second.paths)
    assert len(second.paths) == 3
