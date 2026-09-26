import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_claims  # noqa: E402

CHART = ROOT / "charts" / "2026-09-16-etf-flows"


def test_posted_numbers_match_committed_data():
    errors, warnings = verify_claims.verify(CHART)
    assert errors == []
    assert any("partial week" in w for w in warnings)


def test_mismatched_claim_fails(tmp_path):
    folder = tmp_path / CHART.name
    shutil.copytree(CHART, folder)
    m = json.loads((folder / "manifest.json").read_text())
    m["posted_claims"]["cumulative_since_launch_usd_billions"] = 60.0
    (folder / "manifest.json").write_text(json.dumps(m))
    errors, _ = verify_claims.verify(folder)
    assert any("cumulative_since_launch" in e for e in errors)


def test_weekly_claim_cannot_be_validated_by_an_unchecked_weekly_csv(tmp_path):
    folder = tmp_path / CHART.name
    shutil.copytree(CHART, folder)
    weekly_path = folder / "data" / "etf_weekly_flows.csv"
    import pandas as pd
    weekly = pd.read_csv(weekly_path)
    weekly.iloc[-1, 1] = -400.0
    weekly.to_csv(weekly_path, index=False)
    claims = json.loads((folder / "manifest.json").read_text())
    claims["posted_claims"]["last_week_net_flow_usd_millions"] = -400
    (folder / "manifest.json").write_text(json.dumps(claims))
    errors, _ = verify_claims.verify(folder)
    assert any("weekly CSV" in error and "daily totals sum to" in error for error in errors)


def test_missing_week_or_duplicate_week_is_rejected(tmp_path):
    import pandas as pd
    folder = tmp_path / CHART.name
    shutil.copytree(CHART, folder)
    weekly_path = folder / "data" / "etf_weekly_flows.csv"
    original = pd.read_csv(weekly_path)
    original.drop(index=4).to_csv(weekly_path, index=False)
    errors, _ = verify_claims.verify(folder)
    assert any("week endings differ" in error for error in errors)
    pd.concat([original, original.iloc[[4]]], ignore_index=True).to_csv(weekly_path, index=False)
    errors, _ = verify_claims.verify(folder)
    assert any("duplicate week-end" in error for error in errors)
