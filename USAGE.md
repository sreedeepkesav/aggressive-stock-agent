# Aggressive Stock Advisory Agent - Usage Guide

## 🚀 Four Powerful Modes for Maximum $1000 Growth

### Mode 1: Single Ticker Analysis
Analyze any specific stock ticker with comprehensive technical and sentiment analysis.

```bash
python stock_agent.py ticker NVDA
python stock_agent.py ticker AAPL
python stock_agent.py ticker TSLA
```

**Features:**
- ✅ Deep technical analysis (RSI, moving averages, volume)
- ✅ Latest news sentiment analysis
- ✅ Precise entry/exit points
- ✅ Risk-adjusted position sizing
- ✅ Manual execution option

### Mode 2: Predefined Watchlist Analysis
Analyze the curated aggressive watchlist (same as original functionality).

```bash
python stock_agent.py watchlist
```

**Features:**
- ✅ 60+ pre-selected high-growth tickers
- ✅ Hourly automated analysis
- ✅ Portfolio optimization and swaps
- ✅ Claude 3.5 Sonnet AI recommendations
- ✅ Continuous monitoring

### Mode 3: Dynamic Ticker Discovery (🌟 MAIN GOAL)
Discover new opportunities from financial news twice daily.

```bash
# Auto-detect next market session
python stock_agent.py discover

# Specific market sessions
python stock_agent.py discover europe
python stock_agent.py discover us
```

**Features:**
- 🎯 **News-based ticker extraction** from 10+ financial sources
- 📊 **Market cap flexibility** (tiny, small, mid, large companies)
- 🌍 **Global coverage** (US, Europe, Nordic, Canada)
- 📈 **Sentiment scoring** and opportunity ranking
- ⚡ **High-conviction recommendations** for maximum growth

### Mode 4: Automated Discovery with Continuous Monitoring
Fully automated system with ticker discovery and hourly monitoring.

```bash
# Normal mode (follows market timing)
python stock_agent.py auto

# Force mode (override timing, run immediately)
python stock_agent.py auto force
```

**Discovery Schedule:**
- 🕒 **Europe Session**: 07:30 GMT (30 min before market open)
- 🕒 **US/Canada Session**: 14:00 GMT (30 min before market open)
- ⚡ **Force Mode**: Override timing, discover tickers immediately

**Continuous Monitoring:**
- 📊 **Hourly Analysis**: Top 20 discovered tickers analyzed every hour
- 🎯 **BUY/SELL/HOLD**: Continuous recommendations using old mechanism
- 🔄 **Auto-Execution**: If Avanza connected and AUTO_EXECUTE=true

## 🎯 The Main Goal: Mode 3 & 4

**Mode 3 (Discovery)** is designed to maximize your $1000 by:

1. **Real-time news analysis** from multiple financial sources
2. **Dynamic ticker extraction** using advanced pattern recognition
3. **Sentiment-driven opportunities** focusing on breaking news
4. **Market cap agnostic** - finds gems in all company sizes
5. **Pre-market timing** to catch opportunities before crowds

## 📊 Example Discovery Output

```
🌍 DYNAMIC TICKER DISCOVERY - EUROPE SESSION
=======================================================
🕒 Current time: 2024-01-15 07:30:00 UTC
🎯 Target session: EUROPE

📊 DISCOVERED 15 POTENTIAL OPPORTUNITIES:
 1.   NVDA | Score: 2.45 | Mentions: 3 | Sentiment: +0.68 | Cap: large
 2.   SMCI | Score: 2.31 | Mentions: 2 | Sentiment: +0.82 | Cap: mid
 3.   PLTR | Score: 2.18 | Mentions: 4 | Sentiment: +0.45 | Cap: mid

🔍 ANALYZING TOP 5 CANDIDATES:
   ✅ NVDA: BUY - 92% confidence
   ✅ SMCI: BUY - 87% confidence
   ⚠️  PLTR: No clear signal

🚀 FINAL RECOMMENDATIONS (2):
1. NVDA - BUY (MARKET ORDER) 🔥
   📊 Current Price: $875.32
   🚀 ENTRY PRICE:  $874.45
   🎯 Target Price:  $1066.83 (+22.0%)
   💰 Position: 0 shares = $306.58 (30.7% of capital)
   📰 News Mentions: 3 | Sample Headlines:
      • "NVIDIA Reports Record Q4 Earnings, AI Demand Surges..."
```

