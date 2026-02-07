# Stock Analysis Agent

A modular, quantitative stock analysis tool with 5 analysis engines, market regime detection, adaptive learning, backtesting, and risk management. Covers **83 market packages** across **3,800+ symbols** from all major global exchanges. Runs locally, costs $0/month by default.

**This is NOT financial advice.** This tool is for educational and research purposes only. No guarantees of returns.

## Quick Start

```bash
# 1. Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure (optional - works with defaults)
cp .env.example .env

# 3. Launch web dashboard
python stock_agent.py web

# Or use the terminal
python stock_agent.py ticker NVDA
python stock_agent.py scan              # prompts for package selection
python stock_agent.py packages          # list all 83 packages
```

No API keys required for default operation (`LLM_MODE=off`).

## Global Market Coverage

The system organizes **3,800+ symbols** into **83 packages** across 6 regions. You always choose which package to scan - the system never runs all symbols at once.

| Region | Packages | Symbols | Coverage |
|--------|----------|---------|----------|
| **US** | 29 | ~2,900 | S&P 500, NASDAQ 100, Mid/Small/Micro Cap, 18 Sector packages, Dividend Aristocrats, REITs, IPOs |
| **Europe** | 11 | ~625 | UK FTSE, Germany DAX, France CAC 40, Switzerland SMI, Nordic, Netherlands, Spain, Italy, more |
| **Asia-Pacific** | 12 | ~975 | Japan Nikkei/TOPIX, China ADRs + HK, South Korea KOSPI, India NIFTY, Taiwan, Australia ASX, ASEAN |
| **Americas** | 5 | ~270 | Canada TSX, Brazil Ibovespa, Mexico IPC, Latin America |
| **Middle East & Africa** | 2 | ~75 | Saudi, UAE, Qatar, South Africa JSE |
| **Global** | 22 | ~700 | ETFs (Sector, Country, Bond, Commodity, Leveraged), Themes (AI, Cybersecurity, Cannabis, Space, Quantum) |

### Package Commands

```bash
python stock_agent.py packages                      # List all 83 packages with symbol counts
python stock_agent.py scan 10 --package japan        # Scan Japan package, show top 10
python stock_agent.py scan 5 --package sector_semiconductors  # Scan semiconductors
python stock_agent.py scan                           # Interactive prompt to choose a package
python stock_agent.py backtest 12 --package us_mega_cap  # Backtest US mega caps
```

Set default active packages via environment variable:
```bash
ACTIVE_PACKAGES=us_sp500,uk_ftse,japan python stock_agent.py scan
```

## Web Dashboard

```bash
python stock_agent.py web          # Opens browser at http://localhost:8501
python stock_agent.py web 9000     # Custom port
```

The dashboard has 7 pages:

| Page | Description |
|------|-------------|
| **Ticker Analysis** | Regime-aware analysis across 5 engines + multi-timeframe confirmation |
| **Market Scan** | Select a package, scan with regime-adjusted weights, ranked by combined score |
| **Portfolio** | Positions, cash, drawdown, trade history, exit signals |
| **Engine Performance** | Per-engine accuracy tracking, adaptive weights, analysis history |
| **Backtest** | Walk-forward backtesting with equity curve, Sharpe, vs SPY |
| **Discovery** | Reddit trending tickers + RSS news feed |
| **Settings** | LLM mode, risk parameters, API keys, active packages |

## Terminal CLI

```bash
python stock_agent.py ticker NVDA       # Full analysis (regime + 5 engines + timeframe filter)
python stock_agent.py scan              # Interactive package selection, then scan
python stock_agent.py scan 10 -p japan  # Scan Japan package, show top 10
python stock_agent.py packages          # List all 83 packages by region
python stock_agent.py portfolio show    # Portfolio state + active exit signals
python stock_agent.py portfolio stats   # Trade statistics + engine accuracy
python stock_agent.py backtest 12       # Interactive package selection, then backtest
python stock_agent.py backtest 6 -p us_mega_cap  # Backtest specific package (full mode)
python stock_agent.py backtest 6 -p us_mega_cap --fast  # Fast mode (simplified scoring)
python stock_agent.py discovery         # Discover tickers from news + Reddit
python stock_agent.py universe update   # Refresh S&P 500 / momentum / value lists
python stock_agent.py settings          # Interactive settings (LLM, API keys, risk params)
python stock_agent.py help              # Full help with all env vars
```

