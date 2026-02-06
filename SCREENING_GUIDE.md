# 🔍 INTELLIGENT STOCK SCREENING GUIDE

## 🎯 FINDING THE RIGHT STOCKS FOR YOUR STRATEGIES

You now have powerful screening capabilities to find the best stock candidates for each professional strategy!

---

## 🚀 NEW SCREENING MODES

### 🔍 Mode 2: Strategy-Specific Screening
```bash
python stock_agent.py screen <STRATEGY>
```

**Available Strategies:**
- `momentum` - Volume surge + Price momentum + Technical breakout
- `value` - Low valuation + Strong fundamentals + Oversold conditions  
- `breakout` - Chart patterns + Volume + Support/resistance breaks
- `earnings` - Upcoming earnings + Historical beat rate + Options activity
- `whale` - Unusual options volume + Large trades + Institutional flow
- `oversold` - Oversold conditions + Support levels + Quality fundamentals

**What it does:**
1. Screens 20+ candidates for the specific strategy
2. Runs full professional analysis on top 5 candidates
3. Shows detailed BUY/SELL recommendations with confidence scores

### 🎯 Mode 3: Multi-Strategy Scan
```bash
python stock_agent.py scan
```

**What it does:**
1. Runs 5 screening strategies simultaneously
2. Finds candidates for each approach
3. Identifies high-conviction overlaps (stocks appearing in multiple strategies)
4. Perfect for finding the most promising opportunities

---

## 📈 STRATEGY DETAILS

### 🔥 MOMENTUM SCREENING
```bash
python stock_agent.py screen momentum
```

**Criteria:**
- 1.5x+ recent volume surge
- Price above 20-day SMA > 50-day SMA  
- Current price within 5% of recent highs
- Strong bullish trend structure

**Perfect for:** Momentum Breakout Engine, Options Flow Analyzer

**Example Output:**
```
🔍 SMART SCREENING FOR: MOMENTUM
📈 Screening for: Volume surge + Price momentum + Technical breakout
   ✅ NVDA: Volume 2.8x, Price momentum confirmed
   ✅ AMD: Volume 2.1x, Price momentum confirmed
   ✅ SMCI: Volume 3.2x, Price momentum confirmed

✅ FOUND 3 CANDIDATES:
   1. NVDA
   2. AMD  
   3. SMCI

🔬 PROFESSIONAL ANALYSIS OF TOP 3 CANDIDATES:
【 1/3 】 ANALYZING NVDA
🎯 RESULT: STRONG_BUY (Confidence: 87.3%)
💰 POSITION SIZE: 35.0%
💵 ENTRY: $875.32
🎯 TARGET: $945.67
🛑 STOP: $832.45
```

### 💎 VALUE SCREENING
```bash
python stock_agent.py screen value
```

**Criteria:**
- P/E ratio < 20
- Price-to-Book < 3
- Price 10%+ below 200-day SMA (oversold)
- Strong fundamental metrics

**Perfect for:** Mean Reversion Detector, Fundamental Analysis Scorer

### 📊 BREAKOUT SCREENING
```bash
python stock_agent.py screen breakout
```

**Criteria:**
- Current price within 2% of resistance levels
- Price well above support levels
- 1.2x+ volume pickup
- Chart pattern formation

**Perfect for:** Technical Breakout Detector, Momentum Breakout Engine

### 🐋 WHALE ACTIVITY SCREENING
```bash
python stock_agent.py screen whale
```

**Criteria:**
- 2x+ volume surge (institutional activity)
- Unusual options activity patterns
- Large block trade signatures
- Smart money flow indicators

**Perfect for:** Options Flow Analyzer, Dark Pool Monitor

### 📉 OVERSOLD SCREENING
```bash
python stock_agent.py screen oversold
```

**Criteria:**
- RSI < 35 (oversold)
- Bottom 30% of 1-year price range
- Near key support levels
- Quality fundamental backdrop

**Perfect for:** Mean Reversion Detector, Value opportunities

### 📅 EARNINGS SCREENING
```bash
python stock_agent.py screen earnings
```

**Criteria:**
- Upcoming earnings announcements
- Historical earnings beat patterns
- Options activity around earnings
- Surprise potential indicators

**Perfect for:** Earnings Surprise Engine, Options Flow Analyzer

---

## 🎯 MULTI-STRATEGY SCAN EXAMPLE

```bash
python stock_agent.py scan
```

