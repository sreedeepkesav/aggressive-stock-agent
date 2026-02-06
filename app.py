"""Streamlit web interface for Stock Analysis Agent.

Run with: streamlit run app.py
"""

import os
import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import streamlit as st
import pandas as pd

from config.settings import Settings, RiskParams
from engines.signal_combiner import SignalCombiner, CombinedSignal
from portfolio import state
from portfolio.risk import RiskManager
from portfolio.tracker import get_portfolio_summary, get_trade_stats, sharpe_ratio, vs_spy

# --- Page config ---
st.set_page_config(
    page_title="Stock Analysis Agent",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Init ---
state.init_db()
settings = Settings.load()


# ============================================================
# Sidebar - Navigation + Risk Settings
# ============================================================
with st.sidebar:
    st.title("Stock Agent")
    page = st.radio(
        "Navigate",
        ["Ticker Analysis", "Market Scan", "Portfolio", "Discovery", "Settings"],
        index=0,
    )
    st.divider()
    st.caption(f"LLM Mode: `{settings.llm_mode.value}`")
    st.caption(f"Max Position: {settings.risk.max_position_pct:.0%}")
    st.caption(f"Max Positions: {settings.risk.max_simultaneous_positions}")
    st.caption(f"Drawdown Breaker: {settings.risk.drawdown_circuit_breaker:.0%}")


# ============================================================
# Helper functions
# ============================================================
def signal_color(action: str) -> str:
    if action in ("STRONG_BUY", "BUY"):
        return "green"
    elif action in ("STRONG_SELL", "SELL"):
        return "red"
    return "gray"


def render_engine_results(sig: CombinedSignal):
    """Render engine results as a table."""
    rows = []
    for name, result in sig.engine_results.items():
        rows.append({
            "Engine": name.replace("_", " ").title(),
            "Signal": result.signal,
            "Confidence": f"{result.confidence:.0%}",
            "Reasons": ", ".join(result.reasons[:3]) if result.reasons else "-",
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_combined_signal(sig: CombinedSignal):
    """Render the combined signal with metrics."""
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Action", sig.action)
    col2.metric("Combined Score", f"{sig.combined_score:+.3f}")
    col3.metric("Confidence", f"{sig.confidence:.0%}")
    col4.metric("Agreement", f"{sig.agreement_pct:.0%}")

    if sig.is_actionable:
        st.success("ACTIONABLE - High confidence with engine agreement")
    elif sig.action == "HOLD":
        st.info("HOLD - No clear signal")
    else:
        st.warning("Low confidence - not actionable")


# ============================================================
# Page: Ticker Analysis
# ============================================================
if page == "Ticker Analysis":
    st.header("Ticker Analysis")
    st.caption("Run all 5 engines on a single stock")

    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = st.text_input("Enter ticker symbol", value="NVDA", max_chars=10).strip().upper()
    with col2:
        analyze_btn = st.button("Analyze", type="primary", use_container_width=True)

    if analyze_btn and symbol:
        with st.spinner(f"Analyzing {symbol} across 5 engines..."):
            combiner = SignalCombiner()
            sig = combiner.analyze(symbol)

        st.subheader(f"Results: {symbol}")
        render_combined_signal(sig)

        st.subheader("Engine Breakdown")
        render_engine_results(sig)

        if sig.reasons:
            st.subheader("Top Reasons")
            for r in sig.reasons[:8]:
                st.markdown(f"- {r}")

        # Risk check for actionable signals
        if sig.is_actionable and sig.action in ("STRONG_BUY", "BUY"):
            st.subheader("Risk Assessment")
            rm = RiskManager(settings.risk)
            momentum_result = sig.engine_results.get("momentum")
            entry = momentum_result.metadata.get("entry", 0) if momentum_result else 0
            if entry > 0:
                stop = rm.calculate_stop_loss(symbol, entry)
                qty = rm.calculate_position_size(entry, stop)
                proposed_value = qty * entry
                check = rm.check_can_open_position(symbol, proposed_value)

                if check["allowed"]:
                    st.success(f"Risk check PASSED: {qty} shares @ ${entry:.2f}, stop ${stop:.2f}")
                else:
                    st.error("Risk check BLOCKED:")
                    for reason in check["reasons"]:
                        st.markdown(f"- {reason}")

                col1, col2, col3 = st.columns(3)
                col1.metric("Suggested Qty", qty)
                col2.metric("Entry Price", f"${entry:.2f}")
                col3.metric("Stop Loss", f"${stop:.2f}")


# ============================================================
# Page: Market Scan
# ============================================================
elif page == "Market Scan":
    st.header("Market Scan")
    st.caption("Scan your watchlist for the best opportunities")

    col1, col2 = st.columns([3, 1])
    with col1:
        top_n = st.slider("Show top N results", min_value=3, max_value=30, value=10)
    with col2:
        scan_btn = st.button("Scan Watchlist", type="primary", use_container_width=True)

    if scan_btn:
        progress_bar = st.progress(0, text="Scanning...")
        combiner = SignalCombiner()
        signals = []
        watchlist = settings.watchlist

        for i, sym in enumerate(watchlist):
            try:
                sig = combiner.analyze(sym)
                signals.append(sig)
            except Exception as e:
                pass
            progress_bar.progress((i + 1) / len(watchlist), text=f"Analyzing {sym}...")

        progress_bar.empty()
        signals.sort(key=lambda s: s.combined_score, reverse=True)

        actionable = [s for s in signals if s.is_actionable]
        st.metric("Actionable Signals", len(actionable), delta=f"of {len(signals)} scanned")

        # Results table
        rows = []
        for sig in signals[:top_n]:
            rows.append({
                "Symbol": sig.symbol,
                "Action": sig.action,
                "Score": f"{sig.combined_score:+.3f}",
                "Confidence": f"{sig.confidence:.0%}",
                "Agreement": f"{sig.agreement_pct:.0%}",
                "Actionable": "Yes" if sig.is_actionable else "",
                "Top Reason": sig.reasons[0] if sig.reasons else "-",
            })

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Detailed view for top 3
        st.subheader("Top 3 Detailed")
        for sig in signals[:3]:
            with st.expander(f"{sig.symbol} - {sig.action} ({sig.combined_score:+.3f})"):
                render_combined_signal(sig)
                render_engine_results(sig)


# ============================================================
# Page: Portfolio
# ============================================================
elif page == "Portfolio":
    st.header("Portfolio")

    tab1, tab2 = st.tabs(["Overview", "Trade History"])

    with tab1:
        summary = get_portfolio_summary()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Value", f"${summary['total_value']:,.2f}")
        col2.metric("Cash", f"${summary['cash']:,.2f}")
        col3.metric("Positions", f"${summary['position_value']:,.2f}")
        col4.metric("Drawdown", f"{summary['drawdown']:.1%}")

        col5, col6 = st.columns(2)
        col5.metric("Unrealized PnL", f"${summary['unrealized_pnl']:,.2f}")
        col6.metric("Open Positions", summary['position_count'])

        if summary["positions"]:
            st.subheader("Open Positions")
            pos_df = pd.DataFrame(summary["positions"])
            pos_df.columns = ["Symbol", "Qty", "Entry", "Current", "PnL ($)", "PnL (%)"]
            st.dataframe(pos_df, use_container_width=True, hide_index=True)
        else:
            st.info("No open positions")

    with tab2:
        stats = get_trade_stats()

        if stats.get("total_trades", 0) > 0:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Trades", stats["total_trades"])
            col2.metric("Win Rate", f"{stats['win_rate']:.0%}")
            col3.metric("Total PnL", f"${stats['total_pnl']:,.2f}")
            col4.metric("Profit Factor", f"{stats['profit_factor']:.2f}")

            col5, col6, col7 = st.columns(3)
            col5.metric("Avg Win", f"${stats['avg_win']:,.2f}")
            col6.metric("Avg Loss", f"${stats['avg_loss']:,.2f}")
            col7.metric("Sharpe Ratio", f"{sharpe_ratio():.2f}")

            spy_data = vs_spy()
            st.subheader("vs SPY")
            col1, col2, col3 = st.columns(3)
            col1.metric("SPY Return", f"{spy_data.get('spy_return', 0):.1%}")
            col2.metric("Portfolio Return", f"{spy_data.get('portfolio_return', 0):.1%}")
            col3.metric("Excess Return", f"{spy_data.get('excess_return', 0):.1%}")
        else:
            st.info("No trade history yet")


# ============================================================
# Page: Discovery
# ============================================================
elif page == "Discovery":
    st.header("Opportunity Discovery")
    st.caption("Find new tickers from news and Reddit")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Scan Reddit", type="primary"):
            with st.spinner("Scanning Reddit..."):
                from data.reddit import get_ticker_mentions
                mentions = get_ticker_mentions()

            if mentions:
                st.subheader(f"Trending Tickers ({len(mentions)})")
                rows = []
                for ticker, data in list(mentions.items())[:20]:
                    rows.append({
                        "Ticker": ticker,
                        "Mentions": data["count"],
                        "Avg Score": f"{data['avg_score']:.0f}",
                        "Subreddits": ", ".join(data["subreddits"][:3]),
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.warning("No ticker mentions found")

    with col2:
        if st.button("Fetch News"):
            with st.spinner("Fetching news..."):
                from data.news import fetch_rss_news
                news = fetch_rss_news(max_per_source=5)

            if news:
                st.subheader(f"Latest News ({len(news)} articles)")
                for item in news[:15]:
                    title = item.get("title", "")
                    source = item.get("source", "")
                    if title:
                        st.markdown(f"**{source}**: {title}")
            else:
                st.warning("Could not fetch news")


# ============================================================
# Page: Settings
# ============================================================
elif page == "Settings":
    st.header("Settings")
    st.caption("Current risk parameters (configure via environment variables)")

    params = settings.risk

    st.subheader("Risk Parameters")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("| Parameter | Value |")
        st.markdown("|-----------|-------|")
        st.markdown(f"| Max Position Size | `{params.max_position_pct:.0%}` |")
        st.markdown(f"| Max Portfolio Heat | `{params.max_portfolio_heat:.0%}` |")
        st.markdown(f"| Drawdown Circuit Breaker | `{params.drawdown_circuit_breaker:.0%}` |")
        st.markdown(f"| Max Simultaneous Positions | `{params.max_simultaneous_positions}` |")
        st.markdown(f"| Max Sector Concentration | `{params.max_sector_concentration:.0%}` |")

    with col2:
        st.markdown("| Parameter | Value |")
        st.markdown("|-----------|-------|")
        st.markdown(f"| Cash Reserve | `{params.cash_reserve_pct:.0%}` |")
        st.markdown(f"| Max Daily Risk | `{params.max_daily_risk:.0%}` |")
        st.markdown(f"| Min Profit Target | `{params.min_profit_target:.0%}` |")
        st.markdown(f"| Stop Loss ATR (Swing) | `{params.stop_loss_atr_swing}` |")
        st.markdown(f"| Stop Loss ATR (Position) | `{params.stop_loss_atr_position}` |")

    st.subheader("How to Change")
    st.code("""# Option 1: Set env vars before running
MAX_POSITION_PCT=0.15 MAX_SIMULTANEOUS_POSITIONS=3 streamlit run app.py

# Option 2: Add to .env file
echo "MAX_POSITION_PCT=0.15" >> .env
echo "MAX_SIMULTANEOUS_POSITIONS=3" >> .env""", language="bash")

    st.subheader("LLM Configuration")
    st.markdown(f"**Current Mode:** `{settings.llm_mode.value}`")
    st.markdown("""
| Mode | Cost | How to set |
|------|------|-----------|
| `off` (default) | $0/month | `LLM_MODE=off` |
| `haiku` | ~$0.0003/run | `LLM_MODE=haiku` (needs `ANTHROPIC_API_KEY`) |
| `sonnet` | ~$0.01/run | `LLM_MODE=sonnet` (needs `ANTHROPIC_API_KEY`) |
""")

    st.subheader("Watchlist")
    st.write(", ".join(settings.watchlist))
