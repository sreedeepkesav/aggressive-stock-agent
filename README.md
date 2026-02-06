# Aggressive Stock Advisory Agent

An AI-powered stock analysis and trading system with 8 institutional-grade analysis engines. Uses Claude AI to deliver professional-level momentum, breakout, options flow, and fundamental analysis.

## Quick Start

```bash
# 1. Clone
git clone https://github.com/sreedeepkesav/aggressive-stock-agent.git
cd aggressive-stock-agent

# 2. Set up Python environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API keys
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY (required)

# 5. Run
python stock_agent.py help
```

## API Tokens

Only `ANTHROPIC_API_KEY` is required. All others are optional with automatic fallbacks.

| Variable | Required | Free Tier | Get it from |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | **Yes** | Pay-as-you-go | [console.anthropic.com](https://console.anthropic.com/) |
| `ALPHA_VANTAGE_API_KEY` | No | 25 calls/day | [alphavantage.co](https://www.alphavantage.co/support/#api-key) |
| `POLYGON_API_KEY` | No | Free w/ Alpaca | [alpaca.markets](https://alpaca.markets/) |
| `SEC_API_KEY` | No | 100 req/day | [sec-api.io](https://sec-api.io/) |
| `REDDIT_CLIENT_ID` | No | Unlimited | [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) |
| `REDDIT_CLIENT_SECRET` | No | Unlimited | (same as above) |
| `AVANZA_USERNAME` | No | Broker account | [avanza.se](https://www.avanza.se/) |
| `AVANZA_PASSWORD` | No | Broker account | (same as above) |
| `AUTO_EXECUTE` | No | — | Set `true` to auto-trade (default `false`) |

## Modes

### Analyze a stock
```bash
python stock_agent.py ticker NVDA
```
Runs all 8 professional analysis engines on a single ticker.

### Screen by strategy
```bash
python stock_agent.py screen momentum    # Volume surge + price momentum
python stock_agent.py screen value       # Undervalued + strong fundamentals
python stock_agent.py screen breakout    # Chart pattern breakouts
python stock_agent.py screen earnings    # Pre-earnings setups
python stock_agent.py screen whale       # Unusual institutional activity
python stock_agent.py screen oversold    # Oversold bounces
```
Screens 20+ candidates, then runs full analysis on the top 5.

### Multi-strategy scan
```bash
python stock_agent.py scan
```
Runs all strategies simultaneously and finds high-conviction overlaps.

### Discovery & auto-trading
```bash
python stock_agent.py discover           # News-driven ticker discovery
python stock_agent.py auto               # Continuous discovery + monitoring
python stock_agent.py auto force         # Skip market timing, run immediately
```

### Other
```bash
python stock_agent.py watchlist          # Analyze curated 60+ ticker watchlist
python stock_agent.py update             # Force refresh universe data
python stock_agent.py help               # Full help with all options
```

## Analysis Engines

The system runs 8 engines in parallel for institutional-grade analysis:

1. **Momentum Breakout** — Volume surges, trend structure, technical confluence
2. **Options Flow (Whale Tracking)** — Put/call ratios, large block trades
3. **Earnings Surprise** — Historical beat patterns, analyst revision momentum
4. **Technical Breakout** — Chart patterns, support/resistance, MA crossovers
5. **Dark Pool Monitor** — Hidden institutional accumulation detection
6. **Sector Rotation** — Economic cycle positioning, relative strength
7. **Mean Reversion** — Oversold/overbought extremes, Bollinger Band analysis
8. **Fundamental Scorer** — ROE, margins, growth, debt, valuation metrics

Signals from multiple engines combine to boost confidence scores. See [PROFESSIONAL_FEATURES.md](PROFESSIONAL_FEATURES.md) for detailed engine output examples.

## Documentation

- [USAGE.md](USAGE.md) — Detailed mode descriptions and example output
- [PROFESSIONAL_FEATURES.md](PROFESSIONAL_FEATURES.md) — All 8 engines explained with sample output
- [SCREENING_GUIDE.md](SCREENING_GUIDE.md) — Strategy screening guide
- [API_SETUP.md](API_SETUP.md) — Step-by-step API key setup instructions

## Risk Disclaimer

This tool is for **educational and research purposes**. It provides aggressive trading recommendations with high risk tolerance. Always:

- Verify recommendations with your own research
- Never invest more than you can afford to lose
- Use manual confirmation mode (`AUTO_EXECUTE=false`) until you understand the system
- Past signals do not guarantee future results
