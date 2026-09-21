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
