"""Parse Farside Investors' bitcoin ETF flow table and aggregate it safely.

Farside publishes one row per US trading day, one column per fund and a
Total column, in USD millions. Outflows are written in parentheses and funds
that have not reported yet show "-". Two things are easy to get wrong:

* A "-" in a fund column on the latest row usually means "not reported yet",
  not zero, so that day's Total is provisional.
* pandas' weekly resample labels a week by its Sunday, so the last bucket is a
  partial week whenever the data ends before Friday.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

DATE_RE = re.compile(r"^\d{2} \w{3} \d{4}$")


def parse_number(cell: str) -> float:
    """'1,234.5' -> 1234.5, '(12.3)' -> -12.3, '-' or '' -> NaN."""
    x = cell.strip().replace(",", "")
    if x in ("-", ""):
        return np.nan
    neg = x.startswith("(") and x.endswith(")")
    try:
        v = float(x.strip("()"))
    except ValueError:
        return np.nan
    return -v if neg else v


def parse_table(markdown: str) -> pd.DataFrame:
    """Return daily flows indexed by date: one column per fund plus Total.

    Header and summary rows (Total, Average, Maximum, Minimum) are dropped
    because their first cell is not a date.
    """
    rows = [l for l in markdown.splitlines() if l.startswith("|")]
    header = None
    recs = []
    for line in rows:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None and "Total" in cells:
            header = cells
            continue
        if not cells or not DATE_RE.match(cells[0]):
            continue
        if header is None or len(cells) != len(header):
            raise ValueError(f"row does not match header width: {line!r}")
        recs.append([pd.to_datetime(cells[0], format="%d %b %Y")] + [parse_number(c) for c in cells[1:]])
    if header is None:
        raise ValueError("no header row with a Total column found")
    cols = ["date"] + header[1:]
    df = pd.DataFrame(recs, columns=cols).set_index("date").sort_index()
    if df.index.duplicated().any():
        raise ValueError("duplicate dates in Farside table")
    return df


def pending_funds(daily: pd.DataFrame, day=None) -> list[str]:
    """Funds with no figure on `day` (default: last row) though they reported the day before."""
    fund_cols = [c for c in daily.columns if c != "Total"]
    if len(daily) < 2:
        return []
    day = daily.index[-1] if day is None else pd.Timestamp(day)
    pos = daily.index.get_loc(day)
    if pos == 0:
        return []
    today, prev = daily.iloc[pos], daily.iloc[pos - 1]
    return [c for c in fund_cols if pd.isna(today[c]) and not pd.isna(prev[c])]


def weekly_totals(total: pd.Series, *, complete_only: bool = True) -> pd.Series:
    """Sum daily totals into Monday-Sunday weeks labeled by their Sunday.

    With complete_only (the default) the last week is dropped unless the data
    reaches that week's Friday, so "last week" never means "week to date".
    """
    total = total.sort_index()
    weekly = total.resample("W-SUN").sum(min_count=1).dropna()
    if complete_only and len(weekly):
        last_day = total.index.max()
        friday = weekly.index[-1] - pd.Timedelta(days=2)
        if last_day < friday:
            weekly = weekly.iloc[:-1]
    return weekly


def week_is_complete(total: pd.Series, week_ending) -> bool:
    week_ending = pd.Timestamp(week_ending)
    return total.index.max() >= week_ending - pd.Timedelta(days=2)
