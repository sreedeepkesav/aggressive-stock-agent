# Stock Analysis Agent

A modular, quantitative stock analysis tool with 5 analysis engines, market regime detection, adaptive learning, backtesting, and risk management. Runs locally, costs $0/month by default.

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
```

No API keys required for default operation (`LLM_MODE=off`).

## Web Dashboard

```bash
python stock_agent.py web          # Opens browser at http://localhost:8501
python stock_agent.py web 9000     # Custom port
```

The dashboard has 7 pages:

| Page | Description |
|------|-------------|
| **Ticker Analysis** | Regime-aware analysis across 5 engines + multi-timeframe confirmation |
| **Market Scan** | Scans watchlist with regime-adjusted weights, ranked by combined score |
| **Portfolio** | Positions, cash, drawdown, trade history, exit signals |
| **Engine Performance** | Per-engine accuracy tracking, adaptive weights, analysis history |
| **Backtest** | Walk-forward backtesting with equity curve, Sharpe, vs SPY |
| **Discovery** | Reddit trending tickers + RSS news feed |
| **Settings** | Current risk parameters, LLM config, watchlist |

## Terminal CLI

```bash
python stock_agent.py ticker NVDA       # Full analysis (regime + 5 engines + timeframe filter)
python stock_agent.py scan 5            # Scan watchlist, show top 5 opportunities
python stock_agent.py portfolio show    # Portfolio state + active exit signals
python stock_agent.py portfolio stats   # Trade statistics + engine accuracy
python stock_agent.py backtest 12       # Walk-forward backtest over 12 months
python stock_agent.py discovery         # Discover tickers from news + Reddit
python stock_agent.py universe update   # Refresh S&P 500 / momentum / value lists
python stock_agent.py help              # Full help with all env vars
```

Legacy modes (`screen`, `watchlist`, `discover`, `auto`) remain available for backward compatibility.

## Architecture

```
stock_agent.py          # Entry point (routes to web or cli)
app.py                  # Streamlit web dashboard (7 pages)
config/
  settings.py           # All configurable parameters (risk, LLM, watchlist)
  logging_config.py     # Structured logging with file rotation
data/
  indicators.py         # 13 indicators: RSI, SMA, ATR, MACD, BB, OBV, Stochastic,
                        #   VWAP, ROC, BB%B, Keltner Channels, ADL
  market_data.py        # yfinance wrapper with TTL cache + weekly data
  cache.py              # In-memory TTL cache (eliminates redundant API calls)
  news.py               # RSS + yfinance news with deduplication
  sec_edgar.py          # Free SEC EDGAR API (no paid keys needed)
  reddit.py             # Reddit JSON API (no auth needed)
  universe.py           # S&P 500, momentum, value stock lists
engines/
  base.py               # EngineResult dataclass + BaseEngine ABC
  regime.py             # Market regime detection (SPY, VIX, sector breadth)
  momentum.py           # RSI divergence, MACD crossovers, OBV trend, stochastic
  technical.py          # Market structure (HH/HL), false breakout traps, VWAP, Keltner
  sector.py             # Sector ranking (11 sectors), true relative strength, correlation
  mean_reversion.py     # Regime-gated, detrended deviation, exhaustion detection
  fundamental.py        # Sector-relative P/E, ROIC, earnings quality, PEG weighting
  signal_combiner.py    # Regime-aware weighted combination -> trade decision
  timeframe.py          # Multi-timeframe weekly confirmation filter
portfolio/
  models.py             # Position, Trade, Order dataclasses
  state.py              # SQLite persistence (portfolio.db) + learning tables
  risk.py               # Position limits, drawdown breaker, sector caps, exit signals
  tracker.py            # Sharpe ratio, win rate, max drawdown, vs SPY
  exits.py              # Trailing stops, staged profit taking (2R/3R/5R), time exits
  memory.py             # Learning system: save analyses, check outcomes, adaptive weights
  backtest.py           # Walk-forward backtesting framework
