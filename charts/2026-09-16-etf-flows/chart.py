import requests, pandas as pd, numpy as np, re, time
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams["text.parse_math"] = False

UA = {"User-Agent": "Mozilla/5.0 (compatible; btc-twitter-charts/1.0)"}
ORANGE, GREEN, RED, GREY = "#f7931a", "#26a69a", "#ef5350", "#9aa0a6"

def get_json(url, params=None, tries=6, timeout=40):
    """GET JSON with backoff for CoinGecko-style 429 rate limits."""
    r = None
    for i in range(tries):
        r = requests.get(url, params=params, headers=UA, timeout=timeout)
        if r.status_code == 429:
            time.sleep(5 * (i + 1))
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()

def new_ax(figsize=(12, 6.5)):
    fig, ax = plt.subplots(figsize=figsize, dpi=160)
    fig.patch.set_facecolor("#0e1117")
    ax.set_facecolor("#0e1117")
    for s in ax.spines.values():
        s.set_color("#3a3f4b")
    ax.tick_params(colors=GREY, labelsize=10)
    ax.grid(True, color="#2a2f3a", linewidth=0.7, alpha=0.8)
    ax.title.set_color("white")
    return fig, ax

def finish(fig, ax, title, subtitle, source, fname):
    ax.set_title(title + "\n", fontsize=16, fontweight="bold", loc="left", pad=22, color="white")
    ax.annotate(subtitle, xy=(0, 1.02), xycoords="axes fraction",
                fontsize=10, color=GREY, va="bottom")
    fig.text(0.99, 0.01, source, ha="right", fontsize=8, color=GREY)
    fig.text(0.01, 0.01, "Not financial advice", ha="left", fontsize=8, color=GREY)
    fig.tight_layout()
    fig.savefig(fname, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.show()
    print("saved:", fname)

def ordinal(n):
    n = int(round(n))
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"

def money_m(v):
    return f"-${abs(v):,.0f}M" if v < 0 else f"${v:,.0f}M"

print("setup ok")


r = requests.get("https://r.jina.ai/https://farside.co.uk/bitcoin-etf-flow-all-data/",
                 headers=UA, timeout=90)
r.raise_for_status()
lines = [l for l in r.text.splitlines() if l.startswith("| ")]

def fnum(x):
    x = x.replace(",", "")
    if x in ("-", ""):
        return np.nan
    neg = x.startswith("(") and x.endswith(")")
    try:
        v = float(x.strip("()"))
    except ValueError:
        return np.nan
    return -v if neg else v

recs = []
for l in lines:
    cells = [c.strip() for c in l.strip("|").split("|")]
    if not re.match(r"^\d{2} \w{3} \d{4}$", cells[0]):
        continue
    recs.append([pd.to_datetime(cells[0], format="%d %b %Y"), fnum(cells[1]), fnum(cells[-1])])
flows = pd.DataFrame(recs, columns=["date", "IBIT", "Total"]).set_index("date").sort_index()

weekly = flows.Total.resample("W").sum().dropna()
cum = flows.Total.fillna(0).cumsum()

fig, (ax, ax2) = plt.subplots(2, 1, figsize=(12, 7.5), dpi=160, sharex=True,
                              gridspec_kw={"height_ratios": [1, 1.2], "hspace": 0.12})
for a in (ax, ax2):
    a.set_facecolor("#0e1117")
    for s in a.spines.values():
        s.set_color("#3a3f4b")
    a.tick_params(colors=GREY, labelsize=10)
    a.grid(True, color="#2a2f3a", linewidth=0.7, alpha=0.8)
fig.patch.set_facecolor("#0e1117")

ax.plot(cum.index, cum, color=ORANGE, lw=1.8)
ax.fill_between(cum.index, cum, color=ORANGE, alpha=0.12)
ax.yaxis.set_major_formatter(lambda x, _: f"${x/1000:,.0f}B")
ax.set_ylabel("Cumulative", color=GREY)

colors = [GREEN if v >= 0 else RED for v in weekly]
ax2.bar(weekly.index, weekly, width=5.5, color=colors)
ax2.axhline(0, color="#3a3f4b", lw=0.8)
ax2.yaxis.set_major_formatter(lambda x, _: f"{x:,.0f}")
ax2.set_ylabel("Weekly net flow ($M)", color=GREY)

wk = weekly.iloc[-1]
finish(fig, ax, f"Bitcoin ETF flows: {money_m(wk)} last week",
       f"All US spot bitcoin ETFs: cumulative ${cum.iloc[-1]/1000:,.1f}B since Jan 2024 launch  |  {weekly.index[-1]:%b %d, %Y}",
       "Source: Farside Investors", "2_etf_flows.png")

print(f"Tweet idea: US spot bitcoin ETFs saw {money_m(wk)} in net flows last week. Cumulative since launch: ${cum.iloc[-1]/1000:,.1f}B.")


flows.to_csv("etf_daily_flows.csv")
weekly.rename("weekly_total_usd_millions").to_csv("etf_weekly_flows.csv")
cum.rename("cumulative_total_usd_millions").to_csv("etf_cumulative_flows.csv")