Legacy modes (`screen`, `watchlist`, `discover`, `auto`) remain available for backward compatibility.

## Architecture

```
stock_agent.py          # Entry point (routes to web or cli)
app.py                  # Streamlit web dashboard (7 pages)
config/
  settings.py           # All configurable parameters (risk, LLM, packages)
  watchlists.py         # 83 packages, 3800+ symbols across all global markets
  logging_config.py     # Structured logging with file rotation
data/
  indicators.py         # 13 indicators: RSI, SMA, ATR, MACD, BB, OBV, Stochastic,
                        #   VWAP, ROC, BB%B, Keltner Channels, ADL
  market_data.py        # yfinance wrapper with TTL cache + weekly data
  cache.py              # In-memory TTL cache (eliminates redundant API calls)
  earnings.py           # Earnings calendar, blackout detection, surprise history
  news.py               # RSS + yfinance news with deduplication
  sec_edgar.py          # Free SEC EDGAR API (no paid keys needed)
  reddit.py             # Reddit JSON API (no auth needed)
  universe.py           # S&P 500, momentum, value stock lists
engines/
  base.py               # EngineResult dataclass + BaseEngine ABC
  regime.py             # Market regime detection (SPY, VIX, breadth + lead indicators)
  momentum.py           # RSI divergence, MACD crossovers, OBV trend, stochastic
  technical.py          # Market structure (HH/HL), false breakout traps, VWAP, Keltner
  sector.py             # Sector ranking (11 sectors), true relative strength, correlation
  mean_reversion.py     # Regime-gated, detrended deviation, exhaustion detection
  fundamental.py        # Sector-relative P/E, ROIC, earnings quality + surprise history, PEG
  signal_combiner.py    # Regime-aware weighted combination + earnings blackout -> trade decision
  timeframe.py          # Multi-timeframe weekly confirmation filter
portfolio/
  models.py             # Position, Trade, Order dataclasses
  state.py              # SQLite persistence (portfolio.db) + learning tables
  risk.py               # Position limits, drawdown breaker, sector caps, exit signals
  tracker.py            # Sharpe ratio, win rate, max drawdown, vs SPY
  exits.py              # Trailing stops, staged profit taking (2R/3R/5R), time exits
  memory.py             # Learning system: save analyses, check outcomes, adaptive weights
  backtest.py           # Walk-forward backtest (full mode: real combiner + costs; fast mode)
cli/
  main.py               # argparse entry point + interactive package prompts
  display.py            # All formatting and display functions
connectors/
  base.py               # Abstract BrokerConnector interface
  paper.py              # Paper trading (SQLite-backed)
tests/                  # pytest test suite (85 tests)
```

## Signal Flow

```
1. detect_regime()           SPY/VIX/breadth + lead indicators (credit, yield curve, VIX term, risk appetite)
                             -> TRENDING_UP | TRENDING_DOWN | RANGE_BOUND | HIGH_VOLATILITY
2. engine.analyze()          Each of 5 engines produces EngineResult (signal + confidence + reasons)
3. SignalCombiner.analyze()  Regime-adjusted weights + adaptive weights + earnings blackout -> CombinedSignal
4. apply_timeframe_filter()  Weekly trend confirms or demotes daily signal
5. memory.save_analysis()    Save to SQLite for learning
6. memory.check_outcomes()   Fill actual returns after 5+ days -> per-engine accuracy
7. memory.get_adaptive_weights()  Adjust engine weights based on what's actually working
```