## ⚙️ Configuration (.env file)

```bash
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional (for live trading)
AVANZA_USERNAME=your_avanza_username
AVANZA_PASSWORD=your_avanza_password

# Auto-execution (DANGEROUS!)
AUTO_EXECUTE=false  # Set to 'true' for full automation
```

## 🎪 Aggressive Trading Parameters

- **Maximum Position Size**: 35% of capital per trade
- **Daily Risk Tolerance**: 15% of portfolio
- **Minimum Profit Target**: 12% per trade
- **Target Monthly Returns**: 20-30%
- **Focus**: High-beta momentum stocks, breakouts, news catalysts

## 🛡️ Risk Management

- ✅ Stop losses on all positions
- ✅ Position size limits
- ✅ Confidence-based scaling
- ✅ Portfolio diversification
- ✅ Manual confirmation by default

## 🚨 Important Notes

1. **Mode 3/4 is the main goal** - discovery maximizes opportunity
2. **Market timing is critical** - runs before market opens
3. **News-driven alpha** - catches breaking opportunities
4. **All company sizes** - from penny stocks to mega caps
5. **Global markets** - not limited to US only

## 🤖 Enhanced Auto Mode Workflow

**Mode 4** (`python stock_agent.py auto force`) is the ultimate hands-off system:

### 1. **Discovery Phase** (Twice Daily + Force)
```bash
python stock_agent.py auto force  # Run immediately, don't wait for timing
```
- Scans 100+ financial news articles
- Discovers and ranks new opportunities 
- Limits to **top 20 tickers** for focused monitoring
- Generates immediate BUY/SELL recommendations

### 2. **Continuous Monitoring Phase** (Every Hour)
```
[12:00] 🔍 HOURLY ANALYSIS OF 20 MONITORED TICKERS
[ 1/20] Analyzing NVDA... 🟢 BUY $875.32 (92%)
[ 2/20] Analyzing SMCI... 🟢 BUY $523.45 (87%)
[ 3/20] Analyzing PLTR... ⚪ HOLD
...

📊 HOURLY ANALYSIS SUMMARY:
   🟢 BUY signals: 5
   🔴 SELL signals: 2  
   ⚪ HOLD positions: 13
```

### 3. **Automatic Execution** (If Avanza Connected)
- **Manual Mode**: Prompts for each trade confirmation
- **Auto Mode**: (`AUTO_EXECUTE=true`) Executes all trades automatically
- **Portfolio Tracking**: Updates positions and capital in real-time

### Example Auto Session Output
```
🤖 ADVANCED AUTOMATED DISCOVERY & MONITORING
===============================================
🔍 Discovery Schedule: Force Mode ✅ ENABLED
⏰ Monitoring Schedule: Hourly analysis of top 20 tickers
🔄 Auto-execution: ✅ ENABLED
📡 Avanza API: ✅ Connected

🚀 INITIAL FORCE DISCOVERY...
🌍 DYNAMIC TICKER DISCOVERY - EUROPE SESSION
📊 DISCOVERED 15 POTENTIAL OPPORTUNITIES
📋 Updated monitoring list with 15 tickers

⏰ INITIAL MONITORING CHECK...
🔍 HOURLY ANALYSIS OF 15 MONITORED TICKERS
🎯 Hourly monitoring: 3/5 trades executed

[System continues monitoring every hour...]
```

Start with `python stock_agent.py auto force` for immediate action! 🚀