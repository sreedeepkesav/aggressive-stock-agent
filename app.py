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
from engines.timeframe import apply_timeframe_filter
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
        ["Ticker Analysis", "Market Scan", "Portfolio", "Engine Performance",
         "Backtest", "Discovery", "Settings"],
        index=0,
    )
    st.divider()

    # Show regime info
    try:
        from engines.regime import detect_regime
        regime = detect_regime()
        st.caption(f"Regime: `{regime.regime.value}`")
        st.caption(f"VIX: `{regime.vix_level:.1f}`")
        st.caption(f"Breadth: `{regime.breadth_pct:.0%}`")
        st.caption(f"Credit: `{regime.credit_stress:.2f}`")
        st.caption(f"YC: `{'INV' if regime.yield_curve_inverted else 'OK'}`")
        st.caption(f"VTS: `{regime.vix_term_structure}`")
        st.caption(f"Risk: `{regime.risk_appetite}`")
        if regime.block_buys:
            st.error("BUY signals blocked (VIX > 35)")
    except Exception:
        st.caption("Regime: loading...")

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
    st.caption("Run all 5 engines + regime detection + multi-timeframe confirmation")

    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = st.text_input("Enter ticker symbol", value="NVDA", max_chars=10).strip().upper()
    with col2:
        analyze_btn = st.button("Analyze", type="primary", use_container_width=True)

    if analyze_btn and symbol:
        with st.spinner(f"Analyzing {symbol} across 5 engines..."):
            from portfolio.memory import get_adaptive_weights, save_analysis, check_outcomes
            check_outcomes()
            adaptive_weights = get_adaptive_weights()

            combiner = SignalCombiner()
            sig = combiner.analyze(symbol, adaptive_weights=adaptive_weights)
            sig = apply_timeframe_filter(sig)

        st.subheader(f"Results: {symbol}")

        # Regime info
        if sig.regime:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Regime", sig.regime.regime.value)
            col2.metric("VIX", f"{sig.regime.vix_level:.1f}")
            col3.metric("SPY Trend", sig.regime.spy_trend)
            col4.metric("Breadth", f"{sig.regime.breadth_pct:.0%}")

            # Lead indicators
            col5, col6, col7, col8 = st.columns(4)
            col5.metric("Credit Stress", f"{sig.regime.credit_stress:.2f}")
            col6.metric("Yield Curve", "INVERTED" if sig.regime.yield_curve_inverted else "Normal")
            col7.metric("VIX Term", sig.regime.vix_term_structure)
            col8.metric("Risk Appetite", sig.regime.risk_appetite)

        render_combined_signal(sig)

        st.subheader("Engine Breakdown")
        render_engine_results(sig)

        if sig.reasons:
            st.subheader("Top Reasons")
            for r in sig.reasons[:10]:
                st.markdown(f"- {r}")

        # Save analysis
        price = 0
        momentum_result = sig.engine_results.get("momentum")
        if momentum_result:
            price = momentum_result.metadata.get("entry", 0)
        regime_str = sig.regime.regime.value if sig.regime else "UNKNOWN"
        save_analysis(
            symbol=symbol, combined_score=sig.combined_score, action=sig.action,
            confidence=sig.confidence, agreement_pct=sig.agreement_pct,
            close_price=price, regime=regime_str, engine_results=sig.engine_results,
        )

        # Risk check for actionable signals
        if sig.is_actionable and sig.action in ("STRONG_BUY", "BUY"):
            st.subheader("Risk Assessment")
            rm = RiskManager(settings.risk)
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

                # Show trailing stop level
                from portfolio.exits import calculate_trailing_stop_level
                trail = calculate_trailing_stop_level(symbol, entry, "")
                if trail:
                    st.metric("Trailing Stop", f"${trail:.2f}")


