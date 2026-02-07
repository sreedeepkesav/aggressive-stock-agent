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

---

## How to Get Real Value from This Tool

This section walks through practical workflows - how to actually use the system to find opportunities, validate them, manage risk, and improve over time. Every example uses real commands you can run right now.

### Daily Workflow: Morning Scan (5 minutes)

The highest-value habit is a daily morning scan of your focus packages before markets open.

```bash
# 1. Check the market regime first - this tells you what kind of day to expect
python stock_agent.py ticker SPY

# What to look for in the output:
#   Regime: TRENDING_UP → favor momentum/breakout plays
#   Regime: HIGH_VOLATILITY → sit on hands or look for mean reversion
#   Credit Stress > 0.5 → something is breaking in credit markets, be cautious
#   VIX Term: backwardation → market is panicking, avoid new longs
#   Yield Curve: INVERTED → longer-term recession signal, favor defensive sectors

# 2. Scan your preferred sector for actionable signals
python stock_agent.py scan 10 --package sector_semiconductors

# 3. Deep-dive anything marked [ACTIONABLE]
python stock_agent.py ticker NVDA
python stock_agent.py ticker AMD
```

**What makes a signal worth acting on:**
- Action is BUY or STRONG_BUY
- Confidence >= 50% AND Agreement >= 60% (the `[ACTIONABLE]` tag)
- At least 3 of 5 engines agree on direction
- No earnings blackout warning (the system auto-suppresses these, but check the reasons)
- Regime is not HIGH_VOLATILITY (unless mean reversion engine is driving the signal)

### Finding Opportunities Across Markets

Don't just scan the same 10 stocks. The system has 83 packages for a reason.

```bash
# Scan different sectors to find where the momentum is rotating
python stock_agent.py scan 5 -p sector_semiconductors
python stock_agent.py scan 5 -p sector_energy
python stock_agent.py scan 5 -p sector_healthcare
python stock_agent.py scan 5 -p sector_financials

# The sector engine ranks all 11 S&P sectors - look at which sectors
# are flagged as "top sector" in the reasons. Rotate into strength.

# Scan international markets for diversification
python stock_agent.py scan 5 -p japan
python stock_agent.py scan 5 -p india
python stock_agent.py scan 5 -p uk_ftse

# Look at thematic packages for emerging trends
python stock_agent.py scan 5 -p theme_ai_ml
python stock_agent.py scan 5 -p theme_cybersecurity

# Check Reddit + news for tickers you might be missing
python stock_agent.py discovery
# Then analyze any interesting mentions:
python stock_agent.py ticker PLTR
```

### Reading the Regime: When to Be Aggressive vs Defensive

The regime detection is the single most important output. It changes everything.

**TRENDING_UP (VIX < 25, breadth > 60%)**
- This is where you make money. Momentum weight is 30%.
- Look for breakouts with volume confirmation (technical engine flags these)
- Be willing to hold positions longer - tighten time stops
- Scan growth-heavy packages: `us_nasdaq100`, `theme_ai_ml`, `sector_semiconductors`

**TRENDING_DOWN (SPY < SMA50 < SMA200)**
- Capital preservation mode. Mean reversion and fundamental weight both at 30%.
- Only take signals with very high confidence (>70%)
- Focus on value/defensive: `us_dividend_aristocrats`, `sector_utilities`, `sector_healthcare`
- Look for oversold bounces in quality names (mean reversion engine)

**RANGE_BOUND (low SMA50 slope, mixed breadth)**
- Mean reversion weight is 30% - buy low, sell high within the range
- Look for BB %B < 0.1 (oversold) + stochastic crossover signals
- Shorter holding periods - take profits at 2R instead of holding for 5R
- Good regime for: `us_sp500`, `us_mega_cap` (liquid names with clear ranges)

**HIGH_VOLATILITY (VIX > 30)**
- The system blocks new BUY signals when VIX > 35. Trust this.
- If VIX is 30-35: only take STRONG_BUY with >70% confidence
- Fundamental weight is 30% - focus on balance sheet quality, free cash flow
- Watch the lead indicators: if credit stress is high AND VIX term is backwardation, don't fight it

### Using Lead Indicators for Early Warnings

The 4 lead indicators often signal regime shifts 1-3 weeks before the lagging indicators (SMA crossovers) catch up.

```bash
# The regime summary shows lead indicators:
python stock_agent.py ticker SPY
# Output includes:
#   Lead: Credit: 0.00 | YC: OK | VTS: contango | Risk: neutral
```

**Warning signs to watch for (even when regime still says TRENDING_UP):**
- Credit Stress > 0.3 → junk bonds underperforming, smart money getting nervous
- VIX Term: backwardation → VIX is above VIX3M, market pricing in near-term fear
- Risk: risk_off → gold outperforming stocks, defensive rotation
- YC: INV → yield curve inverted, historically precedes recessions by 6-18 months