## Market Regime Detection

The system classifies market conditions using SPY, VIX, sector breadth, and **4 lead indicators** that provide 1-3 week early warnings:

| Regime | Condition | Momentum | Fundamental | Technical | Sector | Mean Rev |
|--------|-----------|----------|-------------|-----------|--------|----------|
| **Trending Up** | SPY > SMA50 > SMA200, VIX < 25, breadth > 60% | 30% | 20% | 25% | 15% | 10% |
| **Trending Down** | SPY < SMA50 < SMA200, VIX > 20 | 10% | 30% | 15% | 15% | 30% |
| **Range Bound** | Low SMA50 slope, mixed breadth | 15% | 25% | 20% | 10% | 30% |
| **High Volatility** | VIX > 30 or realized vol spike | 10% | 30% | 10% | 20% | 30% |

**Lead indicators** (can upgrade severity, never downgrade):

| Indicator | Source | Signal |
|-----------|--------|--------|
| **Credit Stress** | HYG/LQD ratio | Declining ratio = credit deterioration, early warning |
| **Yield Curve** | ^TNX - ^IRX spread | Inverted = recession risk, rapid steepening = rate shock |
| **VIX Term Structure** | ^VIX / ^VIX3M | Backwardation (>1.0) = panic, contango (<0.85) = complacent |
| **Risk Appetite** | GLD/SPY ratio trend | Rising = risk-off rotation into gold |

**Market filters:**
- VIX > 35: all new BUY signals blocked
- SPY down > 3% same day: all confidence reduced by 50%
- Credit deteriorating + VIX backwardation: extra 20% confidence dampening

## Analysis Engines

| Engine | Default Weight | Key Techniques |
|--------|---------------|----------------|
| **Momentum** | 25% | RSI divergence detection, MACD signal crossovers, stochastic RSI, OBV trend, rate of change, relative RSI thresholds |
| **Fundamental** | 25% | Sector-relative P/E (vs sector median), forward P/E, ROIC, earnings quality (OCF > NI), PEG-weighted growth, earnings surprise history |
| **Technical** | 20% | Market structure (HH/HL), false breakout traps, VWAP as dynamic S/R, ATR-scaled thresholds, Keltner squeeze, BB %B |
| **Sector** | 15% | Sector ranking (top 4 of 11), true relative strength (stock vs sector ETF), SPY correlation check |
| **Mean Reversion** | 15% | Regime-gated activation, detrended deviation (linear regression), stochastic extremes with crossovers, capitulation/exhaustion detection |

## Multi-Timeframe Confirmation

Daily signals are filtered through weekly trend analysis:
- Daily BUY + weekly downtrend: confidence reduced 40%, may demote to HOLD
- Daily SELL + weekly uptrend: confidence reduced 40%, may demote to HOLD
- Daily and weekly agree: confidence boosted 20%

## Earnings Calendar Awareness

The system detects upcoming earnings dates and suppresses signals during binary events:

- **Blackout window** (3 days before, 1 day after): BUY/STRONG_BUY demoted to HOLD, confidence reduced 70%
- **Warning zone** (4-10 days before): informational note added to reasons
- **Earnings quality**: beat rate >75% boosts fundamental score; negative surprise trend penalizes it
- Data sourced from yfinance earnings calendar and historical surprise data

## Learning System

The system improves over time:
1. Every analysis is saved to SQLite with per-engine signals
2. After 5+ trading days, actual outcomes are recorded (price return, signal correctness)
3. Rolling 90-day accuracy is computed per engine
4. Adaptive weights boost engines above 50% accuracy, reduce those below
5. Weights blend: 70% adaptive + 30% regime (prevents wild swings, cold-start safe)

## Trailing Stops & Dynamic Exits

