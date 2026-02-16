<div align="center">

# Stock Analysis Agent

**Quantitative stock analysis with 5 engines, regime detection, adaptive learning, and paper trading**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/streamlit-dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Cost](https://img.shields.io/badge/cost-%240%2Fmonth-brightgreen?style=for-the-badge)]()

<br>

83 market packages &bull; 3,800+ symbols &bull; 6 global regions &bull; runs 100% local

<br>

> **This is NOT financial advice.** Educational and research purposes only. No guarantees of returns.

</div>

<br>

## Highlights

<table>
<tr>
<td width="50%">

**5 Analysis Engines**
Momentum, Fundamental, Technical, Sector Rotation, and Mean Reversion — each regime-aware with adaptive weighting that learns from outcomes.

</td>
<td width="50%">

**Market Regime Detection**
Classifies markets as Trending Up/Down, Range-Bound, or High Volatility using SPY, VIX, breadth, and 4 lead indicators for early warnings.

</td>
</tr>
<tr>
<td width="50%">

**Paper Trading + Kelly Sizing**
Prove your edge with virtual money before risking capital. Half-Kelly position sizing, automatic stop losses, staged profit taking.

</td>
<td width="50%">

**Self-Improving System**
Every analysis feeds a learning database. After 30 days, adaptive weights automatically boost engines that perform and reduce those that don't.

</td>
</tr>
</table>

<br>

## Quick Start

```bash
git clone https://github.com/sreedeepkesav/aggressive-stock-agent.git
cd aggressive-stock-agent

python3 -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate           # Windows

pip install -r requirements.txt
cp .env.example .env              # works out of the box (LLM_MODE=off, $0 cost)

streamlit run app.py              # launch dashboard at localhost:8501
```

No API keys needed. Zero cost by default.

<br>

## Table of Contents

- [Dashboard](#dashboard)
- [CLI Usage](#cli-usage)
- [Paper Trading](#paper-trading)
- [API Keys](#api-keys-optional)
- [Regime Alerts](#regime-change-alerts)
- [Risk Parameters](#risk-parameters)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [Development Phases](#development-phases)

<br>

---

<br>

## Dashboard

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. Dark theme with regime-colored banners, Altair charts, and gradient metric cards.

| Page | What it does |
|:-----|:------------|
| **Dashboard** | Regime status, engine accuracy chart, confidence calibration curve, regime change log |
| **Analyze** | Deep-dive a single ticker across all 5 engines. Insider activity panel, risk assessment |
| **Scan** | Scan any of the 83 watchlist packages. Filter by confidence, agreement, actionability |
| **Paper Trade** | Virtual trading with equity curve, run cycles, full trade log, engine attribution |
| **Portfolio** | Live positions, trade history, exit signals with urgency levels |
| **Backtest** | Walk-forward backtesting — fast mode (instant) or full mode (real combiner + costs) |
| **Discover** | Reddit trending tickers + RSS financial news |
| **Settings** | LLM mode, risk params, API keys, alert config (email / webhook) |

<br>

---

<br>

## CLI Usage

```bash
python stock_agent.py ticker NVDA                          # full analysis on a ticker
python stock_agent.py scan 10 --package mega_cap_tech      # scan top 10 from a package
python stock_agent.py packages                             # list all 83 packages
python stock_agent.py backtest 12 --package mega_cap_tech  # 12-month backtest (full)
python stock_agent.py backtest 12 -p mega_cap_tech --fast  # fast backtest (instant)
python stock_agent.py portfolio show                       # positions + exit signals
python stock_agent.py portfolio stats                      # trade stats + engine accuracy
python stock_agent.py discovery                            # reddit + news
python stock_agent.py settings                             # configure interactively
```

<br>

---

<br>

## Paper Trading

Prove the system works with real market data and virtual money before putting capital at risk.

```bash
python -m portfolio.paper_trader                                # trade active watchlist
python -m portfolio.paper_trader --symbols NVDA AAPL MSFT      # specific symbols
python -m portfolio.paper_trader --package mega_cap_tech        # trade a package
python -m portfolio.paper_trader --summary                      # view performance
```

**Position sizing** uses half-Kelly criterion (clamped to 25% max per position). Falls back to 1% risk when fewer than 10 trades in history.

**Exit rules:** trailing stop (ATR-based), staged profit taking at 2R/3R/5R, time exit at 30 days.

<details>
<summary><strong>Automate with cron (recommended)</strong></summary>

<br>

Run paper trading + learning seeder every weekday at 6 PM EST:

```bash
crontab -e
```

```cron
# Seed learning system (builds data for adaptive weights)
0 18 * * 1-5 cd /path/to/aggressive-stock-agent && venv/bin/python seed_learning.py >> logs/seed.log 2>&1

# Paper trading cycle
30 18 * * 1-5 cd /path/to/aggressive-stock-agent && venv/bin/python -m portfolio.paper_trader >> logs/paper_trade.log 2>&1
```

After 30+ days, the adaptive weight system kicks in automatically.

</details>

<br>

---

<br>

## API Keys (Optional)

Set in `.env`. **None required** for basic operation.

| Key | Purpose | Cost |
|:----|:--------|:-----|
| `ALPHA_VANTAGE_API_KEY` | Auto-fallback when Yahoo Finance fails | Free (25/day) |
| `ANTHROPIC_API_KEY` | AI-powered analysis summaries | ~$0.01/run |
| `SEC_API_KEY` | Enhanced SEC filing data | Free |
| `REDDIT_CLIENT_ID` / `SECRET` | Reddit ticker discovery | Free |

<details>
<summary><strong>Where to get each key</strong></summary>

<br>

- **Alpha Vantage:** [alphavantage.co/support/#api-key](https://www.alphavantage.co/support/#api-key)
- **Anthropic:** [console.anthropic.com](https://console.anthropic.com/)
- **SEC API:** [sec-api.io](https://sec-api.io/)
- **Reddit:** [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)

</details>

<br>

To enable AI summaries:

```env
LLM_MODE=haiku    # cheap summaries (~$0.0003/run)
LLM_MODE=sonnet   # deep analysis (~$0.01/run)
```

<br>

---

<br>

## Regime Change Alerts

Get notified when the market regime shifts (e.g., `TRENDING_UP` -> `HIGH_VOLATILITY`).

Configure in **Settings > Alerts** or in `.env`:

```env
# Email
ALERT_EMAIL_TO=you@example.com
ALERT_SMTP_HOST=smtp.gmail.com
ALERT_SMTP_PORT=587
ALERT_SMTP_USER=you@gmail.com
ALERT_SMTP_PASS=your-app-password

# Webhook (Slack, Discord, Telegram)
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/...
```

<br>

---

<br>

## Risk Parameters

All tunable via `.env` or the Settings page. Defaults are conservative:

| Parameter | Default | What it controls |
|:----------|:--------|:----------------|
| `MAX_POSITION_PCT` | 10% | Max allocation per position |
| `MAX_PORTFOLIO_HEAT` | 8% | Max total portfolio at risk |
| `DRAWDOWN_CIRCUIT_BREAKER` | -10% | Halts all trading at this drawdown |
| `MAX_SIMULTANEOUS_POSITIONS` | 5 | Position count limit |
| `MAX_SECTOR_CONCENTRATION` | 40% | Max in one sector |
| `CASH_RESERVE_PCT` | 20% | Minimum cash reserve |
| `MAX_POSITION_CORRELATION` | 0.75 | Reject correlated positions |

<br>

---

<br>

## Architecture

```
stock_agent.py              Entry point
app.py                      Streamlit dashboard (8 pages, dark theme)
seed_learning.py            Daily learning seeder (cron-ready)

engines/
  signal_combiner.py        Regime-weighted combination of 5 engines
  momentum.py               RSI divergence, MACD, OBV, stochastic
  technical.py              Market structure, VWAP, Keltner, Bollinger
  fundamental.py            Dynamic sector P/E, ROIC, earnings quality
  sector.py                 Sector rotation, relative strength
  mean_reversion.py         Regime-gated oversold/overbought detection
  regime.py                 VIX, breadth, credit stress, yield curve
  timeframe.py              Weekly confirmation filter

portfolio/
  paper_trader.py           Paper trading + Kelly criterion sizing
  backtest.py               Walk-forward backtester (lookahead-free)
  risk.py                   Position limits, correlation, drawdown breaker
  memory.py                 Adaptive learning: predictions -> outcomes -> weights
  calibration.py            Confidence calibration (predicted vs actual)
  attribution.py            Per-engine contribution analysis
  tracker.py                Sharpe, win rate, vs SPY benchmarking
  state.py                  SQLite persistence layer
  exits.py                  Trailing stops, staged profit taking, time exits

data/
  market_data.py            yfinance + Alpha Vantage fallback
  alpha_vantage.py          Secondary data source (25 free calls/day)
  insider_signal.py         SEC EDGAR Form 4 insider analysis
  indicators.py             RSI, SMA, EMA, MACD, ATR, BB, OBV, ADX
  sector_cache.py           Dynamic sector median P/E from ETFs
  sec_edgar.py              SEC filing search
  earnings.py               Earnings calendar + blackout windows
  news.py                   RSS financial news
  reddit.py                 Reddit ticker mentions

alerts/
  regime_alerts.py          Regime change detection + email/webhook dispatch

config/
  settings.py               All configuration (env vars)
  watchlists.py             83 packages, 3800+ symbols
```

<details>
<summary><strong>Signal flow</strong></summary>

<br>

```
detect_regime()              SPY/VIX/breadth + 4 lead indicators
       |                     -> TRENDING_UP | TRENDING_DOWN | RANGE_BOUND | HIGH_VOLATILITY
       v
engine.analyze()             Each of 5 engines -> signal + confidence + reasons
       |
       v
SignalCombiner.analyze()     Regime-adjusted weights + adaptive weights + earnings blackout
       |
       v
apply_timeframe_filter()     Weekly trend confirms or demotes daily signal
       |
       v
memory.save_analysis()       Save to SQLite for learning
       |
       v
memory.check_outcomes()      Fill actual returns after 5+ days
       |
       v
get_adaptive_weights()       Engines that work get more weight, those that don't get less
```

</details>

<details>
<summary><strong>Market regime weights</strong></summary>

<br>

| Regime | Momentum | Fundamental | Technical | Sector | Mean Rev |
|:-------|:--------:|:-----------:|:---------:|:------:|:--------:|
| Trending Up | 30% | 20% | 25% | 15% | 10% |
| Trending Down | 10% | 30% | 15% | 15% | 30% |
| Range Bound | 15% | 25% | 20% | 10% | 30% |
| High Volatility | 10% | 30% | 10% | 20% | 30% |

</details>

<details>
<summary><strong>Global market coverage</strong></summary>

<br>

| Region | Packages | Symbols | Examples |
|:-------|:--------:|:-------:|:--------|
| US | 29 | ~2,900 | S&P 500, NASDAQ 100, 18 sector packages, Dividend Aristocrats |
| Europe | 11 | ~625 | FTSE, DAX, CAC 40, SMI, Nordic |
| Asia-Pacific | 12 | ~975 | Nikkei, KOSPI, NIFTY, Taiwan, ASX |
| Americas | 5 | ~270 | TSX, Ibovespa, IPC |
| Middle East & Africa | 2 | ~75 | Saudi, UAE, South Africa JSE |
| Thematic | 22 | ~700 | AI/ML, Cybersecurity, Space, Quantum, Cannabis |

</details>

<br>

---

<br>

## Troubleshooting

<details>
<summary><code>ModuleNotFoundError: No module named 'yfinance'</code></summary>

<br>

You're not in the venv. Run `source venv/bin/activate` first.

</details>

<details>
<summary><code>streamlit: command not found</code></summary>

<br>

Same thing — activate the venv, or run `venv/bin/streamlit run app.py` directly.

</details>

<details>
<summary><strong>Yahoo Finance returns empty data</strong></summary>

<br>

Yahoo rate-limits aggressive usage. Set `ALPHA_VANTAGE_API_KEY` in `.env` for automatic fallback. Or wait a few minutes and retry.

</details>

<details>
<summary><code>portfolio.db is locked</code></summary>

<br>

Another process is using it. Kill any running streamlit or python processes.

</details>

<details>
<summary><strong>Dashboard has import errors</strong></summary>

<br>

Make sure you're on the latest commit:

```bash
git pull && pip install -r requirements.txt --upgrade
```

</details>

<br>

---

<br>

## Development Phases

| Phase | Focus | Key Changes |
|:------|:------|:------------|
| **Phase 1** | Fix The Foundation | Backtester lookahead fix, monolith removal, correlation risk checks, dynamic sector P/E |
| **Phase 2** | Build The Trust Layer | Dashboard UI overhaul, Alpha Vantage fallback, confidence calibration, regime alerting, learning seeder |
| **Phase 3** | Develop Real Edge | Paper trading with Kelly criterion, SEC insider signals, performance attribution, engine agreement analysis |

<br>

---

<br>

<div align="center">

**The system is designed to prove itself before you put money in.**

Run paper trading for 30+ days. Watch the dashboard. Let the data tell you if it works.

<br>

*This software is for educational and research purposes only. Not financial advice. Trading involves risk of loss. Always consult a licensed financial advisor.*

</div>
