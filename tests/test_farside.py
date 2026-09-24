from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from btcmacro.farside import (
    parse_number, parse_table, pending_funds, week_is_complete, weekly_totals,
)

FIXTURE = (Path(__file__).parent / "fixtures" / "farside_sample.md").read_text()


@pytest.mark.parametrize("cell,expected", [("1,234.5", 1234.5), ("(12.3)", -12.3), ("0.0", 0.0)])
def test_parse_number(cell, expected):
    assert parse_number(cell) == expected


@pytest.mark.parametrize("cell", ["-", "", "n/a"])
def test_parse_number_missing(cell):
    assert np.isnan(parse_number(cell))


def test_parse_table_drops_summary_rows_and_keeps_funds():
    df = parse_table(FIXTURE)
    assert list(df.columns) == ["IBIT", "FBTC", "GBTC", "Total"]
    assert df.index.min() == pd.Timestamp("2026-09-08")
    assert df.index.max() == pd.Timestamp("2026-09-16")
    assert df.loc["2026-09-15", "Total"] == pytest.approx(-450.4)
    assert np.isnan(df.loc["2026-09-16", "IBIT"])


def test_parse_table_rejects_ragged_rows():
    bad = FIXTURE.replace("| 14 Sep 2026 | 134.3 |", "| 14 Sep 2026 |")
    with pytest.raises(ValueError, match="header width"):
        parse_table(bad)


def test_pending_funds_flags_missing_latest_report():
    df = parse_table(FIXTURE)
    assert pending_funds(df) == ["IBIT"]
    # GBTC was "-" on the 11th after reporting on the 10th
    assert pending_funds(df, "2026-09-11") == ["GBTC"]


def test_weekly_totals_drops_partial_last_week():
    total = parse_table(FIXTURE)["Total"]
    full = weekly_totals(total, complete_only=False)
    assert full.index[-1] == pd.Timestamp("2026-09-20")
    assert full.iloc[-1] == pytest.approx(159.9 - 450.4 - 151.8)
    done = weekly_totals(total)
    assert done.index[-1] == pd.Timestamp("2026-09-13")
    assert done.iloc[-1] == pytest.approx(-462.7)
    assert not week_is_complete(total, "2026-09-20")
    assert week_is_complete(total, "2026-09-13")


def test_week_through_friday_counts_as_complete():
    idx = pd.bdate_range("2026-09-14", "2026-09-18")
    total = pd.Series(1.0, index=idx)
    assert weekly_totals(total).iloc[-1] == 5.0