**When 2+ lead indicators flash warning simultaneously:** reduce position sizes, tighten stops, move to cash. Don't wait for the SMA crossover to confirm - by then you've already given back gains.

### Earnings Season Playbook

The system automatically suppresses BUY signals within 3 days of earnings. Here's how to use earnings awareness beyond just the blackout.

```bash
# Before earnings season (check a few weeks early):
python stock_agent.py ticker AAPL
# Look for: "[Earnings] 14d until earnings - monitor closely"

# The fundamental engine now scores earnings surprise history:
# - "Earnings beat rate 88%" → consistent beater, likely to beat again
# - "Avg surprise +7.2%" → tends to beat by a wide margin
# - "Negative surprise trend" → recent misses, be cautious
```

**Earnings strategy:**
1. 2+ weeks before earnings: analyze the stock normally. If it's STRONG_BUY with high beat rate, consider entering early before the run-up
2. 3 days before earnings: the system auto-suppresses to HOLD. Respect this - don't override
3. Day after earnings: re-analyze immediately. Post-earnings momentum is often the safest entry
4. Use `discovery` to find which companies are reporting this week and pre-scan them

### Validating Your Strategy with Backtesting

Don't trade a strategy you haven't backtested. The system has two backtest modes for different needs.

```bash
# Quick validation: does this package have any edge?
python stock_agent.py backtest 6 -p sector_semiconductors --fast
# Takes seconds. Look at: win rate > 50%, profit factor > 1.2, excess return > 0

# If fast mode looks promising, run the real test:
python stock_agent.py backtest 6 -p sector_semiconductors
# This uses the actual 5-engine combiner with slippage and commission.
# Takes longer but results are honest - if it works here, it works in practice.
```

**How to interpret backtest results:**

| Metric | Good | Mediocre | Bad |
|--------|------|----------|-----|
| Win Rate | > 55% | 45-55% | < 45% |
| Profit Factor | > 1.5 | 1.0-1.5 | < 1.0 |
| Sharpe Ratio | > 1.0 | 0.5-1.0 | < 0.5 |
| Max Drawdown | < -10% | -10% to -20% | > -20% |
| Excess vs SPY | > 0% | -5% to 0% | < -5% |

**Regime breakdown is key.** If your strategy has a 60% win rate overall but 20% win rate in HIGH_VOLATILITY, you know to sit out volatile periods. The backtest shows per-regime performance so you can match strategy to conditions.

```bash
# Compare packages to find your edge
python stock_agent.py backtest 12 -p us_mega_cap --fast
python stock_agent.py backtest 12 -p us_nasdaq100 --fast
python stock_agent.py backtest 12 -p sector_semiconductors --fast
python stock_agent.py backtest 12 -p us_dividend_aristocrats --fast
# Whichever has the best risk-adjusted returns (Sharpe), focus there
```

**Test before you trust:**
- Always compare full vs fast mode. If fast mode shows +20% but full mode shows +5%, the difference is slippage, commission, and more realistic signal generation.
- Total costs in full mode should be < 2% of capital per year. If higher, you're overtrading.
- If regime breakdown shows losses in every regime, the package doesn't have an edge.

### Building the Learning System

The system gets smarter the more you use it. Here's how to maximize learning.

```bash
# Step 1: Analyze stocks regularly (this feeds the learning database)
python stock_agent.py ticker NVDA
python stock_agent.py ticker AAPL
python stock_agent.py ticker MSFT
# Every analysis is saved to SQLite with per-engine signals

# Step 2: After 5+ trading days, check how predictions played out
python stock_agent.py portfolio stats
# The system auto-fills actual returns and marks each engine's signal as correct/wrong

# Step 3: View which engines are actually working
# In CLI:
python stock_agent.py portfolio stats
# Look at "Engine Accuracy (last 90 days)"
# In web dashboard: Engine Performance page

# Step 4: Adaptive weights automatically adjust
# Engines above 50% accuracy get more weight, below get less
# The blend is 70% adaptive + 30% regime (safe, won't overcorrect)
```

