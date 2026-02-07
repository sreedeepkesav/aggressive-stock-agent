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
        for line in signal.regime.summary.split("\n"):
            print(f"    {line.strip()}")

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


def _prompt_package_selection() -> str:
    """Interactive prompt to select a watchlist package."""
    from config.watchlists import list_packages_by_region, WATCHLIST_PACKAGES

    print("\n  Select a package to scan:\n")
    print(f"  {'#':<4} {'Package Key':<32} {'Name':<28} {'Symbols':>7}")
    print(f"  {'-'*75}")

    options = []
    idx = 1
    for region, pkgs in list_packages_by_region().items():
        print(f"\n  {region}:")
        for key, name, count in pkgs:
            print(f"  {idx:<4} {key:<32} {name:<28} {count:>5}")
            options.append(key)
            idx += 1

    print(f"\n  Enter package number (1-{len(options)}), package key, or 'q' to quit:")
    try:
        choice = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if choice.lower() in ('q', 'quit', ''):
        return None

    # Try as number
    try:
        num = int(choice)
        if 1 <= num <= len(options):
            return options[num - 1]
        print(f"  Invalid number. Must be 1-{len(options)}.")
        return None
    except ValueError:
        pass

    # Try as package key
    if choice in WATCHLIST_PACKAGES:
        return choice
    print(f"  Unknown package: {choice}. Run 'packages' to see all options.")
    return None


def cmd_scan(count: int, settings: Settings, package: str = None) -> None:
    """Scan watchlist and show top opportunities with regime-aware analysis."""
    from config.watchlists import get_package_symbols, PACKAGE_META

    # Always require explicit package selection
    if not package:
        package = _prompt_package_selection()
        if not package:
            print("\n  Scan cancelled.")
            return

    symbols = get_package_symbols([package])
    if not symbols:
        print(f"\n  No symbols found for package '{package}'.")
        return
    pkg_name = PACKAGE_META.get(package, {}).get("name", package)
    print_header(f"Market Scan - {pkg_name} (Top {count})")

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
    print(f"  Package: {package} ({len(symbols)} symbols)")
    print()

    signals = combiner.analyze_multiple(symbols, adaptive_weights=adaptive_weights)

    # Apply timeframe filter to each
    signals = [apply_timeframe_filter(s) for s in signals]
    signals.sort(key=lambda s: s.combined_score, reverse=True)

    actionable = [s for s in signals if s.is_actionable]
    print(f"  Scanned {len(symbols)} symbols, {len(actionable)} actionable signals\n")

    for sig in signals[:count]:
        print_combined_signal(sig)

    print()


def cmd_packages() -> None:
    """List all available watchlist packages."""
    from config.watchlists import list_packages_by_region, get_total_symbol_count, WATCHLIST_PACKAGES
    from config.settings import Settings

    settings = Settings.load()
    print_header("Watchlist Packages")
    print(f"\n  Total: {get_total_symbol_count()} unique symbols across {len(WATCHLIST_PACKAGES)} packages")
    print(f"  Active: {len(settings.active_packages)} packages, {len(settings.watchlist)} symbols")
    print(f"  Active packages: {', '.join(settings.active_packages)}")

    for region, pkgs in list_packages_by_region().items():
        total = sum(c for _, _, c in pkgs)
        print(f"\n  {region} ({total} symbols)")
        print(f"  {'Package Key':<30s} {'Name':<30s} {'Symbols':>8s}")
        print(f"  {'-'*70}")
        for key, name, count in pkgs:
            active = " *" if key in settings.active_packages else ""
            print(f"  {key:<30s} {name:<30s} {count:>6d}{active}")

    print(f"\n  * = active package")
    print(f"\n  Usage:")
    print(f"    python stock_agent.py scan 10 --package sector_semiconductors")
    print(f"    python stock_agent.py scan 5 --package japan")
    print(f"    ACTIVE_PACKAGES=us_sp500,uk_ftse python stock_agent.py scan 10")
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


