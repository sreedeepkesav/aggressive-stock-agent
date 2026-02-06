# Stock Analysis Agent

A modular, professional stock analysis tool with 5 analysis engines, signal combination, risk management, and portfolio tracking. Runs locally, costs $0/month by default.

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

The dashboard has 5 pages:

| Page | Description |
|------|-------------|
| **Ticker Analysis** | Enter a symbol, runs all 5 engines, shows combined signal + risk check |
| **Market Scan** | Scans watchlist with progress bar, ranked table of opportunities |
| **Portfolio** | Positions, cash, drawdown, trade history, Sharpe ratio, vs SPY |
| **Discovery** | Reddit trending tickers + RSS news feed |
| **Settings** | Current risk parameters, LLM config, watchlist |

## Terminal CLI

```bash
python stock_agent.py ticker NVDA       # Full analysis (5 engines + signal combiner)
python stock_agent.py scan 5            # Scan watchlist, show top 5 opportunities
python stock_agent.py portfolio show    # Portfolio state (positions, cash, drawdown)
python stock_agent.py portfolio stats   # Trade statistics (Sharpe, win rate, vs SPY)
python stock_agent.py discovery         # Discover tickers from news + Reddit
python stock_agent.py universe update   # Refresh S&P 500 / momentum / value lists
python stock_agent.py help              # Full help with all env vars
```

Legacy modes (`screen`, `watchlist`, `discover`, `auto`) remain available for backward compatibility.

## Architecture

```
stock_agent.py          # Entry point (routes to web or cli)
app.py                  # Streamlit web dashboard
config/
  settings.py           # All configurable parameters (risk, LLM, watchlist)
  logging_config.py     # Structured logging with file rotation
data/
  indicators.py         # ONE canonical RSI, SMA, ATR, MACD, BB, OBV
  market_data.py        # yfinance wrapper with TTL cache
  cache.py              # In-memory TTL cache (eliminates redundant API calls)
  news.py               # RSS + yfinance news with deduplication
  sec_edgar.py          # Free SEC EDGAR API (no paid keys needed)
  reddit.py             # Reddit JSON API (no auth needed)
  universe.py           # S&P 500, momentum, value stock lists
engines/
  base.py               # EngineResult dataclass + BaseEngine ABC
  momentum.py           # Volume surge, trend structure, RSI/MACD confluence
  technical.py          # Chart patterns, S/R breakouts, MA crossovers, BB squeezes
  sector.py             # Sector ETF momentum, relative strength vs SPY
  mean_reversion.py     # Oversold/overbought extremes, price deviation from SMA200
  fundamental.py        # ROE, margins, growth, debt, valuation scoring
  signal_combiner.py    # Weighted combination of all engines -> trade decision
portfolio/
  models.py             # Position, Trade, Order dataclasses
  state.py              # SQLite persistence (portfolio.db)
  risk.py               # Position limits, drawdown breaker, sector caps
  tracker.py            # Sharpe ratio, win rate, max drawdown, vs SPY
cli/
  main.py               # argparse entry point
  display.py            # All formatting and display functions
connectors/
  base.py               # Abstract BrokerConnector interface
  paper.py              # Paper trading (SQLite-backed)
tests/                  # pytest test suite (32 tests)
```

## Analysis Engines

| Engine | Weight | What it does |
|--------|--------|-------------|
| Momentum | 25% | Volume surges, trend structure, RSI/MACD confluence, volatility expansion |
| Fundamental | 25% | Profitability, growth, financial health, valuation, efficiency scoring |
| Technical | 20% | S/R breakouts, chart patterns (triangles), MA crossovers, BB squeezes |
| Sector | 15% | Sector ETF momentum, relative strength vs SPY, sector flow analysis |
| Mean Reversion | 15% | Price deviation from SMA200, RSI/BB extremes, volume divergence |

The **Signal Combiner** takes all 5 engine results, applies configurable weights, handles disagreement (dampening), and produces an actionable trade decision with confidence score.

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
python -m pytest tests/ -v
```

## Disclaimer

This software is provided "as is" for educational and research purposes only. It is not financial advice. There are no guarantees of returns. Trading stocks involves risk of loss. Always do your own research and consult a licensed financial advisor before making investment decisions.