**How to accelerate learning:**
- Analyze at least 5-10 symbols per day for the first 2 weeks
- Cover different sectors and market caps (don't just do tech mega caps)
- After 2 weeks, you'll have ~100+ data points and adaptive weights will kick in
- Check Engine Performance weekly to see which engines are earning their weight

### Position Sizing and Risk Management

The risk system is the difference between surviving and blowing up.

```bash
# See all risk parameters:
python stock_agent.py settings
# Choose option 4 to display current settings

# Adjust for your risk tolerance:
python stock_agent.py settings
# Choose option 3 to modify risk parameters
```

**Conservative setup (recommended for starting out):**
```bash
MAX_POSITION_PCT=0.05          # 5% per position (half of default)
MAX_SIMULTANEOUS_POSITIONS=3   # Only 3 positions at a time
DRAWDOWN_CIRCUIT_BREAKER=-0.07 # Stop at 7% drawdown
CASH_RESERVE_PCT=0.30          # Keep 30% in cash
```

**Aggressive setup (experienced traders only):**
```bash
MAX_POSITION_PCT=0.15          # 15% per position
MAX_SIMULTANEOUS_POSITIONS=5   # 5 positions
DRAWDOWN_CIRCUIT_BREAKER=-0.15 # Allow 15% drawdown
CASH_RESERVE_PCT=0.10          # Only 10% cash reserve
```

**Key risk rules the system enforces:**
- No single position exceeds MAX_POSITION_PCT of portfolio
- No sector exceeds 40% of portfolio (prevents "all in on tech")
- Circuit breaker halts all trading when drawdown hits threshold
- Trailing stops tighten as profit grows (2.5 ATR -> 2.0 -> 1.5)
- Dead money exit closes positions going nowhere after 20 days

### Exit Signals: When to Actually Sell

Most people know when to buy. Few know when to sell. The exit system handles this.

```bash
# Check exit signals for open positions:
python stock_agent.py portfolio show
# Output shows active exit signals with urgency levels:
#   [immediate] NVDA: trailing_stop - Trailing stop hit: $118.50 (HWM $125.00, 2.0x ATR)
#   [end_of_day] AMD: profit_take - 3R profit (3.2R) - take 33%, tighten stop
#   [next_session] MSFT: time_exit - Dead money: 32 days held, only 1.2% gain
```

**What each urgency level means:**
- `immediate` - Exit now, price has broken your stop level
- `end_of_day` - Take action before market close today
- `next_session` - Can wait until tomorrow, but don't ignore it

**How the staged profit system works in practice:**
1. You buy NVDA at $100, stop at $93.75 (2.5 ATR = $6.25 risk per share, that's 1R)
2. NVDA hits $112.50 (2R profit) -> sell 33%, move stop to $100 (breakeven)
3. NVDA hits $118.75 (3R profit) -> sell another 33%, tighten stop to 1.5 ATR from high
4. NVDA hits $131.25 (5R profit) -> close remaining position
5. If NVDA reverses at any point, trailing stop catches it

### Web Dashboard: Best Practices

```bash
python stock_agent.py web
```

**Ticker Analysis page:**
- Use this for deep dives on specific stocks
- The 4x2 regime grid (Regime, VIX, SPY Trend, Breadth + Credit, Yield Curve, VIX Term, Risk) is the most information-dense view
- Scroll to "Top Reasons" - these explain *why* the system is bullish or bearish

**Market Scan page:**
- Select a package from the dropdown, set top N to 10-15
- After scanning, click "Top 3 Detailed" expanders to see engine breakdowns
- The Actionable count at the top tells you how many signals are worth looking at

**Backtest page:**
- Always start with Fast mode to quickly compare packages
- Switch to Full mode only for your top 2-3 candidate packages
- The equity curve shows drawdown periods - if the curve has long flat periods, the strategy doesn't have enough edge for that package

**Engine Performance page:**
- Click "Refresh Data" to update outcome tracking
- Compare Default Weight vs Adaptive Weight columns - big differences mean the learning system has identified engines that over/under-perform
- If one engine is consistently < 40% accuracy, investigate why (might be wrong regime for that engine)

### Common Mistakes to Avoid

1. **Ignoring regime.** A STRONG_BUY in HIGH_VOLATILITY is not the same as in TRENDING_UP. The system adjusts weights, but you should adjust position size too.

2. **Overriding earnings blackout.** The system suppresses signals near earnings for a reason. Binary events are gambling, not investing.

3. **Scanning too many packages.** Pick 3-5 packages you know well. Scanning 83 packages generates noise, not signal.

4. **Skipping backtesting.** If you wouldn't bet on it historically, don't bet on it now. Run `backtest --fast` at minimum.

5. **Ignoring exit signals.** The hardest part of trading is selling. When the system says exit, exit. The trailing stop and staged profit system exists so you don't have to decide emotionally.

6. **Not feeding the learning system.** The adaptive weights only work if you analyze stocks regularly. 5-10 analyses per day for 2 weeks bootstraps the system.

7. **Using full backtest on too many symbols.** Full mode runs the real 5-engine combiner per signal. Start with `--fast` and only promote to full for packages that show promise.

8. **Trading during lead indicator warnings.** When credit stress is high AND VIX is in backwardation, the regime might still say TRENDING_UP (lagging). Trust the lead indicators - they're early for a reason.

---

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
