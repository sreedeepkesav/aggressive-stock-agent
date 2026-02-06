# Free API Keys Setup Guide

## 🔑 **Completely Free APIs (No Credit Card Required)**

### 1. **Reddit API** (100% Free)
- **Purpose**: Social sentiment analysis from Reddit communities
- **Setup**: 
  1. Go to https://www.reddit.com/prefs/apps
  2. Click "Create Application"
  3. Choose "script" type
  4. Get your `client_id` and `client_secret`
  5. Add to `.env` file

### 2. **SEC API** (100 requests/day free)
- **Purpose**: Insider trading monitoring
- **Setup**:
  1. Go to https://sec-api.io/
  2. Sign up for free account
  3. Get 100 free API calls per day
  4. Add SEC_API_KEY to `.env` file
- **Alternative**: Leave empty - tool uses free SEC EDGAR database

## ⚡ **Optional Free APIs (Enhanced Features)**

### 3. **Alpha Vantage** (25 calls/day free)
- **Purpose**: Enhanced stock data
- **Setup**:
  1. Go to https://www.alphavantage.co/support/#api-key
  2. Get free API key (no credit card)
  3. Add ALPHA_VANTAGE_API_KEY to `.env`

### 4. **Polygon.io via Alpaca** (Free with account)
- **Purpose**: Real-time market data
- **Setup**:
  1. Create free Alpaca account at https://alpaca.markets/
  2. Get free Polygon.io access
  3. Add POLYGON_API_KEY to `.env`

## 🚀 **Quick Start (No API Keys)**

The tool works out-of-the-box without any API keys! It will:
- ✅ Fetch news from 16+ sources
- ✅ Extract and validate tickers  
- ✅ Use fallback SEC data
- ✅ Use fallback social sentiment
- ✅ Perform full market analysis

**Just run**: `python stock_agent.py auto force`

## 🔧 **Current Configuration**

Your `.env` file should look like:
```bash
# Required (already set)
ANTHROPIC_API_KEY=your_key_here
AVANZA_USERNAME=your_username
AVANZA_PASSWORD=your_password
AUTO_EXECUTE=false

# Optional (free APIs)
SEC_API_KEY=               # Leave empty for free mode
REDDIT_CLIENT_ID=          # Get from reddit.com/prefs/apps
REDDIT_CLIENT_SECRET=      # Get from reddit.com/prefs/apps
ALPHA_VANTAGE_API_KEY=     # Get from alphavantage.co
POLYGON_API_KEY=           # Get from alpaca.markets
```

## 📊 **What Each API Adds**

| API | Free Tier | What It Adds |
|-----|-----------|--------------|
| **None** | ∞ | Basic news discovery, fallback data |
| **Reddit** | ∞ | Real social sentiment from 8+ subreddits |
| **SEC API** | 100/day | Real insider trading alerts |
| **Alpha Vantage** | 25/day | Enhanced stock data validation |
| **Polygon** | Free | Real-time price data |

**Bottom line**: The tool is fully functional without any additional API keys!