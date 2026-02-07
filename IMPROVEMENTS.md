# Future Improvements

Documented opportunities for further development, roughly ordered by impact.

## Data Quality
- **SEC EDGAR fundamentals** - Replace yfinance fundamental data with direct EDGAR filings for more reliable/timely data
- **Options flow / IV rank** - Implied volatility percentile and unusual options activity as a signal source (needs paid API like CBOE or Tradier)
- **Volume profile as S/R** - Point of control and value area from volume-at-price as dynamic support/resistance levels

## Signal Improvement
- **Seasonality patterns** - Calendar overlays (sell in May, Santa rally, quad witching) as regime modifier
- **Sentiment scoring** - NLP on news headlines and earnings call transcripts for sentiment signal
- **Sector rotation model** - Dual-momentum (absolute + relative) for sector ETF rotation overlay
- **Intermarket analysis** - USD, bonds, commodities as confirming/diverging signals for equity direction

## Portfolio Management
- **Correlation-aware position management** - Check pairwise correlation before opening positions to avoid concentration in correlated names
- **Dynamic position sizing** - Kelly criterion or optimal-f based on recent win rate and payoff ratio
- **Multi-asset allocation** - Allocate across equities, bonds, gold based on regime instead of 100% equities

## Infrastructure
- **Real-time streaming** - WebSocket price feeds for intraday trailing stop monitoring
- **Broker integration** - Direct order execution via broker APIs (IBKR, Alpaca)
- **Alerting** - Push notifications for exit signals, earnings warnings, regime changes
- **Database migration** - Move from SQLite to PostgreSQL for concurrent access and better querying
