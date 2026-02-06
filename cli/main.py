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
from portfolio import state
from portfolio.tracker import get_portfolio_summary, get_trade_stats, sharpe_ratio, vs_spy

logger = logging.getLogger("stock_agent")


def cmd_ticker(symbol: str, settings: Settings) -> None:
    """Analyze a single ticker through all engines."""
    print_header(f"Analysis: {symbol}")

    combiner = SignalCombiner()
    signal = combiner.analyze(symbol)
    print_combined_signal(signal)

    # Risk check
    if signal.is_actionable and signal.action in ("STRONG_BUY", "BUY"):
        from portfolio.risk import RiskManager
        rm = RiskManager(settings.risk)
        # Estimate position value
        price = signal.engine_results.get("momentum", signal.engine_results.get("technical"))
        entry = price.metadata.get("entry", 0) if price else 0
        if entry > 0:
            stop = rm.calculate_stop_loss(symbol, entry)
            qty = rm.calculate_position_size(entry, stop)
            proposed_value = qty * entry
            check = rm.check_can_open_position(symbol, proposed_value)
            print_section("Risk Assessment")
            print_risk_check(check)
            print(f"    Suggested: {qty} shares @ ${entry:.2f}, stop ${stop:.2f}")

    print()


def cmd_scan(count: int, settings: Settings) -> None:
    """Scan watchlist and show top opportunities."""
    print_header(f"Market Scan - Top {count}")

    combiner = SignalCombiner()
    signals = combiner.analyze_multiple(settings.watchlist)

    actionable = [s for s in signals if s.is_actionable]
    print(f"\n  Scanned {len(settings.watchlist)} symbols, {len(actionable)} actionable signals\n")

    for sig in signals[:count]:
        print_combined_signal(sig)

    print()


def cmd_portfolio_show() -> None:
    """Show portfolio state."""
    state.init_db()
    summary = get_portfolio_summary()
    print_portfolio_summary(summary)
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
    print()


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
                        choices=["ticker", "scan", "portfolio", "discovery", "universe", "help"])
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

    else:
        print_help()


if __name__ == "__main__":
    main()