cli/
  main.py               # argparse entry point
  display.py            # All formatting and display functions
connectors/
  base.py               # Abstract BrokerConnector interface
  paper.py              # Paper trading (SQLite-backed)
tests/                  # pytest test suite (71 tests)
```

## Signal Flow

```
1. detect_regime()           SPY/VIX/breadth -> TRENDING_UP | TRENDING_DOWN | RANGE_BOUND | HIGH_VOLATILITY
2. engine.analyze()          Each of 5 engines produces EngineResult (signal + confidence + reasons)
3. SignalCombiner.analyze()  Regime-adjusted weights + adaptive weights -> CombinedSignal
4. apply_timeframe_filter()  Weekly trend confirms or demotes daily signal
5. memory.save_analysis()    Save to SQLite for learning
6. memory.check_outcomes()   Fill actual returns after 5+ days -> per-engine accuracy
7. memory.get_adaptive_weights()  Adjust engine weights based on what's actually working
```

## Market Regime Detection

The system classifies market conditions using SPY, VIX, and sector breadth, then adjusts engine weights accordingly:

| Regime | Condition | Momentum | Fundamental | Technical | Sector | Mean Rev |
|--------|-----------|----------|-------------|-----------|--------|----------|
| **Trending Up** | SPY > SMA50 > SMA200, VIX < 25, breadth > 60% | 30% | 20% | 25% | 15% | 10% |
| **Trending Down** | SPY < SMA50 < SMA200, VIX > 20 | 10% | 30% | 15% | 15% | 30% |
| **Range Bound** | Low SMA50 slope, mixed breadth | 15% | 25% | 20% | 10% | 30% |
| **High Volatility** | VIX > 30 or realized vol spike | 10% | 30% | 10% | 20% | 30% |

**Market filters:**
- VIX > 35: all new BUY signals blocked
- SPY down > 3% same day: all confidence reduced by 50%

## Analysis Engines

| Engine | Default Weight | Key Techniques |
|--------|---------------|----------------|
| **Momentum** | 25% | RSI divergence detection, MACD signal crossovers, stochastic RSI, OBV trend, rate of change, relative RSI thresholds |
| **Fundamental** | 25% | Sector-relative P/E (vs sector median), forward P/E, ROIC, earnings quality (OCF > NI), PEG-weighted growth scoring |
| **Technical** | 20% | Market structure (HH/HL), false breakout traps, VWAP as dynamic S/R, ATR-scaled thresholds, Keltner squeeze, BB %B |
| **Sector** | 15% | Sector ranking (top 4 of 11), true relative strength (stock vs sector ETF), SPY correlation check |
| **Mean Reversion** | 15% | Regime-gated activation, detrended deviation (linear regression), stochastic extremes with crossovers, capitulation/exhaustion detection |

## Multi-Timeframe Confirmation

Daily signals are filtered through weekly trend analysis:
- Daily BUY + weekly downtrend: confidence reduced 40%, may demote to HOLD
- Daily SELL + weekly uptrend: confidence reduced 40%, may demote to HOLD
- Daily and weekly agree: confidence boosted 20%

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

Walk-forward backtesting validates the system on historical data:

```bash
python stock_agent.py backtest 12       # 12-month backtest on full watchlist
```

**Metrics:** Total return, Sharpe ratio, max drawdown, win rate, profit factor, excess return vs SPY.

The web dashboard provides an interactive backtest page with equity curve chart and trade-by-trade breakdown.

## Risk Parameters

All risk parameters are configurable via environment variables:

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

Example override:
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
python -m pytest tests/ -v    # 71 tests
```

## Disclaimer

This software is provided "as is" for educational and research purposes only. It is not financial advice. There are no guarantees of returns. Trading stocks involves risk of loss. Always do your own research and consult a licensed financial advisor before making investment decisions.