def cmd_backtest(months: int, settings: Settings, package: str = None, fast: bool = False) -> None:
    """Run backtest over specified period."""
    from config.watchlists import get_package_symbols, PACKAGE_META
    from portfolio.backtest import run_backtest, format_backtest_report

    if not package:
        print_header("Backtest - Select Package")
        package = _prompt_package_selection()
        if not package:
            print("\n  Backtest cancelled.")
            return

    symbols = get_package_symbols([package])
    if not symbols:
        print(f"\n  No symbols found for package '{package}'.")
        return
    pkg_name = PACKAGE_META.get(package, {}).get("name", package)
    mode_label = "FAST" if fast else "FULL"
    print_header(f"Backtest [{mode_label}] - {pkg_name} - {months} months")

    if not fast:
        est_calls = len(symbols) * (months * 4)  # ~4 weekly evaluations per month
        est_minutes = max(1, est_calls // 60)
        print(f"  Mode: FULL (real 5-engine combiner + slippage + commission)")
        print(f"  Estimated: ~{est_calls} signal evaluations (~{est_minutes} min)")
    else:
        print(f"  Mode: FAST (simplified indicator scoring, no costs)")

    print(f"  Running backtest on {len(symbols)} symbols ({pkg_name}) for {months} months...")
    print(f"  This may take a moment...\n")

    def _progress(current, total, msg):
        pct = current / total * 100 if total > 0 else 0
        print(f"\r  [{pct:5.1f}%] {msg}", end="", flush=True)

    result = run_backtest(symbols=symbols, months=months, fast=fast, progress_callback=_progress)
    print("\r" + " " * 60 + "\r", end="")  # Clear progress line
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
    """Refresh stock universes (S&P 500 list only - momentum/value use active watchlist)."""
    print_header("Universe Update")
    from data.universe import update_all_universes
    settings = Settings.load()
    print(f"  Using active watchlist ({len(settings.watchlist)} symbols) for momentum/value screens...")
    print(f"  Fetching S&P 500 list from Wikipedia...\n")
    universes = update_all_universes(active_symbols=settings.watchlist)
    for name, symbols in universes.items():
        print(f"  {name}: {len(symbols)} symbols")
    print()


def cmd_settings() -> None:
    """Interactive settings prompt for quick configuration changes."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

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

    def _write_env(updates):
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

    current = _read_env()
    settings = Settings.load()
    print_header("Settings")

    print(f"\n  Current LLM Mode: {settings.llm_mode.value}")
    print(f"  Current Max Position: {settings.risk.max_position_pct:.0%}")
    print(f"  Current Max Positions: {settings.risk.max_simultaneous_positions}")
    print()

    print("  What would you like to change?")
    print("    1) LLM Mode (off/haiku/sonnet)")
    print("    2) API Keys")
    print("    3) Risk Parameters")
    print("    4) Show all current settings")
    print("    5) Exit")

    choice = input("\n  Enter choice [1-5]: ").strip()

    if choice == "1":
        print(f"\n  Current LLM Mode: {settings.llm_mode.value}")
        print("  Options: off ($0), haiku (~$0.0003/run), sonnet (~$0.01/run)")
        mode = input("  New LLM Mode [off/haiku/sonnet]: ").strip().lower()
        if mode in ("off", "haiku", "sonnet"):
            updates = {"LLM_MODE": mode}
            if mode != "off":
                key = current.get("ANTHROPIC_API_KEY", "")
                if not key:
                    key = input("  Anthropic API Key: ").strip()
                if key:
                    updates["ANTHROPIC_API_KEY"] = key
            _write_env(updates)
            print(f"\n  Saved LLM_MODE={mode} to .env")
        else:
            print("  Invalid mode. No changes made.")

    elif choice == "2":
        print("\n  Enter new value or press Enter to keep current:")
        print("  (Keys are saved to .env only, never committed)\n")
        _mask = lambda s: s[:8] + "..." if len(s) > 8 else ("(not set)" if not s else s)
        api_fields = [
            ("ANTHROPIC_API_KEY", "Anthropic API Key", _mask(settings.anthropic_api_key)),
            ("SEC_API_KEY", "SEC API Key", _mask(settings.sec_api_key)),
            ("REDDIT_CLIENT_ID", "Reddit Client ID", _mask(settings.reddit_client_id)),
            ("REDDIT_CLIENT_SECRET", "Reddit Client Secret", _mask(settings.reddit_client_secret)),
            ("ALPHA_VANTAGE_API_KEY", "Alpha Vantage Key", _mask(settings.alpha_vantage_api_key)),
            ("AVANZA_USERNAME", "Avanza Username", _mask(settings.avanza_username)),
            ("AVANZA_PASSWORD", "Avanza Password", _mask(settings.avanza_password)),
        ]
        updates = {}
        for env_key, label, masked in api_fields:
            val = input(f"  {label} [{masked}]: ").strip()
            if val:
                updates[env_key] = val
        if updates:
            _write_env(updates)
            print(f"\n  Saved {len(updates)} API key(s) to .env")
        else:
            print("\n  No changes made.")

    elif choice == "3":
        print("\n  Enter new value or press Enter to keep current:\n")
        risk_fields = [
            ("MAX_POSITION_PCT", "Max Position Size", f"{settings.risk.max_position_pct}"),
            ("MAX_PORTFOLIO_HEAT", "Max Portfolio Heat", f"{settings.risk.max_portfolio_heat}"),
            ("DRAWDOWN_CIRCUIT_BREAKER", "Drawdown Breaker", f"{settings.risk.drawdown_circuit_breaker}"),
            ("MAX_SIMULTANEOUS_POSITIONS", "Max Positions", f"{settings.risk.max_simultaneous_positions}"),
            ("MAX_SECTOR_CONCENTRATION", "Max Sector Conc.", f"{settings.risk.max_sector_concentration}"),
            ("CASH_RESERVE_PCT", "Cash Reserve", f"{settings.risk.cash_reserve_pct}"),
            ("STOP_LOSS_ATR_SWING", "Stop ATR Swing", f"{settings.risk.stop_loss_atr_swing}"),
            ("STOP_LOSS_ATR_POSITION", "Stop ATR Position", f"{settings.risk.stop_loss_atr_position}"),
        ]
        updates = {}
        for env_key, label, default in risk_fields:
            val = input(f"  {label} [{default}]: ").strip()
            if val:
                updates[env_key] = val
        if updates:
            _write_env(updates)
            print(f"\n  Saved {len(updates)} parameter(s) to .env")
        else:
            print("\n  No changes made.")

    elif choice == "4":
        print(f"\n  LLM Mode:              {settings.llm_mode.value}")
        print(f"  Anthropic Key:         {'Yes' if settings.anthropic_api_key else 'No'}")
        print(f"  SEC Key:               {'Yes' if settings.sec_api_key else 'No'}")
        print(f"  Reddit Keys:           {'Yes' if settings.reddit_client_id else 'No'}")
        print(f"  Alpha Vantage Key:     {'Yes' if settings.alpha_vantage_api_key else 'No'}")
        print(f"  Avanza:                {'Yes' if settings.avanza_username else 'No'}")
        print(f"  Max Position:          {settings.risk.max_position_pct:.0%}")
        print(f"  Portfolio Heat:        {settings.risk.max_portfolio_heat:.0%}")
        print(f"  Drawdown Breaker:      {settings.risk.drawdown_circuit_breaker:.0%}")
        print(f"  Max Positions:         {settings.risk.max_simultaneous_positions}")
        print(f"  Sector Concentration:  {settings.risk.max_sector_concentration:.0%}")
        print(f"  Cash Reserve:          {settings.risk.cash_reserve_pct:.0%}")
        print(f"  Daily Risk:            {settings.risk.max_daily_risk:.0%}")
        print(f"  Profit Target:         {settings.risk.min_profit_target:.0%}")
        print(f"  Stop ATR Swing:        {settings.risk.stop_loss_atr_swing}")
        print(f"  Stop ATR Position:     {settings.risk.stop_loss_atr_position}")
        print(f"  Cache TTL:             {settings.cache_ttl_seconds}s")
        print(f"  Watchlist:             {', '.join(settings.watchlist[:10])}...")

    print()


def main(argv=None) -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="stock_agent",
        description="Professional Stock Analysis Agent",
        add_help=False,
    )
    parser.add_argument("mode", nargs="?", default="help",
                        choices=["ticker", "scan", "portfolio", "discovery", "universe", "backtest", "settings", "packages", "help"])
    parser.add_argument("args", nargs="*", default=[])
    parser.add_argument("--package", "-p", default=None, help="Scan a specific watchlist package")
    parser.add_argument("--fast", action="store_true", default=False, help="Fast backtest mode (simplified scoring, no costs)")

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
        cmd_scan(count, settings, package=args.package)

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
        cmd_backtest(months, settings, package=args.package, fast=args.fast)

    elif mode == "settings":
        cmd_settings()

    elif mode == "packages":
        cmd_packages()

    else:
        print_help()


if __name__ == "__main__":
    main()
