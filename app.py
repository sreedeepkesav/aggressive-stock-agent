"""Stock Analysis Agent — Modern Dashboard.

A clean, intuitive web interface for regime-aware stock analysis.
Run with: streamlit run app.py
"""

import os
import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import streamlit as st
import pandas as pd
import altair as alt

from config.settings import Settings, RiskParams
from engines.signal_combiner import SignalCombiner, CombinedSignal, DEFAULT_WEIGHTS
from engines.timeframe import apply_timeframe_filter
from portfolio import state
from portfolio.risk import RiskManager
from portfolio.tracker import get_portfolio_summary, get_trade_stats, sharpe_ratio, vs_spy

# --- Page config ---
st.set_page_config(
    page_title="Stock Agent",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS for modern look ---
st.markdown("""
<style>
    /* Clean up default streamlit padding */
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f1419 0%, #1a1f2e 100%);
    }
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stMarkdown span,
    [data-testid="stSidebar"] label {
        color: #c8cdd3 !important;
    }

    /* Card component */
    .metric-card {
        background: linear-gradient(135deg, #1e2738 0%, #1a2332 100%);
        border: 1px solid #2a3a4a;
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 0.8rem;
    }
    .metric-card h4 {
        color: #7b8794;
        font-size: 0.8rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin: 0 0 0.4rem 0;
    }
    .metric-card .value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #e8ecf1;
        margin: 0;
    }
    .metric-card .sub {
        font-size: 0.8rem;
        color: #5a6b7d;
        margin-top: 0.2rem;
    }

    /* Regime banner */
    .regime-banner {
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }
    .regime-trending-up {
        background: linear-gradient(135deg, #0d3b1e 0%, #1a4a2e 100%);
        border: 1px solid #2a6b3e;
    }
    .regime-trending-down {
        background: linear-gradient(135deg, #3b0d0d 0%, #4a1a1a 100%);
        border: 1px solid #6b2a2a;
    }
    .regime-range-bound {
        background: linear-gradient(135deg, #2a2a0d 0%, #3a3a1a 100%);
        border: 1px solid #5a5a2a;
    }
    .regime-high-volatility {
        background: linear-gradient(135deg, #3b1e0d 0%, #4a2a1a 100%);
        border: 1px solid #6b3e2a;
    }
    .regime-unknown {
        background: linear-gradient(135deg, #1e2738 0%, #1a2332 100%);
        border: 1px solid #2a3a4a;
    }
    .regime-banner .regime-label {
        font-size: 1.1rem;
        font-weight: 700;
        color: #e8ecf1;
    }
    .regime-banner .regime-detail {
        font-size: 0.85rem;
        color: #9aa5b4;
    }

    /* Signal badges */
    .signal-strong-buy { color: #00c853; font-weight: 700; }
    .signal-buy { color: #4caf50; font-weight: 600; }
    .signal-hold { color: #9e9e9e; }
    .signal-sell { color: #ef5350; font-weight: 600; }
    .signal-strong-sell { color: #d32f2f; font-weight: 700; }

    /* Section headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #c8cdd3;
        border-bottom: 1px solid #2a3a4a;
        padding-bottom: 0.5rem;
        margin: 1.5rem 0 1rem 0;
    }

    /* Status dot */
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
    }
    .dot-green { background: #00c853; }
    .dot-red { background: #d32f2f; }
    .dot-yellow { background: #ffc107; }
    .dot-gray { background: #616161; }

    /* Data tables */
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        padding-left: 0;
        padding-right: 0;
    }
</style>
""", unsafe_allow_html=True)


# --- Init ---
state.init_db()
settings = Settings.load()


# ============================================================
# Helper functions
# ============================================================

def card(title: str, value: str, sub: str = "", color: str = "") -> str:
    """Generate HTML for a metric card."""
    style = f'color: {color};' if color else ''
    return f"""
    <div class="metric-card">
        <h4>{title}</h4>
        <p class="value" style="{style}">{value}</p>
        {'<p class="sub">' + sub + '</p>' if sub else ''}
    </div>
    """


def regime_banner(regime_info) -> str:
    """Generate HTML for the regime status banner."""
    regime_name = regime_info.regime.value
    css_class = f"regime-{regime_name.lower().replace('_', '-')}"

    indicators = []
    indicators.append(f"VIX {regime_info.vix_level:.1f}")
    indicators.append(f"Breadth {regime_info.breadth_pct:.0%}")
    indicators.append(f"SPY {regime_info.spy_trend}")
    indicators.append(f"Credit {regime_info.credit_stress:.2f}")
    indicators.append(f"YC {'INV' if regime_info.yield_curve_inverted else 'OK'}")
    indicators.append(f"VTS {regime_info.vix_term_structure}")

    block_warning = ""
    if regime_info.block_buys:
        block_warning = '<span style="color: #ef5350; font-weight: 600; margin-left: 1rem;">BUY SIGNALS BLOCKED</span>'

    return f"""
    <div class="regime-banner {css_class}">
        <div>
            <div class="regime-label">{regime_name.replace('_', ' ')}{block_warning}</div>
            <div class="regime-detail">{' · '.join(indicators)}</div>
        </div>
    </div>
    """


def signal_badge(action: str) -> str:
    """Return styled signal text."""
    css = f"signal-{action.lower().replace('_', '-')}"
    return f'<span class="{css}">{action}</span>'


def signal_color(action: str) -> str:
    colors = {
        "STRONG_BUY": "#00c853", "BUY": "#4caf50",
        "HOLD": "#9e9e9e",
        "SELL": "#ef5350", "STRONG_SELL": "#d32f2f",
    }
    return colors.get(action, "#9e9e9e")


def render_engine_results(sig: CombinedSignal):
    """Render engine results as a styled table."""
    rows = []
    for name, result in sig.engine_results.items():
        rows.append({
            "Engine": name.replace("_", " ").title(),
            "Signal": result.signal,
            "Confidence": f"{result.confidence:.0%}",
            "Score": f"{result.numeric_signal:+.1f}",
            "Top Reason": result.reasons[0] if result.reasons else "-",
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.markdown("### Stock Agent")

    page = st.radio(
        "Navigate",
        ["Dashboard", "Analyze", "Scan", "Paper Trade", "Portfolio", "Backtest", "Discover", "Settings"],
        index=0,
        label_visibility="collapsed",
    )

    st.divider()

    # Regime summary
    try:
        from engines.regime import detect_regime
        regime = detect_regime()
        st.markdown(f"**Regime:** {regime.regime.value.replace('_', ' ')}")
        st.caption(f"VIX {regime.vix_level:.1f} · Breadth {regime.breadth_pct:.0%}")
        if regime.block_buys:
            st.error("Buys blocked (VIX > 35)")
    except Exception:
        st.caption("Regime: loading...")
        regime = None

    st.divider()
    st.caption(f"LLM: {settings.llm_mode.value}")
    st.caption(f"Risk: {settings.risk.max_position_pct:.0%} max pos")
    st.caption(f"Positions: {settings.risk.max_simultaneous_positions} max")


# ============================================================
# Page: Dashboard (Home)
# ============================================================
if page == "Dashboard":
    st.markdown("## Dashboard")

    # Regime banner
    try:
        if regime:
            st.markdown(regime_banner(regime), unsafe_allow_html=True)
    except Exception:
        pass

    # Record regime for alerting
    try:
        from alerts.regime_alerts import record_regime
        if regime:
            change = record_regime(regime)
            if change:
                st.warning(f"Regime changed: {change['previous']} → {change['current']}")
    except Exception:
        pass

    # Key metrics row
    from portfolio.memory import (
        get_engine_performance_summary, get_analysis_history,
        compute_engine_accuracy, get_adaptive_weights, check_outcomes,
    )
    from portfolio.calibration import get_calibration_summary

    history = get_analysis_history(limit=100)
    perf = get_engine_performance_summary()
    cal_summary = get_calibration_summary()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(card("Total Analyses", str(len(history)), "in database"), unsafe_allow_html=True)
    with col2:
        outcomes_count = sum(1 for h in history if h.get("actual_return_pct") is not None)
        st.markdown(card("Outcomes Tracked", str(outcomes_count),
                         f"{'Ready for adaptive' if outcomes_count >= 30 else f'{30 - outcomes_count} more needed'}"),
                    unsafe_allow_html=True)
    with col3:
        if perf:
            best = max(perf, key=lambda p: p.get("accuracy", 0))
            st.markdown(card("Best Engine", best["engine_name"].replace("_", " ").title(),
                             f"{best['accuracy']:.0%} accuracy"),
                        unsafe_allow_html=True)
        else:
            st.markdown(card("Best Engine", "—", "No data yet"), unsafe_allow_html=True)
    with col4:
        adaptive = get_adaptive_weights()
        status = "Active" if adaptive else "Collecting data"
        dot = "dot-green" if adaptive else "dot-yellow"
        st.markdown(card("Adaptive Learning",
                         f'<span class="status-dot {dot}"></span>{status}',
                         f"{outcomes_count}/30 samples"),
                    unsafe_allow_html=True)

    # Engine Performance Chart
    if perf:
        st.markdown('<div class="section-header">Engine Accuracy (Last 90 Days)</div>', unsafe_allow_html=True)

        perf_df = pd.DataFrame([{
            "Engine": p["engine_name"].replace("_", " ").title(),
            "Accuracy": p["accuracy"],
            "Signals": p["total_signals"],
        } for p in perf])

        bars = alt.Chart(perf_df).mark_bar(
            cornerRadiusTopLeft=4, cornerRadiusTopRight=4,
        ).encode(
            x=alt.X("Engine:N", sort="-y", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Accuracy:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format=".0%")),
            color=alt.condition(
                alt.datum.Accuracy >= 0.5,
                alt.value("#4caf50"),
                alt.value("#ef5350"),
            ),
            tooltip=["Engine", alt.Tooltip("Accuracy:Q", format=".1%"), "Signals"],
        ).properties(height=280)

        # Add 50% baseline
        rule = alt.Chart(pd.DataFrame({"y": [0.5]})).mark_rule(
            color="#5a6b7d", strokeDash=[4, 4]
        ).encode(y="y:Q")

        st.altair_chart(bars + rule, use_container_width=True)

    # Confidence Calibration
    cal_data = cal_summary.get("buckets", [])
    if cal_data and cal_summary.get("total_outcomes", 0) >= 10:
        st.markdown('<div class="section-header">Confidence Calibration</div>', unsafe_allow_html=True)

        col1, col2 = st.columns([2, 1])
        with col1:
            cal_df = pd.DataFrame(cal_data)
            if not cal_df.empty:
                cal_chart_df = cal_df.melt(
                    id_vars=["bucket", "count"],
                    value_vars=["predicted_avg", "actual_win_rate"],
                    var_name="Type",
                    value_name="Rate",
                )
                cal_chart_df["Type"] = cal_chart_df["Type"].map({
                    "predicted_avg": "Predicted Confidence",
                    "actual_win_rate": "Actual Win Rate",
                })

                cal_chart = alt.Chart(cal_chart_df).mark_bar(
                    cornerRadiusTopLeft=3, cornerRadiusTopRight=3,
                ).encode(
                    x=alt.X("bucket:N", title="Confidence Bucket", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("Rate:Q", title="Rate", axis=alt.Axis(format=".0%")),
                    color=alt.Color("Type:N", scale=alt.Scale(
                        domain=["Predicted Confidence", "Actual Win Rate"],
                        range=["#5a6b7d", "#4caf50"],
                    )),
                    xOffset="Type:N",
                    tooltip=["bucket", "Type", alt.Tooltip("Rate:Q", format=".1%"), "count"],
                ).properties(height=250)

                st.altair_chart(cal_chart, use_container_width=True)

        with col2:
            overconf = cal_summary.get("avg_overconfidence", 0)
            if overconf > 0.05:
                st.warning(f"System is overconfident by {overconf:.1%}")
            elif overconf < -0.05:
                st.info(f"System is underconfident by {abs(overconf):.1%}")
            else:
                st.success("Confidence is well-calibrated")

            st.caption(f"Based on {cal_summary.get('total_outcomes', 0)} outcomes")
            if cal_summary.get("worst_bucket"):
                st.caption(f"Worst bucket: {cal_summary['worst_bucket']} (off by {cal_summary.get('worst_diff', 0):+.1%})")

    # Recent signal history
    st.markdown('<div class="section-header">Recent Analyses</div>', unsafe_allow_html=True)

    if history:
        recent_rows = []
        for h in history[:15]:
            outcome = ""
            if h.get("actual_return_pct") is not None:
                ret = h["actual_return_pct"]
                correct = h.get("signal_correct")
                icon = "+" if correct else "-"
                outcome = f"{icon} {ret:+.1%}"

            recent_rows.append({
                "Date": h["analysis_date"][:10] if h.get("analysis_date") else "",
                "Symbol": h.get("symbol", ""),
                "Action": h.get("action", ""),
                "Score": f"{h['combined_score']:+.3f}" if h.get("combined_score") is not None else "",
                "Confidence": f"{h['confidence']:.0%}" if h.get("confidence") is not None else "",
                "Regime": h.get("regime", ""),
                "Outcome (5d)": outcome,
            })
        st.dataframe(pd.DataFrame(recent_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No analyses yet. Use the **Analyze** tab to start building your history.")

    # Regime change log
    try:
        from alerts.regime_alerts import get_regime_changes
        changes = get_regime_changes(limit=5)
        if changes:
            st.markdown('<div class="section-header">Recent Regime Changes</div>', unsafe_allow_html=True)
            for c in changes:
                ts = c["timestamp"][:16] if c.get("timestamp") else ""
                st.markdown(
                    f"`{ts}` — **{c['from_regime']}** → **{c['to_regime']}** "
                    f"(VIX {c.get('vix', 0):.1f}, Breadth {c.get('breadth', 0):.0%})"
                )
    except Exception:
        pass


# ============================================================
# Page: Analyze
# ============================================================
elif page == "Analyze":
    st.markdown("## Ticker Analysis")
    st.caption("All 5 engines + regime detection + multi-timeframe confirmation")

    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = st.text_input("Ticker", value="NVDA", max_chars=10,
                               placeholder="Enter ticker symbol...").strip().upper()
    with col2:
        analyze_btn = st.button("Analyze", type="primary", use_container_width=True)

    if analyze_btn and symbol:
        with st.spinner(f"Analyzing {symbol}..."):
            from portfolio.memory import get_adaptive_weights, save_analysis, check_outcomes
            check_outcomes()
            adaptive_weights = get_adaptive_weights()

            combiner = SignalCombiner()
            sig = combiner.analyze(symbol, adaptive_weights=adaptive_weights)
            sig = apply_timeframe_filter(sig)

        # Regime banner
        if sig.regime:
            st.markdown(regime_banner(sig.regime), unsafe_allow_html=True)

        # Main signal
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(card("Action", sig.action, color=signal_color(sig.action)),
                        unsafe_allow_html=True)
        with col2:
            st.markdown(card("Score", f"{sig.combined_score:+.3f}"), unsafe_allow_html=True)
        with col3:
            st.markdown(card("Confidence", f"{sig.confidence:.0%}"), unsafe_allow_html=True)
        with col4:
            st.markdown(card("Agreement", f"{sig.agreement_pct:.0%}"), unsafe_allow_html=True)

        if sig.is_actionable:
            st.success("ACTIONABLE — High confidence with engine agreement")
        elif sig.action == "HOLD":
            st.info("HOLD — No clear signal")
        else:
            st.warning("Low confidence — not actionable")

        # Engine breakdown
        st.markdown('<div class="section-header">Engine Breakdown</div>', unsafe_allow_html=True)
        render_engine_results(sig)

        # Insider signal + reasons
        col_left, col_right = st.columns([1, 1])
        with col_left:
            if sig.reasons:
                with st.expander("Signal Reasoning", expanded=False):
                    for r in sig.reasons[:10]:
                        st.markdown(f"- {r}")
        with col_right:
            try:
                from data.insider_signal import get_insider_signal
                insider = get_insider_signal(symbol)
                if insider["total_filings"] > 0:
                    with st.expander(f"Insider Activity ({insider['net_sentiment']})", expanded=False):
                        ins_color = {"BULLISH": "#4caf50", "BEARISH": "#ef5350"}.get(insider["net_sentiment"], "#9e9e9e")
                        st.markdown(f'<span style="color:{ins_color};font-weight:600">{insider["net_sentiment"]}</span> — {insider["reason"]}',
                                    unsafe_allow_html=True)
                        st.caption(f"Buys: {insider['buy_count']} | Sells: {insider['sell_count']} | "
                                   f"Unique buyers: {insider.get('unique_buyers', 0)} | "
                                   f"Recent buys (30d): {insider.get('recent_buys', 0)}")
            except Exception:
                pass

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

        # Risk check
        if sig.is_actionable and sig.action in ("STRONG_BUY", "BUY"):
            st.markdown('<div class="section-header">Risk Assessment</div>', unsafe_allow_html=True)
            rm = RiskManager(settings.risk)
            entry = momentum_result.metadata.get("entry", 0) if momentum_result else 0
            if entry > 0:
                stop = rm.calculate_stop_loss(symbol, entry)
                qty = rm.calculate_position_size(entry, stop)
                proposed_value = qty * entry
                check = rm.check_can_open_position(symbol, proposed_value)

                if check["allowed"]:
                    st.success(f"Risk check passed: {qty} shares @ ${entry:.2f}, stop ${stop:.2f}")
                else:
                    st.error("Risk check blocked:")
                    for reason in check["reasons"]:
                        st.markdown(f"- {reason}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(card("Qty", str(qty)), unsafe_allow_html=True)
                with col2:
                    st.markdown(card("Entry", f"${entry:.2f}"), unsafe_allow_html=True)
                with col3:
                    st.markdown(card("Stop Loss", f"${stop:.2f}"), unsafe_allow_html=True)


# ============================================================
# Page: Market Scan
# ============================================================
elif page == "Scan":
    st.markdown("## Market Scan")
    st.caption("Scan watchlist packages with regime-aware analysis")

    from config.watchlists import list_packages_by_region, PACKAGE_META, get_package_symbols

    pkg_options = {}
    for region, pkgs in list_packages_by_region().items():
        for key, name, count in pkgs:
            pkg_options[f"{name} ({count}) [{region}]"] = key

    col1, col2 = st.columns([1, 1])
    with col1:
        selected_pkg_label = st.selectbox(
            "Package", list(pkg_options.keys()),
            index=None, placeholder="Choose a package...",
        )
    with col2:
        top_n = st.slider("Top N results", min_value=3, max_value=30, value=10)

    if not selected_pkg_label:
        st.info("Select a package to start scanning.")

    scan_btn = st.button("Scan", type="primary", use_container_width=True, disabled=not selected_pkg_label)

    if scan_btn and selected_pkg_label:
        selected_pkg = pkg_options[selected_pkg_label]
        from portfolio.memory import get_adaptive_weights, check_outcomes
        check_outcomes()
        adaptive_weights = get_adaptive_weights()

        progress = st.progress(0, text="Starting scan...")
        combiner = SignalCombiner()

        # Show regime
        r = combiner.regime_info
        st.markdown(regime_banner(r), unsafe_allow_html=True)

        signals = []
        watchlist = get_package_symbols([selected_pkg])
        st.caption(f"Scanning {len(watchlist)} symbols...")

        for i, sym in enumerate(watchlist):
            try:
                sig = combiner.analyze(sym, adaptive_weights=adaptive_weights)
                sig = apply_timeframe_filter(sig)
                signals.append(sig)
            except Exception:
                pass
            progress.progress((i + 1) / len(watchlist), text=f"Analyzing {sym}...")

        progress.empty()
        signals.sort(key=lambda s: s.combined_score, reverse=True)

        actionable = [s for s in signals if s.is_actionable]
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(card("Actionable", str(len(actionable)), f"of {len(signals)} scanned"),
                        unsafe_allow_html=True)
        with col2:
            buys = sum(1 for s in signals if s.action in ("BUY", "STRONG_BUY"))
            sells = sum(1 for s in signals if s.action in ("SELL", "STRONG_SELL"))
            st.markdown(card("Direction", f"{buys} buy / {sells} sell"),
                        unsafe_allow_html=True)

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
                "Reason": sig.reasons[1] if len(sig.reasons) > 1 else (sig.reasons[0] if sig.reasons else "-"),
            })

        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # Top 3 detail
        if signals[:3]:
            st.markdown('<div class="section-header">Top 3 Detailed</div>', unsafe_allow_html=True)
            for sig in signals[:3]:
                with st.expander(f"{sig.symbol} — {sig.action} ({sig.combined_score:+.3f})"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Score", f"{sig.combined_score:+.3f}")
                    col2.metric("Confidence", f"{sig.confidence:.0%}")
                    col3.metric("Agreement", f"{sig.agreement_pct:.0%}")
                    render_engine_results(sig)


# ============================================================
# Page: Paper Trade
# ============================================================
elif page == "Paper Trade":
    st.markdown("## Paper Trading")
    st.caption("Simulated trading with real data — prove the system before risking capital")

    from portfolio.paper_trader import (
        PaperTrader, paper_get_positions, paper_get_trades,
        paper_get_daily_log, paper_get_cash, paper_get_peak,
        _ensure_paper_tables, kelly_fraction,
    )
    _ensure_paper_tables()

    tab_pt1, tab_pt2, tab_pt3, tab_pt4 = st.tabs(["Overview", "Run Cycle", "Trade Log", "Attribution"])

    with tab_pt1:
        trader = PaperTrader()
        summary_pt = trader.get_summary()

        # KPI cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            pv = summary_pt["portfolio_value"]
            st.markdown(card("Paper Portfolio", f"${pv:,.0f}",
                             f"Peak: ${summary_pt['peak_value']:,.0f}"),
                        unsafe_allow_html=True)
        with col2:
            dd_color = "#ef5350" if summary_pt['drawdown'] < -0.05 else "#9e9e9e"
            st.markdown(card("Drawdown", f"{summary_pt['drawdown']:.1%}", color=dd_color),
                        unsafe_allow_html=True)
        with col3:
            wr_color = "#4caf50" if summary_pt['win_rate'] >= 0.5 else "#ef5350"
            st.markdown(card("Win Rate", f"{summary_pt['win_rate']:.0%}",
                             f"{summary_pt['total_trades']} trades", color=wr_color),
                        unsafe_allow_html=True)
        with col4:
            st.markdown(card("Sharpe", f"{summary_pt['sharpe_ratio']:.2f}",
                             f"Kelly: {summary_pt['kelly_fraction']:.1%}"),
                        unsafe_allow_html=True)

        col5, col6, col7 = st.columns(3)
        with col5:
            pnl_color = "#4caf50" if summary_pt['total_pnl'] >= 0 else "#ef5350"
            st.markdown(card("Total PnL", f"${summary_pt['total_pnl']:+,.0f}", color=pnl_color),
                        unsafe_allow_html=True)
        with col6:
            st.markdown(card("Profit Factor", f"{summary_pt['profit_factor']:.2f}"),
                        unsafe_allow_html=True)
        with col7:
            st.markdown(card("Cash", f"${summary_pt['cash']:,.0f}"),
                        unsafe_allow_html=True)

        # Open positions
        if summary_pt["positions"]:
            st.markdown('<div class="section-header">Open Positions</div>', unsafe_allow_html=True)
            pos_rows = []
            for p in summary_pt["positions"]:
                pos_rows.append({
                    "Symbol": p["symbol"],
                    "Qty": p["qty"],
                    "Entry": f"${p['entry']:.2f}",
                    "Current": f"${p['current']:.2f}",
                    "PnL": f"${p['pnl']:+.2f}",
                    "Return": p["pnl_pct"],
                    "Stop": f"${p['stop']:.2f}",
                    "Signal": p["signal"],
                })
            st.dataframe(pd.DataFrame(pos_rows), use_container_width=True, hide_index=True)

        # Equity curve from daily log
        daily = paper_get_daily_log(60)
        if daily:
            st.markdown('<div class="section-header">Equity Curve</div>', unsafe_allow_html=True)
            eq_data = list(reversed(daily))
            eq_df = pd.DataFrame({
                "Day": range(len(eq_data)),
                "Value": [d["portfolio_value"] for d in eq_data],
            })
            eq_chart = alt.Chart(eq_df).mark_area(
                line={"color": "#4caf50"},
                color=alt.Gradient(
                    gradient="linear",
                    stops=[
                        alt.GradientStop(color="rgba(76, 175, 80, 0.3)", offset=0),
                        alt.GradientStop(color="rgba(76, 175, 80, 0.02)", offset=1),
                    ],
                    x1=1, x2=1, y1=1, y2=0,
                ),
            ).encode(
                x=alt.X("Day:Q", title="Days"),
                y=alt.Y("Value:Q", title="Portfolio ($)", scale=alt.Scale(zero=False)),
                tooltip=["Day", alt.Tooltip("Value:Q", format="$,.0f")],
            ).properties(height=250)
            st.altair_chart(eq_chart, use_container_width=True)

    with tab_pt2:
        st.markdown('<div class="section-header">Execute Paper Trading Cycle</div>', unsafe_allow_html=True)
        st.caption("Runs the full signal pipeline: analyze → risk check → paper trade")

        from config.watchlists import list_packages_by_region, get_package_symbols as pt_get_pkg

        pt_pkg_options = {}
        for region, pkgs in list_packages_by_region().items():
            for key, name, count in pkgs:
                pt_pkg_options[f"{name} ({count}) [{region}]"] = key

        col1, col2 = st.columns([2, 1])
        with col1:
            pt_src = st.selectbox("Symbols", ["Active Watchlist", "Package", "Custom"], key="pt_src")
        with col2:
            pass

        if pt_src == "Custom":
            pt_custom = st.text_input("Symbols", value="NVDA,AAPL,MSFT,TSLA,AMD", key="pt_custom")
            pt_symbols = [s.strip().upper() for s in pt_custom.split(",") if s.strip()]
        elif pt_src == "Package":
            pt_label = st.selectbox("Package", list(pt_pkg_options.keys()),
                                    index=None, placeholder="Choose...", key="pt_pkg")
            pt_symbols = pt_get_pkg([pt_pkg_options[pt_label]]) if pt_label else []
        else:
            pt_symbols = settings.watchlist[:20]  # Limit for speed

        if st.button("Run Paper Trading Cycle", type="primary", use_container_width=True,
                     disabled=len(pt_symbols) == 0):
            with st.spinner(f"Paper trading {len(pt_symbols)} symbols..."):
                trader = PaperTrader()
                result = trader.run_daily_cycle(pt_symbols)

            st.success(f"Cycle complete: ${result['portfolio_value']:,.0f} portfolio")
            if result["actions"]:
                st.markdown('<div class="section-header">Actions Taken</div>', unsafe_allow_html=True)
                for a in result["actions"]:
                    st.markdown(f"- {a}")
            else:
                st.info("No trades executed this cycle (no actionable signals or risk limits reached)")

    with tab_pt3:
        st.markdown('<div class="section-header">Paper Trade History</div>', unsafe_allow_html=True)
        trades_pt = paper_get_trades(50)
        if trades_pt:
            t_rows = []
            for t in trades_pt:
                pnl_str = f"${t['pnl']:+,.0f}" if t['pnl'] else "$0"
                t_rows.append({
                    "Symbol": t["symbol"],
                    "Entry": t["entry_date"][:10],
                    "Exit": t["exit_date"][:10],
                    "Entry $": f"${t['entry_price']:.2f}",
                    "Exit $": f"${t['exit_price']:.2f}",
                    "Return": f"{t['pnl_pct']:+.1%}",
                    "PnL": pnl_str,
                    "Days": t.get("hold_days", ""),
                    "Reason": t.get("exit_reason", ""),
                })
            st.dataframe(pd.DataFrame(t_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No paper trades completed yet. Run a few cycles to start building history.")

    with tab_pt4:
        st.markdown('<div class="section-header">Engine Attribution</div>', unsafe_allow_html=True)
        st.caption("Which engines actually drive profitable signals?")

        try:
            from portfolio.attribution import get_engine_attribution, get_signal_agreement_analysis

            attr = get_engine_attribution()
            if attr:
                attr_rows = []
                for eng, data in attr.items():
                    if data["total_signals"] == 0:
                        continue
                    attr_rows.append({
                        "Engine": eng.replace("_", " ").title(),
                        "Signals": data["total_signals"],
                        "Bull Win%": f"{data['bullish_win_rate']:.0%}" if data["bullish_count"] > 0 else "—",
                        "Bear Win%": f"{data['bearish_win_rate']:.0%}" if data["bearish_count"] > 0 else "—",
                        "Avg Ret (Bull)": f"{data['avg_return_when_bullish']:+.1%}" if data.get("avg_return_when_bullish") is not None else "—",
                        "Hi-Conf Acc": f"{data['high_conf_accuracy']:.0%}" if data.get("high_conf_accuracy") is not None else "—",
                        "Contribution": f"{data['contribution_score']:+.1f}",
                    })

                if attr_rows:
                    st.dataframe(pd.DataFrame(attr_rows), use_container_width=True, hide_index=True)

                    # Contribution chart
                    cont_df = pd.DataFrame([{
                        "Engine": eng.replace("_", " ").title(),
                        "Contribution": data["contribution_score"],
                    } for eng, data in attr.items() if data["total_signals"] > 0])

                    if not cont_df.empty:
                        cont_chart = alt.Chart(cont_df).mark_bar(
                            cornerRadiusTopLeft=4, cornerRadiusTopRight=4,
                        ).encode(
                            x=alt.X("Engine:N", sort="-y", axis=alt.Axis(labelAngle=0)),
                            y=alt.Y("Contribution:Q", title="Alpha Contribution"),
                            color=alt.condition(
                                alt.datum.Contribution >= 0,
                                alt.value("#4caf50"),
                                alt.value("#ef5350"),
                            ),
                            tooltip=["Engine", alt.Tooltip("Contribution:Q", format=".1f")],
                        ).properties(height=250)
                        st.altair_chart(cont_chart, use_container_width=True)

            # Agreement analysis
            agree = get_signal_agreement_analysis()
            if "high_agreement" in agree:
                st.markdown('<div class="section-header">Does Engine Agreement Matter?</div>',
                            unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    h = agree["high_agreement"]
                    st.markdown(card("High Agreement (70%+)",
                                     f"{h['win_rate']:.0%} win rate",
                                     f"{h['count']} signals, avg {h['avg_return']:+.1%}"),
                                unsafe_allow_html=True)
                with col2:
                    l = agree["low_agreement"]
                    st.markdown(card("Low Agreement (<70%)",
                                     f"{l['win_rate']:.0%} win rate",
                                     f"{l['count']} signals, avg {l['avg_return']:+.1%}"),
                                unsafe_allow_html=True)

                if agree.get("agreement_matters"):
                    st.success("Engine agreement IS predictive — high-agreement signals perform better")
                elif agree["high_agreement"]["count"] >= 5:
                    st.info("Engine agreement shows no significant edge — more data needed")

        except Exception as e:
            st.info(f"Attribution requires outcome data. Run analyses and wait for 5-day outcomes to accumulate.")


# ============================================================
# Page: Portfolio
# ============================================================
elif page == "Portfolio":
    st.markdown("## Portfolio")

    tab1, tab2, tab3 = st.tabs(["Overview", "Trade History", "Exit Signals"])

    with tab1:
        summary = get_portfolio_summary()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(card("Total Value", f"${summary['total_value']:,.0f}"),
                        unsafe_allow_html=True)
        with col2:
            st.markdown(card("Cash", f"${summary['cash']:,.0f}"),
                        unsafe_allow_html=True)
        with col3:
            st.markdown(card("Invested", f"${summary['position_value']:,.0f}"),
                        unsafe_allow_html=True)
        with col4:
            dd_color = "#ef5350" if summary['drawdown'] < -0.05 else "#9e9e9e"
            st.markdown(card("Drawdown", f"{summary['drawdown']:.1%}", color=dd_color),
                        unsafe_allow_html=True)

        if summary["positions"]:
            st.markdown('<div class="section-header">Open Positions</div>', unsafe_allow_html=True)
            pos_df = pd.DataFrame(summary["positions"])
            pos_df.columns = ["Symbol", "Qty", "Entry", "Current", "PnL ($)", "PnL (%)"]
            st.dataframe(pos_df, use_container_width=True, hide_index=True)
        else:
            st.info("No open positions")

    with tab2:
        stats = get_trade_stats()

        if stats.get("total_trades", 0) > 0:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(card("Trades", str(stats["total_trades"])), unsafe_allow_html=True)
            with col2:
                wr_color = "#4caf50" if stats['win_rate'] >= 0.5 else "#ef5350"
                st.markdown(card("Win Rate", f"{stats['win_rate']:.0%}", color=wr_color),
                            unsafe_allow_html=True)
            with col3:
                pnl_color = "#4caf50" if stats['total_pnl'] >= 0 else "#ef5350"
                st.markdown(card("Total PnL", f"${stats['total_pnl']:,.0f}", color=pnl_color),
                            unsafe_allow_html=True)
            with col4:
                st.markdown(card("Sharpe", f"{sharpe_ratio():.2f}"), unsafe_allow_html=True)

            spy_data = vs_spy()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(card("SPY Return", f"{spy_data.get('spy_return', 0):.1%}"),
                            unsafe_allow_html=True)
            with col2:
                st.markdown(card("Portfolio Return", f"{spy_data.get('portfolio_return', 0):.1%}"),
                            unsafe_allow_html=True)
            with col3:
                excess = spy_data.get('excess_return', 0)
                ex_color = "#4caf50" if excess >= 0 else "#ef5350"
                st.markdown(card("Excess Return", f"{excess:+.1%}", color=ex_color),
                            unsafe_allow_html=True)
        else:
            st.info("No trade history yet")

    with tab3:
        st.markdown('<div class="section-header">Active Exit Signals</div>', unsafe_allow_html=True)
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
# Page: Backtest
# ============================================================
elif page == "Backtest":
    st.markdown("## Backtest")
    st.caption("Walk-forward validation of the signal system")

    from config.watchlists import list_packages_by_region, PACKAGE_META, get_package_symbols as bt_get_pkg

    bt_pkg_options = {}
    for region, pkgs in list_packages_by_region().items():
        for key, name, count in pkgs:
            bt_pkg_options[f"{name} ({count}) [{region}]"] = key

    col1, col2, col3 = st.columns(3)
    with col1:
        months = st.slider("Period (months)", 3, 24, 12)
    with col2:
        src = st.selectbox("Symbols", ["Package", "Custom"])
    with col3:
        bt_mode = st.radio("Mode", ["Full", "Fast"], index=1,
                           help="Full = real 5-engine combiner. Fast = simplified scoring.")

    if src == "Custom":
        custom = st.text_input("Symbols (comma-separated)", value="NVDA,AAPL,MSFT,TSLA,AMD")
        symbols = [s.strip().upper() for s in custom.split(",") if s.strip()]
    else:
        bt_label = st.selectbox("Package", list(bt_pkg_options.keys()),
                                index=None, placeholder="Choose...", key="bt_pkg")
        symbols = bt_get_pkg([bt_pkg_options[bt_label]]) if bt_label else []

    run_btn = st.button("Run Backtest", type="primary", use_container_width=True, disabled=len(symbols) == 0)

    if run_btn and symbols:
        from portfolio.backtest import run_backtest

        fast = "Fast" in bt_mode
        with st.spinner(f"Running {'fast' if fast else 'full'} backtest on {len(symbols)} symbols..."):
            result = run_backtest(symbols=symbols, months=months, fast=fast)

        # Results
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            ret_color = "#4caf50" if result.total_return_pct >= 0 else "#ef5350"
            st.markdown(card("Return", f"{result.total_return_pct:+.1%}", color=ret_color),
                        unsafe_allow_html=True)
        with col2:
            st.markdown(card("SPY", f"{result.spy_return_pct:+.1%}"), unsafe_allow_html=True)
        with col3:
            ex = result.excess_return_pct
            ex_color = "#4caf50" if ex >= 0 else "#ef5350"
            st.markdown(card("Excess", f"{ex:+.1%}", "vs SPY", color=ex_color),
                        unsafe_allow_html=True)
        with col4:
            st.markdown(card("Sharpe", f"{result.sharpe_ratio:.2f}"), unsafe_allow_html=True)

        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.markdown(card("Trades", str(result.total_trades)), unsafe_allow_html=True)
        with col6:
            wr_color = "#4caf50" if result.win_rate >= 0.5 else "#ef5350"
            st.markdown(card("Win Rate", f"{result.win_rate:.0%}", color=wr_color),
                        unsafe_allow_html=True)
        with col7:
            st.markdown(card("Profit Factor", f"{result.profit_factor:.2f}"), unsafe_allow_html=True)
        with col8:
            st.markdown(card("Max Drawdown", f"{result.max_drawdown_pct:.1%}", color="#ef5350"),
                        unsafe_allow_html=True)

        # Costs
        if result.total_costs > 0:
            st.markdown('<div class="section-header">Trading Costs</div>', unsafe_allow_html=True)
            slip = sum(t.slippage_cost for t in result.trades)
            comm = sum(t.commission_cost for t in result.trades)
            col1, col2, col3 = st.columns(3)
            col1.metric("Total", f"${result.total_costs:,.2f}")
            col2.metric("Slippage", f"${slip:,.2f}")
            col3.metric("Commission", f"${comm:,.2f}")

        # Regime breakdown
        if result.regime_breakdown:
            st.markdown('<div class="section-header">By Regime</div>', unsafe_allow_html=True)
            regime_rows = []
            for reg, stats in sorted(result.regime_breakdown.items()):
                regime_rows.append({
                    "Regime": reg,
                    "Trades": stats["trades"],
                    "Win Rate": f"{stats['win_rate']:.0%}",
                    "Avg Return": f"{stats['avg_return']:+.1%}",
                })
            st.dataframe(pd.DataFrame(regime_rows), use_container_width=True, hide_index=True)

        # Equity curve
        if result.equity_curve:
            st.markdown('<div class="section-header">Equity Curve</div>', unsafe_allow_html=True)
            eq_df = pd.DataFrame({
                "Day": range(len(result.equity_curve)),
                "Value": result.equity_curve,
            })
            eq_chart = alt.Chart(eq_df).mark_area(
                line={"color": "#4caf50"},
                color=alt.Gradient(
                    gradient="linear",
                    stops=[
                        alt.GradientStop(color="rgba(76, 175, 80, 0.3)", offset=0),
                        alt.GradientStop(color="rgba(76, 175, 80, 0.02)", offset=1),
                    ],
                    x1=1, x2=1, y1=1, y2=0,
                ),
            ).encode(
                x=alt.X("Day:Q", title="Trading Days"),
                y=alt.Y("Value:Q", title="Portfolio Value ($)", scale=alt.Scale(zero=False)),
                tooltip=["Day", alt.Tooltip("Value:Q", format="$,.0f")],
            ).properties(height=300)
            st.altair_chart(eq_chart, use_container_width=True)

        # Trades table
        if result.trades:
            st.markdown(f'<div class="section-header">Trades ({len(result.trades)})</div>',
                        unsafe_allow_html=True)
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
                trade_rows.append(row)
            st.dataframe(pd.DataFrame(trade_rows), use_container_width=True, hide_index=True)


# ============================================================
# Page: Discover
# ============================================================
elif page == "Discover":
    st.markdown("## Opportunity Discovery")
    st.caption("Find trending tickers from Reddit and financial news")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-header">Reddit</div>', unsafe_allow_html=True)
        if st.button("Scan Reddit", type="primary"):
            with st.spinner("Scanning subreddits..."):
                from data.reddit import get_ticker_mentions
                mentions = get_ticker_mentions()

            if mentions:
                rows = []
                for ticker, data in list(mentions.items())[:20]:
                    rows.append({
                        "Ticker": ticker,
                        "Mentions": data["count"],
                        "Score": f"{data['avg_score']:.0f}",
                        "Subreddits": ", ".join(data["subreddits"][:3]),
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.warning("No ticker mentions found")

    with col2:
        st.markdown('<div class="section-header">News</div>', unsafe_allow_html=True)
        if st.button("Fetch News"):
            with st.spinner("Fetching feeds..."):
                from data.news import fetch_rss_news
                news = fetch_rss_news(max_per_source=5)

            if news:
                for item in news[:15]:
                    title = item.get("title", "")
                    source = item.get("source", "")
                    if title:
                        st.markdown(f"**{source}** — {title}")
            else:
                st.warning("Could not fetch news")


# ============================================================
# Page: Settings
# ============================================================
elif page == "Settings":
    st.markdown("## Settings")

    env_path = os.path.join(os.path.dirname(__file__), ".env")

    def _read_env():
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
        lines = []
        if os.path.exists(env_path):
            with open(env_path) as f:
                lines = f.readlines()

        updated = set()
        new_lines = []
        for line in lines:
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                key = s.partition("=")[0].strip()
                if key in updates:
                    new_lines.append(f"{key}={updates[key]}\n")
                    updated.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        for key, val in updates.items():
            if key not in updated:
                new_lines.append(f"{key}={val}\n")

        with open(env_path, "w") as f:
            f.writelines(new_lines)

    tab1, tab2, tab3, tab4 = st.tabs(["LLM", "Risk", "API Keys", "Alerts"])

    with tab1:
        st.markdown('<div class="section-header">LLM Configuration</div>', unsafe_allow_html=True)
        llm_modes = {"Off — $0 (algorithmic only)": "off",
                     "Haiku — ~$0.0003/run": "haiku",
                     "Sonnet — ~$0.01/run": "sonnet"}
        current = settings.llm_mode.value
        current_label = [k for k, v in llm_modes.items() if v == current][0]

        selected_label = st.selectbox("Mode", list(llm_modes.keys()),
                                      index=list(llm_modes.keys()).index(current_label))
        selected_mode = llm_modes[selected_label]

        api_key_val = settings.anthropic_api_key or ""
        if selected_mode != "off":
            api_key_val = st.text_input("Anthropic API Key", value=api_key_val, type="password")

        if st.button("Save LLM Settings"):
            updates = {"LLM_MODE": selected_mode}
            if selected_mode != "off" and api_key_val:
                updates["ANTHROPIC_API_KEY"] = api_key_val
            _write_env(updates)
            st.success("Saved. Restart app to apply.")

    with tab2:
        st.markdown('<div class="section-header">Risk Parameters</div>', unsafe_allow_html=True)
        p = settings.risk

        col1, col2 = st.columns(2)
        with col1:
            new_max_pos = st.slider("Max Position Size", 0.01, 0.50, p.max_position_pct, 0.01, format="%.0f%%")
            new_heat = st.slider("Max Portfolio Heat", 0.01, 0.30, p.max_portfolio_heat, 0.01, format="%.0f%%")
            new_dd = st.slider("Drawdown Breaker", -0.50, -0.01, p.drawdown_circuit_breaker, 0.01, format="%.0f%%")
            new_count = st.number_input("Max Positions", 1, 20, p.max_simultaneous_positions)
            new_sector = st.slider("Sector Cap", 0.10, 1.00, p.max_sector_concentration, 0.05, format="%.0f%%")
        with col2:
            new_cash = st.slider("Cash Reserve", 0.0, 0.50, p.cash_reserve_pct, 0.05, format="%.0f%%")
            new_daily = st.slider("Daily Risk", 0.01, 0.20, p.max_daily_risk, 0.01, format="%.0f%%")
            new_profit = st.slider("Profit Target", 0.01, 0.50, p.min_profit_target, 0.01, format="%.0f%%")
            new_atr_s = st.number_input("Stop ATR (Swing)", 0.5, 5.0, p.stop_loss_atr_swing, 0.1)
            new_atr_p = st.number_input("Stop ATR (Position)", 0.5, 5.0, p.stop_loss_atr_position, 0.1)

        new_corr = st.slider("Max Position Correlation", 0.3, 1.0, p.max_position_correlation, 0.05,
                             help="Reject new positions with avg correlation above this")

        if st.button("Save Risk Parameters"):
            _write_env({
                "MAX_POSITION_PCT": f"{new_max_pos:.2f}",
                "MAX_PORTFOLIO_HEAT": f"{new_heat:.2f}",
                "DRAWDOWN_CIRCUIT_BREAKER": f"{new_dd:.2f}",
                "MAX_SIMULTANEOUS_POSITIONS": str(int(new_count)),
                "MAX_SECTOR_CONCENTRATION": f"{new_sector:.2f}",
                "CASH_RESERVE_PCT": f"{new_cash:.2f}",
                "MAX_DAILY_RISK": f"{new_daily:.2f}",
                "MIN_PROFIT_TARGET": f"{new_profit:.2f}",
                "STOP_LOSS_ATR_SWING": f"{new_atr_s:.1f}",
                "STOP_LOSS_ATR_POSITION": f"{new_atr_p:.1f}",
                "MAX_POSITION_CORRELATION": f"{new_corr:.2f}",
            })
            st.success("Saved. Restart app to apply.")

    with tab3:
        st.markdown('<div class="section-header">API Keys</div>', unsafe_allow_html=True)
        st.caption("Saved to .env (gitignored)")

        new_anthropic = st.text_input("Anthropic", value=settings.anthropic_api_key, type="password")
        new_sec = st.text_input("SEC API", value=settings.sec_api_key, type="password")
        col1, col2 = st.columns(2)
        with col1:
            new_r_id = st.text_input("Reddit Client ID", value=settings.reddit_client_id, type="password")
        with col2:
            new_r_sec = st.text_input("Reddit Secret", value=settings.reddit_client_secret, type="password")
        new_av = st.text_input("Alpha Vantage", value=settings.alpha_vantage_api_key, type="password",
                               help="Free at alphavantage.co — enables data fallback")
        col1, col2 = st.columns(2)
        with col1:
            new_az_u = st.text_input("Avanza User", value=settings.avanza_username)
        with col2:
            new_az_p = st.text_input("Avanza Pass", value=settings.avanza_password, type="password")

        if st.button("Save API Keys"):
            keys = {}
            if new_anthropic: keys["ANTHROPIC_API_KEY"] = new_anthropic
            if new_sec: keys["SEC_API_KEY"] = new_sec
            if new_r_id: keys["REDDIT_CLIENT_ID"] = new_r_id
            if new_r_sec: keys["REDDIT_CLIENT_SECRET"] = new_r_sec
            if new_av: keys["ALPHA_VANTAGE_API_KEY"] = new_av
            if new_az_u: keys["AVANZA_USERNAME"] = new_az_u
            if new_az_p: keys["AVANZA_PASSWORD"] = new_az_p
            if keys:
                _write_env(keys)
                st.success(f"Saved {len(keys)} key(s). Restart to apply.")

    with tab4:
        st.markdown('<div class="section-header">Alert Configuration</div>', unsafe_allow_html=True)
        st.caption("Get notified when market regime changes")

        env = _read_env()

        alert_email = st.text_input("Alert Email", value=env.get("ALERT_EMAIL_TO", ""),
                                    placeholder="your@email.com")
        smtp_host = st.text_input("SMTP Host", value=env.get("ALERT_SMTP_HOST", ""),
                                  placeholder="smtp.gmail.com")
        col1, col2 = st.columns(2)
        with col1:
            smtp_port = st.text_input("SMTP Port", value=env.get("ALERT_SMTP_PORT", "587"))
        with col2:
            smtp_user = st.text_input("SMTP User", value=env.get("ALERT_SMTP_USER", ""), type="password")
        smtp_pass = st.text_input("SMTP Password", value=env.get("ALERT_SMTP_PASS", ""), type="password")

        st.divider()
        webhook = st.text_input("Webhook URL", value=env.get("ALERT_WEBHOOK_URL", ""),
                                placeholder="https://hooks.slack.com/... or Telegram bot URL",
                                help="Works with Slack, Discord, Telegram bots, or any webhook endpoint")

        if st.button("Save Alert Settings"):
            alert_updates = {}
            if alert_email: alert_updates["ALERT_EMAIL_TO"] = alert_email
            if smtp_host: alert_updates["ALERT_SMTP_HOST"] = smtp_host
            if smtp_port: alert_updates["ALERT_SMTP_PORT"] = smtp_port
            if smtp_user: alert_updates["ALERT_SMTP_USER"] = smtp_user
            if smtp_pass: alert_updates["ALERT_SMTP_PASS"] = smtp_pass
            if webhook: alert_updates["ALERT_WEBHOOK_URL"] = webhook
            if alert_updates:
                _write_env(alert_updates)
                st.success("Alert settings saved.")
