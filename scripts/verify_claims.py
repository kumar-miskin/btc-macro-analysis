"""Recompute the numbers a chart folder's manifest says were posted.

Usage: python scripts/verify_claims.py charts/<folder> [...]

Fails if a posted number does not match the committed data at the precision
it was posted. Prints warnings (without failing) when the data behind a
"last week" figure covered a partial week or a day with funds still pending.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from btcmacro.farside import pending_funds, week_is_complete, weekly_totals  # noqa: E402


def check_etf_flows(folder: Path, claims: dict) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    daily = pd.read_csv(folder / "data" / "etf_daily_flows.csv", parse_dates=["date"]).set_index("date")
    weekly = pd.read_csv(folder / "data" / "etf_weekly_flows.csv", parse_dates=["date"]).set_index("date").iloc[:, 0]
    cum = pd.read_csv(folder / "data" / "etf_cumulative_flows.csv", parse_dates=["date"]).set_index("date").iloc[:, 0]

    # The weekly file is derived data, not independent evidence. Verify every
    # committed bucket against the daily source before trusting a posted claim.
    recomputed_weekly = weekly_totals(daily["Total"], complete_only=False)
    if weekly.index.has_duplicates:
        errors.append("weekly CSV contains duplicate week-end dates")
    if not weekly.index.equals(recomputed_weekly.index):
        missing = recomputed_weekly.index.difference(weekly.index)
        extra = weekly.index.difference(recomputed_weekly.index)
        errors.append(
            "weekly CSV week endings differ from daily totals"
            f" (missing: {missing.strftime('%Y-%m-%d').tolist()},"
            f" extra: {extra.strftime('%Y-%m-%d').tolist()})"
        )
    else:
        mismatch = weekly.isna() | recomputed_weekly.isna() | (weekly - recomputed_weekly).abs().gt(0.05)
        if mismatch.any():
            week = mismatch[mismatch].index[0]
            errors.append(
                f"weekly CSV {week:%Y-%m-%d}: {weekly.loc[week]:.1f},"
                f" daily totals sum to {recomputed_weekly.loc[week]:.1f}"
            )

    recomputed_cum = daily["Total"].fillna(0).cumsum()
    if abs(recomputed_cum.iloc[-1] - cum.iloc[-1]) > 0.05:
        errors.append(f"cumulative CSV ends at {cum.iloc[-1]:.1f}, daily totals sum to {recomputed_cum.iloc[-1]:.1f}")

    if "last_week_net_flow_usd_millions" in claims:
        posted = claims["last_week_net_flow_usd_millions"]
        wk_end, wk = weekly.index[-1], weekly.iloc[-1]
        if not weekly.index.has_duplicates and wk_end in recomputed_weekly.index:
            verified_week = recomputed_weekly.loc[wk_end]
            if round(verified_week) != posted:
                errors.append(f"last_week_net_flow: posted {posted}, daily data gives {verified_week:.1f}")
        elif not weekly.index.has_duplicates:
            errors.append(f"last_week_net_flow: week ending {wk_end:%Y-%m-%d} not in daily data")
        if not week_is_complete(daily["Total"], wk_end):
            days = daily.loc[wk_end - pd.Timedelta(days=6):wk_end].index
            warnings.append(
                f"'last week' figure {wk:.1f} covers only {days.min():%a %b %d}-{days.max():%a %b %d}, "
                f"a partial week ending {wk_end:%b %d}"
            )
    if "cumulative_since_launch_usd_billions" in claims:
        posted = claims["cumulative_since_launch_usd_billions"]
        got = cum.iloc[-1] / 1000
        if round(got, 1) != posted:
            errors.append(f"cumulative_since_launch: posted {posted}B, data gives {got:.2f}B")
    pend = pending_funds(daily)
    if pend:
        warnings.append(f"last day {daily.index[-1]:%b %d} has no figure yet for: {', '.join(pend)}")
    return errors, warnings


CHECKS = {"Farside Investors": check_etf_flows}


def verify(folder: Path) -> tuple[list[str], list[str]]:
    manifest = json.loads((folder / "manifest.json").read_text())
    check = CHECKS.get(manifest.get("source"))
    if check is None:
        return [], [f"no claim check for source {manifest.get('source')!r}"]
    return check(folder, manifest.get("posted_claims", {}))


def main(argv: list[str]) -> int:
    failed = False
    for arg in argv:
        folder = Path(arg)
        errors, warnings = verify(folder)
        for w in warnings:
            print(f"warning {folder.name}: {w}")
        for e in errors:
            print(f"error   {folder.name}: {e}")
        failed |= bool(errors)
        if not errors:
            print(f"ok      {folder.name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