| Exit Type | Trigger | Action |
|-----------|---------|--------|
| **Trailing Stop** | Price < HWM - ATR * multiplier | Full exit. Multiplier tightens: 2.5 ATR -> 2.0 at 2R -> 1.5 at 3R |
| **Profit Take (2R)** | Profit = 2x initial risk | Close 33%, move stop to breakeven |
| **Profit Take (3R)** | Profit = 3x initial risk | Close 33%, tighten stop to 1.5 ATR |
| **Profit Take (5R)** | Profit = 5x initial risk | Close remaining position |
| **Time Exit** | Held > 20 trading days, < 2% gain | Full exit (dead money) |

## Backtesting

Walk-forward backtesting with two modes:

```bash
python stock_agent.py backtest 12 --package us_mega_cap          # Full mode (real combiner)
python stock_agent.py backtest 12 --package us_mega_cap --fast   # Fast mode (simplified scoring)
python stock_agent.py backtest 12                                 # Interactive package prompt
```

| Mode | Entry Logic | Exit Rules | Costs | Speed |
|------|------------|------------|-------|-------|
| **Full** (default) | Real 5-engine SignalCombiner + earnings blackout | Trailing stop (HWM - ATR), staged profit at 2R/3R/5R, time exit | 0.1% slippage + $1 commission per side | ~1-2s per signal |
| **Fast** (`--fast`) | Simplified indicator scoring (_quick_score) | Same exit rules, no costs | None | Instant |

**Metrics:** Total return, Sharpe ratio, max drawdown, win rate, profit factor, excess return vs SPY, total trading costs, per-regime win rate breakdown.

The web dashboard provides a fast/full toggle, equity curve chart, regime breakdown table, and per-trade cost details.

## Risk Parameters

All risk parameters are configurable via environment variables or the interactive settings prompt:

| Parameter | Env Var | Default | Description |
|-----------|---------|---------|-------------|
| Max Position | `MAX_POSITION_PCT` | 10% | Max allocation per position |
| Portfolio Heat | `MAX_PORTFOLIO_HEAT` | 8% | Max total portfolio risk |
| Drawdown Breaker | `DRAWDOWN_CIRCUIT_BREAKER` | -10% | Stop trading at this drawdown from peak |
| Max Positions | `MAX_SIMULTANEOUS_POSITIONS` | 5 | Max number of open positions |
| Sector Cap | `MAX_SECTOR_CONCENTRATION` | 40% | Max allocation to one sector |
| Cash Reserve | `CASH_RESERVE_PCT` | 20% | Minimum cash reserve |
| Daily Risk | `MAX_DAILY_RISK` | 5% | Daily risk tolerance |
| Profit Target | `MIN_PROFIT_TARGET` | 8% | Minimum profit target |
| Swing Stop | `STOP_LOSS_ATR_SWING` | 2.0 ATR | Stop loss for swing trades |
| Position Stop | `STOP_LOSS_ATR_POSITION` | 2.5 ATR | Stop loss for position trades |

Configure via terminal or web:
```bash
python stock_agent.py settings    # Interactive prompt (LLM, API keys, risk params)
python stock_agent.py web         # Settings page in web dashboard
```

Or via environment:
```bash
MAX_POSITION_PCT=0.15 MAX_SIMULTANEOUS_POSITIONS=3 python stock_agent.py ticker NVDA
```

## LLM Cost Control

| Mode | Env Var | Cost | Description |
|------|---------|------|-------------|
| Off (default) | `LLM_MODE=off` | $0/month | Pure algorithmic analysis |
| Haiku | `LLM_MODE=haiku` | ~$0.0003/run | AI summaries |
| Sonnet | `LLM_MODE=sonnet` | ~$0.01/run | Deep AI analysis |

`ANTHROPIC_API_KEY` is only needed when `LLM_MODE` is not `off`.

## Tests

```bash
pip install pytest
python -m pytest tests/ -v    # 85 tests
```

## Disclaimer

This software is provided "as is" for educational and research purposes only. It is not financial advice. There are no guarantees of returns. Trading stocks involves risk of loss. Always do your own research and consult a licensed financial advisor before making investment decisions.
