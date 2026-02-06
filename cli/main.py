"""CLI entry point - replaces the 950+ lines of runner functions in stock_agent.py."""

import argparse
import logging
import sys
import os
import warnings

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from config.settings import Settings
from config.logging_config import setup_logging
from cli.display import (
    print_header, print_section, print_combined_signal,
    print_portfolio_summary, print_trade_stats, print_risk_check, print_help,
)
from engines.signal_combiner import SignalCombiner
from engines.timeframe import apply_timeframe_filter
from portfolio import state
from portfolio.tracker import get_portfolio_summary, get_trade_stats, sharpe_ratio, vs_spy

logger = logging.getLogger("stock_agent")


def cmd_ticker(symbol: str, settings: Settings) -> None:
    """Analyze a single ticker through all engines with regime detection and timeframe filter."""
    print_header(f"Analysis: {symbol}")

    # Try to get adaptive weights
    from portfolio.memory import get_adaptive_weights, save_analysis, check_outcomes

    # Check outcomes from previous analyses
    filled = check_outcomes()
    if filled > 0:
        print(f"  Updated {filled} outcome records from previous analyses")

    adaptive_weights = get_adaptive_weights()
    if adaptive_weights:
        print(f"  Using adaptive weights (learned from {sum(1 for _ in adaptive_weights)} engines)")

    combiner = SignalCombiner()
    signal = combiner.analyze(symbol, adaptive_weights=adaptive_weights)

    # Apply multi-timeframe filter
    signal = apply_timeframe_filter(signal)

    print_combined_signal(signal)

    # Show regime info
    if signal.regime:
        print_section("Market Regime")
        print(f"    {signal.regime.summary}")

    # Save analysis to memory
    price = 0
    momentum_result = signal.engine_results.get("momentum")
    if momentum_result and momentum_result.metadata.get("entry"):
        price = momentum_result.metadata["entry"]
    elif signal.engine_results.get("technical"):
        price = signal.engine_results["technical"].metadata.get("price", 0)

    regime_str = signal.regime.regime.value if signal.regime else "UNKNOWN"
    save_analysis(
        symbol=symbol,
        combined_score=signal.combined_score,
        action=signal.action,
        confidence=signal.confidence,
        agreement_pct=signal.agreement_pct,
        close_price=price,
        regime=regime_str,
        engine_results=signal.engine_results,
    )

    # Risk check
    if signal.is_actionable and signal.action in ("STRONG_BUY", "BUY"):
        from portfolio.risk import RiskManager
        rm = RiskManager(settings.risk)
        entry = momentum_result.metadata.get("entry", 0) if momentum_result else 0
        if entry > 0:
            stop = rm.calculate_stop_loss(symbol, entry)
            qty = rm.calculate_position_size(entry, stop)
            proposed_value = qty * entry
            check = rm.check_can_open_position(symbol, proposed_value)
            print_section("Risk Assessment")
            print_risk_check(check)
            print(f"    Suggested: {qty} shares @ ${entry:.2f}, stop ${stop:.2f}")

        # Check exit signals for existing positions
        exit_signals = rm.check_exit_signals()
        if exit_signals:
            print_section("Exit Signals")
            for es in exit_signals:
                print(f"    [{es.urgency.upper()}] {es.symbol}: {es.reason}")

    print()


def cmd_scan(count: int, settings: Settings) -> None:
    """Scan watchlist and show top opportunities with regime-aware analysis."""
    print_header(f"Market Scan - Top {count}")

    from portfolio.memory import get_adaptive_weights, check_outcomes

    check_outcomes()
    adaptive_weights = get_adaptive_weights()

    combiner = SignalCombiner()

    # Show regime
    regime = combiner.regime_info
    print(f"\n  Market Regime: {regime.regime.value} (VIX {regime.vix_level:.1f}, "
          f"breadth {regime.breadth_pct:.0%}, SPY {regime.spy_trend})")
    if regime.block_buys:
        print(f"  WARNING: VIX > 35 - new BUY signals blocked")
    if adaptive_weights:
        print(f"  Using adaptive weights")
    print()

    signals = combiner.analyze_multiple(settings.watchlist, adaptive_weights=adaptive_weights)

    # Apply timeframe filter to each
    signals = [apply_timeframe_filter(s) for s in signals]
    signals.sort(key=lambda s: s.combined_score, reverse=True)

    actionable = [s for s in signals if s.is_actionable]
    print(f"  Scanned {len(settings.watchlist)} symbols, {len(actionable)} actionable signals\n")

    for sig in signals[:count]:
        print_combined_signal(sig)

    print()


