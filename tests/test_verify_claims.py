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
