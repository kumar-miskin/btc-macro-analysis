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
from btcmacro.farside import pending_funds, week_is_complete  # noqa: E402


def check_etf_flows(folder: Path, claims: dict) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    daily = pd.read_csv(folder / "data" / "etf_daily_flows.csv", parse_dates=["date"]).set_index("date")
    weekly = pd.read_csv(folder / "data" / "etf_weekly_flows.csv", parse_dates=["date"]).set_index("date").iloc[:, 0]
    cum = pd.read_csv(folder / "data" / "etf_cumulative_flows.csv", parse_dates=["date"]).set_index("date").iloc[:, 0]

    recomputed_cum = daily["Total"].fillna(0).cumsum()
    if abs(recomputed_cum.iloc[-1] - cum.iloc[-1]) > 0.05:
        errors.append(f"cumulative CSV ends at {cum.iloc[-1]:.1f}, daily totals sum to {recomputed_cum.iloc[-1]:.1f}")

    if "last_week_net_flow_usd_millions" in claims:
        posted = claims["last_week_net_flow_usd_millions"]
        wk_end, wk = weekly.index[-1], weekly.iloc[-1]
        if round(wk) != posted:
            errors.append(f"last_week_net_flow: posted {posted}, data gives {wk:.1f}")
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