def cmd_portfolio_show() -> None:
    """Show portfolio state with exit signals."""
    state.init_db()
    summary = get_portfolio_summary()
    print_portfolio_summary(summary)

    # Check exit signals
    from portfolio.risk import RiskManager
    rm = RiskManager()
    exit_signals = rm.check_exit_signals()
    if exit_signals:
        print_section("Exit Signals")
        for es in exit_signals:
            print(f"    [{es.urgency.upper()}] {es.symbol}: {es.exit_type} - {es.reason}")
            if es.exit_pct < 1.0:
                print(f"      Exit {es.exit_pct:.0%} of position")

    print()


def cmd_portfolio_stats() -> None:
    """Show trade statistics."""
    state.init_db()
    stats = get_trade_stats()
    print_trade_stats(stats)

    sr = sharpe_ratio()
    spy = vs_spy()
    print_section("Performance Metrics")
    print(f"  Sharpe Ratio:    {sr:.2f}")
    print(f"  SPY Return:      {spy.get('spy_return', 0):.1%}")
    print(f"  Portfolio Return: {spy.get('portfolio_return', 0):.1%}")
    print(f"  Excess Return:   {spy.get('excess_return', 0):.1%}")

    # Show engine performance
    from portfolio.memory import get_engine_performance_summary
    perf = get_engine_performance_summary()
    if perf:
        print_section("Engine Accuracy (last 90 days)")
        for p in perf:
            print(f"    {p['engine_name']:15s}: {p['accuracy']:.0%} "
                  f"({p['correct_signals']}/{p['total_signals']} correct)")
    print()


def cmd_backtest(months: int, settings: Settings) -> None:
    """Run backtest over specified period."""
    print_header(f"Backtest - {months} months")

    from portfolio.backtest import run_backtest, format_backtest_report

    print(f"  Running backtest on {len(settings.watchlist)} symbols for {months} months...")
    print(f"  This may take a moment...\n")

    result = run_backtest(symbols=settings.watchlist, months=months)
    print(format_backtest_report(result))


def cmd_discovery(settings: Settings) -> None:
    """Discover new opportunities from news + social."""
    print_header("Opportunity Discovery")

    from data.news import get_comprehensive_news
    from data.reddit import get_ticker_mentions

    print("  Fetching news...")
    news = get_comprehensive_news(symbols=settings.watchlist[:5])
    print(f"  Found {len(news)} news articles")

    print("  Scanning Reddit...")
    mentions = get_ticker_mentions()
    if mentions:
        print_section("Reddit Trending Tickers")
        for ticker, data in list(mentions.items())[:10]:
            print(f"    {ticker:6s}  mentions={data['count']:3d}  avg_score={data['avg_score']:6.0f}  "
                  f"subs={', '.join(data['subreddits'][:3])}")

    print()


def cmd_universe_update() -> None:
    """Refresh stock universes."""
    print_header("Universe Update")
    from data.universe import update_all_universes
    universes = update_all_universes()
    for name, symbols in universes.items():
        print(f"  {name}: {len(symbols)} symbols")
    print()


def main(argv=None) -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="stock_agent",
        description="Professional Stock Analysis Agent",
        add_help=False,
    )
    parser.add_argument("mode", nargs="?", default="help",
                        choices=["ticker", "scan", "portfolio", "discovery", "universe", "backtest", "help"])
    parser.add_argument("args", nargs="*", default=[])

    args = parser.parse_args(argv)
    settings = Settings.load()
    setup_logging()
    state.init_db()

    mode = args.mode
    extra = args.args

    if mode == "help" or (not mode):
        print_help()

    elif mode == "ticker":
        if not extra:
            print("Error: ticker mode requires a symbol. Example: stock_agent.py ticker NVDA")
            sys.exit(1)
        cmd_ticker(extra[0].upper(), settings)

    elif mode == "scan":
        count = int(extra[0]) if extra else 10
        cmd_scan(count, settings)

    elif mode == "portfolio":
        sub = extra[0] if extra else "show"
        if sub == "show":
            cmd_portfolio_show()
        elif sub == "stats":
            cmd_portfolio_stats()
        else:
            print(f"Unknown portfolio sub-command: {sub}. Use 'show' or 'stats'.")

    elif mode == "discovery":
        cmd_discovery(settings)

    elif mode == "universe":
        sub = extra[0] if extra else "update"
        if sub == "update":
            cmd_universe_update()
        else:
            print(f"Unknown universe sub-command: {sub}. Use 'update'.")

    elif mode == "backtest":
        months = int(extra[0]) if extra else 12
        cmd_backtest(months, settings)

    else:
        print_help()


if __name__ == "__main__":
    main()