**Sample Output:**
```
🎯 MULTI-STRATEGY SCAN
Running 5 screening strategies simultaneously

📊 STRATEGY SCAN RESULTS:

🔍 MOMENTUM CANDIDATES:
  1. NVDA
  2. AMD
  3. SMCI
  4. ARM
  5. MRVL

🔍 BREAKOUT CANDIDATES:
  1. AAPL
  2. NVDA
  3. MSFT
  4. META
  5. GOOGL

🔍 WHALE CANDIDATES:
  1. NVDA
  2. TSLA
  3. AAPL
  4. AMD
  5. META

🔍 OVERSOLD CANDIDATES:
  1. BAC
  2. XOM
  3. JPM
  4. CVX
  5. F

🔍 VALUE CANDIDATES:
  1. BAC
  2. JPM
  3. XOM
  4. WFC
  5. CVX

🎯 COMBINED OPPORTUNITIES:
Found 18 unique candidates: AAPL, AMD, ARM, BAC, CVX, F, GOOGL, JPM, META, MRVL, MSFT, NVDA, SMCI, TSLA, WFC, XOM

🔥 HIGH-CONVICTION OVERLAPS:
  ⭐ NVDA (appears in 3 strategies)
  ⭐ AAPL (appears in 2 strategies)
  ⭐ AMD (appears in 2 strategies)
  ⭐ META (appears in 2 strategies)
  ⭐ BAC (appears in 2 strategies)
  ⭐ JPM (appears in 2 strategies)
  ⭐ XOM (appears in 2 strategies)
```

**High-conviction overlaps = Best opportunities!**

---

## 🏛️ STOCK UNIVERSES

The screener uses curated universes for each strategy:

### 📈 Momentum Universe (30 stocks)
High-growth tech and momentum names: NVDA, AMD, SMCI, ARM, PLTR, NET, SNOW, CRWD, etc.

### 💎 Value Universe (30 stocks)  
Banks, energy, industrials: BAC, JPM, XOM, CVX, F, GM, etc.

### 📊 Breakout Universe (20 stocks)
Large caps with breakout potential: AAPL, MSFT, GOOGL, META, NFLX, etc.

### 🐋 Whale Universe (40 stocks)
S&P 500 names with heavy options activity

### 🏢 Sector Leaders (40 stocks)
Top names across 5 major sectors

---

## 💡 HOW TO USE THE SCREENER

### 1. **Start with Multi-Strategy Scan**
```bash
python stock_agent.py scan
```
- Gives you the big picture
- Identifies high-conviction overlaps
- Shows which strategies are working

### 2. **Deep Dive on Specific Strategy**
```bash
python stock_agent.py screen momentum
```
- Focus on one approach
- Get detailed analysis of top candidates
- Perfect for when you have a directional view

### 3. **Analyze Individual Winners**
```bash
python stock_agent.py ticker NVDA
```
- Full professional analysis
- All 8 engines working together
- Detailed entry/exit/risk management

### 4. **Automate the Process**
```bash
python stock_agent.py auto force
```
- Combines news discovery + screening
- Continuous monitoring
- Full automation

---

## 🎯 STRATEGY COMBINATIONS

**For Maximum Edge, Combine Multiple Signals:**

### 🔥 High-Conviction Momentum
1. Run `screen momentum` - Find volume surge candidates
2. Look for candidates also appearing in `screen whale` 
3. Analyze with `ticker` mode for full confirmation
4. **Result:** Institutional momentum with whale confirmation

### 💎 Smart Value Plays
1. Run `screen oversold` - Find beaten down quality names
2. Cross-reference with `screen value` for fundamental confirmation
3. Use `ticker` mode for mean reversion + fundamental analysis
4. **Result:** Quality value with technical timing

### 📊 Breakout Confirmation
1. Run `screen breakout` - Find pattern setups
2. Verify with `screen momentum` for volume confirmation
3. Full analysis with `ticker` mode
4. **Result:** Technical + momentum convergence

---

## ⚡ QUICK REFERENCE

```bash
# FIND OPPORTUNITIES
python stock_agent.py scan                    # Best overall approach
python stock_agent.py screen momentum         # Momentum plays  
python stock_agent.py screen whale           # Follow big money
python stock_agent.py screen oversold        # Contrarian opportunities

# ANALYZE WINNERS
python stock_agent.py ticker NVDA            # Full professional analysis

# GET HELP
python stock_agent.py help                   # Complete guide
```

---

**🚀 The screening system solves your exact problem: finding the right stocks for the right strategies at the right time!**

No more guessing - let the professional screener find the best opportunities, then let the 8 analysis engines confirm the trades with institutional precision.