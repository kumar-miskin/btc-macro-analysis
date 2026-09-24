# btc-macro-analysis

Code and data behind the bitcoin and macro charts posted on X [@KumarMiskin](https://x.com/KumarMiskin).

Every chart that goes up on the timeline gets a folder here with the code that generated it and the data it used, so any number in a post can be checked and reproduced.

## Layout

```
charts/YYYY-MM-DD-<slug>/
  chart.py        (or notebook) - generates the chart
  data/           - input data (CSV/JSON) with source noted
  output/         - the posted PNG
```

## Stack

Python, pandas, matplotlib. Data from free public sources (Farside Investors ETF flows, CoinGlass, FRED, mempool.space, Yahoo Finance); each folder notes its exact source.

Run any chart:

```
pip install -r requirements.txt
python charts/<folder>/chart.py
```

## Checks

`btcmacro/farside.py` parses Farside's ETF flow table and aggregates it into weeks. By default `weekly_totals` drops the last week unless the data reaches its Friday, so a "last week" number is never a week-to-date sum. `pending_funds` lists funds with no figure yet on the latest day, which makes that day's Total provisional.

`scripts/verify_claims.py` recomputes the numbers listed under `posted_claims` in each chart's `manifest.json` from the committed CSVs. It fails on a mismatch and warns when a figure rests on a partial week or a day with funds still pending. CI runs it on every push along with the tests:

```
pip install -r requirements.txt pytest
pytest -q
python scripts/verify_claims.py charts/*/
```