# ============================================================
# Page: Market Scan
# ============================================================
elif page == "Market Scan":
    st.header("Market Scan")
    st.caption("Scan your watchlist with regime-aware analysis")

    from config.watchlists import list_packages_by_region, PACKAGE_META, get_package_symbols

    # Package selector - require explicit selection
    pkg_options = {}
    for region, pkgs in list_packages_by_region().items():
        for key, name, count in pkgs:
            pkg_options[f"{name} ({count} symbols) [{region}]"] = key

    col1, col2 = st.columns([1, 1])
    with col1:
        selected_pkg_label = st.selectbox(
            "Select a package to scan",
            list(pkg_options.keys()),
            index=None,
            placeholder="Choose a package...",
        )
    with col2:
        top_n = st.slider("Show top N results", min_value=3, max_value=30, value=10)

    if not selected_pkg_label:
        st.info("Select a package above to start scanning. Use the **Packages** page or `python stock_agent.py packages` to browse all 83 packages.")

    scan_btn = st.button("Scan", type="primary", use_container_width=True, disabled=not selected_pkg_label)

    if scan_btn and selected_pkg_label:
        selected_pkg = pkg_options[selected_pkg_label]
        from portfolio.memory import get_adaptive_weights, check_outcomes
        check_outcomes()
        adaptive_weights = get_adaptive_weights()

        progress_bar = st.progress(0, text="Scanning...")
        combiner = SignalCombiner()

        # Show regime
        regime = combiner.regime_info
        st.info(f"Regime: **{regime.regime.value}** | VIX: {regime.vix_level:.1f} | "
                f"Breadth: {regime.breadth_pct:.0%} | SPY: {regime.spy_trend}")

        signals = []
        watchlist = get_package_symbols([selected_pkg])
        st.caption(f"Scanning: **{PACKAGE_META.get(selected_pkg, {}).get('name', selected_pkg)}** ({len(watchlist)} symbols)")

        for i, sym in enumerate(watchlist):
            try:
                sig = combiner.analyze(sym, adaptive_weights=adaptive_weights)
                sig = apply_timeframe_filter(sig)
                signals.append(sig)
            except Exception:
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
                "Top Reason": sig.reasons[1] if len(sig.reasons) > 1 else (sig.reasons[0] if sig.reasons else "-"),
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

    tab1, tab2, tab3 = st.tabs(["Overview", "Trade History", "Exit Signals"])

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

    with tab3:
        st.subheader("Active Exit Signals")
        rm = RiskManager(settings.risk)
        exits = rm.check_exit_signals()
        if exits:
            exit_rows = []
            for es in exits:
                exit_rows.append({
                    "Symbol": es.symbol,
                    "Type": es.exit_type,
                    "Exit %": f"{es.exit_pct:.0%}",
                    "Price": f"${es.exit_price:.2f}",
                    "Urgency": es.urgency,
                    "Reason": es.reason,
                })
            st.dataframe(pd.DataFrame(exit_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No active exit signals")


# ============================================================
# Page: Engine Performance
# ============================================================
elif page == "Engine Performance":
    st.header("Engine Performance")
    st.caption("Track how each engine performs over time - the learning system")

    from portfolio.memory import (
        get_engine_performance_summary, compute_engine_accuracy,
        get_analysis_history, check_outcomes,
    )

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Refresh Data", type="primary"):
            check_outcomes()
            compute_engine_accuracy()
            st.rerun()

    # Engine accuracy
    perf = get_engine_performance_summary()
    if perf:
        st.subheader("Engine Accuracy (last 90 days)")
        perf_rows = []
        for p in perf:
            perf_rows.append({
                "Engine": p["engine_name"].replace("_", " ").title(),
                "Accuracy": f"{p['accuracy']:.0%}",
                "Signals": p["total_signals"],
                "Correct": p["correct_signals"],
                "Avg Return (Correct)": f"{p['avg_return_when_correct']:+.1%}" if p['avg_return_when_correct'] else "-",
                "Avg Return (Wrong)": f"{p['avg_return_when_wrong']:+.1%}" if p['avg_return_when_wrong'] else "-",
            })
        st.dataframe(pd.DataFrame(perf_rows), use_container_width=True, hide_index=True)

        # Adaptive weights
        from portfolio.memory import get_adaptive_weights
        adaptive = get_adaptive_weights()
        if adaptive:
            st.subheader("Adaptive Weights")
            from engines.signal_combiner import DEFAULT_WEIGHTS
            weight_rows = []
            for eng in DEFAULT_WEIGHTS:
                weight_rows.append({
                    "Engine": eng.replace("_", " ").title(),
                    "Default Weight": f"{DEFAULT_WEIGHTS[eng]:.0%}",
                    "Adaptive Weight": f"{adaptive.get(eng, DEFAULT_WEIGHTS[eng]):.0%}",
                    "Change": f"{(adaptive.get(eng, DEFAULT_WEIGHTS[eng]) - DEFAULT_WEIGHTS[eng]):+.0%}",
                })
            st.dataframe(pd.DataFrame(weight_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No engine performance data yet. Run some analyses first, then check back after 5+ days.")

    # Recent analysis history
    st.subheader("Recent Analysis History")
    history = get_analysis_history(limit=20)
    if history:
        hist_rows = []
        for h in history:
            outcome = ""
            if h.get("actual_return_pct") is not None:
                ret = h["actual_return_pct"]
                correct = h.get("signal_correct")
                outcome = f"{ret:+.1%} {'correct' if correct else 'wrong'}"

            hist_rows.append({
                "Date": h["analysis_date"][:10] if h.get("analysis_date") else "",
                "Symbol": h.get("symbol", ""),
                "Action": h.get("action", ""),
                "Score": f"{h['combined_score']:+.3f}" if h.get("combined_score") is not None else "",
                "Confidence": f"{h['confidence']:.0%}" if h.get("confidence") is not None else "",
                "Regime": h.get("regime", ""),
                "5-Day Outcome": outcome,
            })
        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No analysis history yet")


# ============================================================
# Page: Backtest
# ============================================================
elif page == "Backtest":
    st.header("Backtesting")
    st.caption("Walk-forward backtest to validate the system")

    from config.watchlists import list_packages_by_region, PACKAGE_META, get_package_symbols as bt_get_pkg_symbols

    bt_pkg_options = {}
    for region, pkgs in list_packages_by_region().items():
        for key, name, count in pkgs:
            bt_pkg_options[f"{name} ({count} symbols) [{region}]"] = key

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        months = st.slider("Backtest Period (months)", min_value=3, max_value=24, value=12)
    with col2:
        symbols_option = st.selectbox("Symbols", ["Select Package", "Custom"])
    with col3:
        bt_mode = st.radio("Mode", ["Full (real combiner)", "Fast (quick score)"], index=1,
                           help="Full uses real 5-engine combiner with slippage/commission. Fast uses simplified scoring.")

    if symbols_option == "Custom":
        custom_syms = st.text_input("Enter symbols (comma-separated)", value="NVDA,AAPL,MSFT,TSLA,AMD")
        symbols = [s.strip().upper() for s in custom_syms.split(",") if s.strip()]
    else:
        bt_pkg_label = st.selectbox("Package", list(bt_pkg_options.keys()), index=None,
                                     placeholder="Choose a package...", key="bt_pkg")
        if bt_pkg_label:
            symbols = bt_get_pkg_symbols([bt_pkg_options[bt_pkg_label]])
        else:
            symbols = []

    run_btn = st.button("Run Backtest", type="primary", use_container_width=True, disabled=len(symbols) == 0)

    if run_btn and symbols:
        from portfolio.backtest import run_backtest, format_backtest_report

        fast_mode = "Fast" in bt_mode
        mode_label = "fast" if fast_mode else "full"
        with st.spinner(f"Running {mode_label} backtest on {len(symbols)} symbols for {months} months..."):
            result = run_backtest(symbols=symbols, months=months, fast=fast_mode)

        st.caption(f"Mode: **{result.mode.upper()}** {'(simplified scoring)' if result.mode == 'fast' else '(real 5-engine combiner)'}")

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Return", f"{result.total_return_pct:+.1%}")
        col2.metric("SPY Return", f"{result.spy_return_pct:+.1%}")
        col3.metric("Excess Return", f"{result.excess_return_pct:+.1%}",
                     delta=f"vs SPY")
        col4.metric("Sharpe Ratio", f"{result.sharpe_ratio:.2f}")

        col5, col6, col7, col8 = st.columns(4)
        col5.metric("Total Trades", result.total_trades)
        col6.metric("Win Rate", f"{result.win_rate:.0%}")
        col7.metric("Profit Factor", f"{result.profit_factor:.2f}")
        col8.metric("Max Drawdown", f"{result.max_drawdown_pct:.1%}")

        # Costs (full mode only)
        if result.total_costs > 0:
            st.subheader("Trading Costs")
            total_slippage = sum(t.slippage_cost for t in result.trades)
            total_commission = sum(t.commission_cost for t in result.trades)
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Costs", f"${result.total_costs:,.2f}")
            col2.metric("Slippage", f"${total_slippage:,.2f}")
            col3.metric("Commission", f"${total_commission:,.2f}")

        # Regime breakdown
        if result.regime_breakdown:
            st.subheader("Performance by Regime")
            regime_rows = []
            for regime, stats in sorted(result.regime_breakdown.items()):
                regime_rows.append({
                    "Regime": regime,
                    "Trades": stats["trades"],
                    "Win Rate": f"{stats['win_rate']:.0%}",
                    "Avg Return": f"{stats['avg_return']:+.1%}",
                })
            st.dataframe(pd.DataFrame(regime_rows), use_container_width=True, hide_index=True)

        # Equity curve
        if result.equity_curve:
            st.subheader("Equity Curve")
            eq_df = pd.DataFrame({"Portfolio Value": result.equity_curve})
            st.line_chart(eq_df)

        # Trades table
        if result.trades:
            st.subheader(f"All Trades ({len(result.trades)})")
            trade_rows = []
            for t in sorted(result.trades, key=lambda x: x.pnl_pct, reverse=True):
                row = {
                    "Symbol": t.symbol,
                    "Entry": t.entry_date,
                    "Exit": t.exit_date,
                    "Entry $": f"${t.entry_price:.2f}",
                    "Exit $": f"${t.exit_price:.2f}",
                    "Return": f"{t.pnl_pct:+.1%}",
                    "PnL": f"${t.pnl:+,.0f}",
                }
                if result.mode == "full":
                    row["Regime"] = t.regime
                    row["Costs"] = f"${t.slippage_cost + t.commission_cost:.2f}"
                trade_rows.append(row)
            st.dataframe(pd.DataFrame(trade_rows), use_container_width=True, hide_index=True)


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

    env_path = os.path.join(os.path.dirname(__file__), ".env")

    def _read_env_file():
        """Read .env file into a dict (preserves comments as None values)."""
        vals = {}
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, val = line.partition("=")
                        vals[key.strip()] = val.strip()
        return vals

    def _write_env(updates: dict):
        """Update .env file, preserving comments and adding new keys."""
        lines = []
        if os.path.exists(env_path):
            with open(env_path) as f:
                lines = f.readlines()

        updated_keys = set()
        new_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.partition("=")[0].strip()
                if key in updates:
                    new_lines.append(f"{key}={updates[key]}\n")
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        for key, val in updates.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={val}\n")

        with open(env_path, "w") as f:
            f.writelines(new_lines)

    # --- LLM Configuration ---
    st.subheader("LLM Configuration")
    llm_modes = {"off - $0/month (algorithmic only)": "off",
                 "haiku - ~$0.0003/run (AI summaries)": "haiku",
                 "sonnet - ~$0.01/run (deep AI analysis)": "sonnet"}
    current_mode = settings.llm_mode.value
    current_label = [k for k, v in llm_modes.items() if v == current_mode][0]

    selected_label = st.selectbox("LLM Mode", list(llm_modes.keys()),
                                  index=list(llm_modes.keys()).index(current_label))
    selected_mode = llm_modes[selected_label]

    api_key_val = settings.anthropic_api_key or ""
    if selected_mode != "off":
        api_key_val = st.text_input("Anthropic API Key", value=api_key_val, type="password",
                                    help="Required for haiku/sonnet modes")

    if st.button("Save LLM Settings"):
        updates = {"LLM_MODE": selected_mode}
        if selected_mode != "off" and api_key_val:
            updates["ANTHROPIC_API_KEY"] = api_key_val
        _write_env(updates)
        st.success(f"Saved LLM_MODE={selected_mode}. Restart the app to apply.")

    st.divider()

    # --- Risk Parameters ---
    st.subheader("Risk Parameters")
    params = settings.risk

    col1, col2 = st.columns(2)
    with col1:
        new_max_pos = st.slider("Max Position Size", 0.01, 0.50, params.max_position_pct,
                                0.01, format="%.0f%%",
                                help="Max allocation per position")
        new_heat = st.slider("Max Portfolio Heat", 0.01, 0.30, params.max_portfolio_heat,
                             0.01, format="%.0f%%",
                             help="Max total portfolio risk")
        new_dd = st.slider("Drawdown Circuit Breaker", -0.50, -0.01,
                           params.drawdown_circuit_breaker, 0.01, format="%.0f%%",
                           help="Stop trading at this drawdown from peak")
        new_max_pos_count = st.number_input("Max Simultaneous Positions", 1, 20,
                                            params.max_simultaneous_positions)
        new_sector = st.slider("Max Sector Concentration", 0.10, 1.00,
                               params.max_sector_concentration, 0.05, format="%.0f%%",
                               help="Max allocation to one sector")

    with col2:
        new_cash = st.slider("Cash Reserve", 0.0, 0.50, params.cash_reserve_pct,
                             0.05, format="%.0f%%",
                             help="Minimum cash reserve")
        new_daily = st.slider("Max Daily Risk", 0.01, 0.20, params.max_daily_risk,
                              0.01, format="%.0f%%")
        new_profit = st.slider("Min Profit Target", 0.01, 0.50, params.min_profit_target,
                               0.01, format="%.0f%%")
        new_atr_swing = st.number_input("Stop Loss ATR (Swing)", 0.5, 5.0,
                                        params.stop_loss_atr_swing, 0.1)
        new_atr_pos = st.number_input("Stop Loss ATR (Position)", 0.5, 5.0,
                                      params.stop_loss_atr_position, 0.1)

    if st.button("Save Risk Parameters"):
        _write_env({
            "MAX_POSITION_PCT": f"{new_max_pos:.2f}",
            "MAX_PORTFOLIO_HEAT": f"{new_heat:.2f}",
            "DRAWDOWN_CIRCUIT_BREAKER": f"{new_dd:.2f}",
            "MAX_SIMULTANEOUS_POSITIONS": str(int(new_max_pos_count)),
            "MAX_SECTOR_CONCENTRATION": f"{new_sector:.2f}",
            "CASH_RESERVE_PCT": f"{new_cash:.2f}",
            "MAX_DAILY_RISK": f"{new_daily:.2f}",
            "MIN_PROFIT_TARGET": f"{new_profit:.2f}",
            "STOP_LOSS_ATR_SWING": f"{new_atr_swing:.1f}",
            "STOP_LOSS_ATR_POSITION": f"{new_atr_pos:.1f}",
        })
        st.success("Risk parameters saved. Restart the app to apply.")

    st.divider()

    # --- API Keys ---
    st.subheader("API Keys")
    st.caption("Keys are saved to .env (gitignored, never committed)")

    new_anthropic = st.text_input("Anthropic API Key", value=settings.anthropic_api_key,
                                  type="password", help="For LLM modes (haiku/sonnet)")
    new_sec = st.text_input("SEC API Key", value=settings.sec_api_key,
                            type="password", help="Free at https://sec-api.io/")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        new_reddit_id = st.text_input("Reddit Client ID", value=settings.reddit_client_id,
                                      type="password", help="https://www.reddit.com/prefs/apps")
    with col_r2:
        new_reddit_secret = st.text_input("Reddit Client Secret", value=settings.reddit_client_secret,
                                          type="password")
    new_av = st.text_input("Alpha Vantage API Key", value=settings.alpha_vantage_api_key,
                           type="password", help="Free at https://www.alphavantage.co/support/#api-key")
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        new_avanza_user = st.text_input("Avanza Username", value=settings.avanza_username,
                                        help="Optional - for auto-trading")
    with col_a2:
        new_avanza_pass = st.text_input("Avanza Password", value=settings.avanza_password,
                                        type="password")

    if st.button("Save API Keys"):
        key_updates = {}
        if new_anthropic: key_updates["ANTHROPIC_API_KEY"] = new_anthropic
        if new_sec: key_updates["SEC_API_KEY"] = new_sec
        if new_reddit_id: key_updates["REDDIT_CLIENT_ID"] = new_reddit_id
        if new_reddit_secret: key_updates["REDDIT_CLIENT_SECRET"] = new_reddit_secret
        if new_av: key_updates["ALPHA_VANTAGE_API_KEY"] = new_av
        if new_avanza_user: key_updates["AVANZA_USERNAME"] = new_avanza_user
        if new_avanza_pass: key_updates["AVANZA_PASSWORD"] = new_avanza_pass
        if key_updates:
            _write_env(key_updates)
            st.success(f"Saved {len(key_updates)} API key(s). Restart the app to apply.")
        else:
            st.info("No keys to save (all fields empty).")

    st.divider()

    # --- Packages ---
    st.subheader("Active Packages")
    from config.watchlists import get_total_symbol_count, WATCHLIST_PACKAGES
    st.write(f"**Active:** {', '.join(settings.active_packages)} ({len(settings.watchlist)} symbols)")
    st.write(f"**Total available:** {len(WATCHLIST_PACKAGES)} packages, {get_total_symbol_count()} symbols")
    st.caption("Set `ACTIVE_PACKAGES` in .env to change default packages. Scans always prompt for package selection.")
