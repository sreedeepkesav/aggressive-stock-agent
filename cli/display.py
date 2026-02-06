"""Formatting and display helpers for CLI output."""

from typing import Dict, List


def print_header(title: str) -> None:
    width = 70
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def print_section(title: str) -> None:
    print(f"\n--- {title} ---")


def print_combined_signal(sig) -> None:
    """Pretty-print a CombinedSignal."""
    icon = {"STRONG_BUY": "+", "BUY": "+", "HOLD": "~", "SELL": "-", "STRONG_SELL": "-"}.get(sig.action, "?")
    actionable = " [ACTIONABLE]" if sig.is_actionable else ""

    print(f"\n  [{icon}] {sig.symbol}: {sig.action} (score={sig.combined_score:+.3f}, "
          f"confidence={sig.confidence:.0%}, agreement={sig.agreement_pct:.0%}){actionable}")

    for eng_name, result in sig.engine_results.items():
        if result.signal == "NO_DATA":
            print(f"      {eng_name:15s}: NO DATA")
        else:
            print(f"      {eng_name:15s}: {result.signal:12s} conf={result.confidence:.2f}  {', '.join(result.reasons[:2])}")

    if sig.reasons:
        print(f"    Top reasons:")
        for r in sig.reasons[:5]:
            print(f"      - {r}")


def print_portfolio_summary(summary: Dict) -> None:
    print_header("Portfolio Summary")
    print(f"  Cash:           ${summary['cash']:>12,.2f}")
    print(f"  Positions:      ${summary['position_value']:>12,.2f}")
    print(f"  Total Value:    ${summary['total_value']:>12,.2f}")
    print(f"  Unrealized PnL: ${summary['unrealized_pnl']:>12,.2f}")
    print(f"  Peak Value:     ${summary['peak_value']:>12,.2f}")
    print(f"  Drawdown:        {summary['drawdown']:>11.1%}")
    print(f"  Open Positions:  {summary['position_count']:>11d}")

    if summary["positions"]:
        print_section("Open Positions")
        print(f"  {'Symbol':<8} {'Qty':>6} {'Entry':>10} {'Current':>10} {'PnL':>10} {'PnL%':>8}")
        print(f"  {'-'*52}")
        for p in summary["positions"]:
            print(f"  {p['symbol']:<8} {p['qty']:>6} {p['entry']:>10.2f} {p['current']:>10.2f} "
                  f"{p['pnl']:>10.2f} {p['pnl_pct']:>8}")


def print_trade_stats(stats: Dict) -> None:
    print_header("Trade Statistics")
    if stats.get("message"):
        print(f"  {stats['message']}")
        return
    print(f"  Total trades:   {stats['total_trades']}")
    print(f"  Wins/Losses:    {stats['wins']}/{stats['losses']}")
    print(f"  Win rate:       {stats['win_rate']:.0%}")
    print(f"  Total PnL:     ${stats['total_pnl']:>10,.2f}")
    print(f"  Avg win:       ${stats['avg_win']:>10,.2f}")
    print(f"  Avg loss:      ${stats['avg_loss']:>10,.2f}")
    print(f"  Profit factor:  {stats['profit_factor']:.2f}")
    print(f"  Largest win:   ${stats['largest_win']:>10,.2f}")
    print(f"  Largest loss:  ${stats['largest_loss']:>10,.2f}")


def print_risk_check(check: Dict) -> None:
    if check["allowed"]:
        print("  Risk check: PASSED")
    else:
        print("  Risk check: BLOCKED")
        for r in check["reasons"]:
            print(f"    - {r}")


def print_help() -> None:
    print_header("Stock Agent - Professional Analysis Tool")
    print("""
  Usage: python stock_agent.py <mode> [options]

  Modes:
    web [PORT]          Launch web dashboard (default port 8501)
    ticker <SYMBOL>     Analyze a single stock (regime-aware, 5 engines + timeframe filter)
    scan [N]            Scan watchlist, show top N opportunities (default 10)
    portfolio show      Show current portfolio state + exit signals
    portfolio stats     Show trade statistics + engine accuracy
    backtest [MONTHS]   Run walk-forward backtest (default 12 months)
    discovery           Discover new opportunities from news + Reddit
    universe update     Refresh stock universes (S&P 500, momentum, value)
    help                Show this help message

  Environment Variables (Risk Parameters - all configurable):
    MAX_POSITION_PCT          Max position as fraction of portfolio (default: 0.10)
    MAX_PORTFOLIO_HEAT        Max total portfolio risk (default: 0.08)
    DRAWDOWN_CIRCUIT_BREAKER  Stop trading at this drawdown (default: -0.10)
    MAX_SIMULTANEOUS_POSITIONS Max open positions (default: 5)
    MAX_SECTOR_CONCENTRATION  Max allocation to one sector (default: 0.40)
    CASH_RESERVE_PCT          Min cash reserve (default: 0.20)
    MAX_DAILY_RISK            Daily risk tolerance (default: 0.05)
    MIN_PROFIT_TARGET         Min profit target (default: 0.08)
    STOP_LOSS_ATR_SWING       ATR multiplier for swing stops (default: 2.0)
    STOP_LOSS_ATR_POSITION    ATR multiplier for position stops (default: 2.5)
    LLM_MODE                  off (default) | haiku | sonnet
    CACHE_TTL_SECONDS         Data cache TTL (default: 300)
    LOG_LEVEL                 Logging level (default: INFO)

  Signal Flow:
    1. Market regime detected (SPY/VIX/breadth -> weight adjustment)
    2. Each of 5 engines analyzes the stock independently
    3. Signals combined with regime-adjusted + adaptive weights
    4. Weekly timeframe filter confirms or demotes signal
    5. Analysis saved for learning (outcomes checked after 5+ days)

  Examples:
    python stock_agent.py web               # Launch web dashboard
    python stock_agent.py web 9000          # Launch on custom port
    python stock_agent.py ticker NVDA       # Analyze a stock (regime + 5 engines)
    python stock_agent.py scan 5            # Scan watchlist, show top 5
    python stock_agent.py backtest 12       # 12-month walk-forward backtest
    python stock_agent.py portfolio show    # Portfolio state + exit signals
    python stock_agent.py portfolio stats   # Trade stats + engine accuracy
    MAX_POSITION_PCT=0.15 python stock_agent.py ticker AAPL
""")
