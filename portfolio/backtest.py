"""Walk-forward backtesting framework.

Two modes:
- Full mode (default): Uses real SignalCombiner with all 5 engines, earnings blackout,
  slippage, commission, and live-matching exit rules (trailing stop + staged profit taking + time exit).
- Fast mode (--fast): Uses simplified _quick_score() for rapid iteration. No slippage/commission.

Design:
- Download 2 years of daily data for symbols
- Walk-forward: test window = N months, weekly signal evaluation
- On each evaluation day: run signal combiner or quick score, simulate trades
- Exit rules match live system: trailing stop (HWM - ATR * mult), staged profit at 2R/3R/5R, time exit
- Track: Sharpe ratio, max drawdown, win rate, total return, vs SPY, regime breakdown, costs
"""

import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from data.indicators import (
    calculate_rsi, calculate_sma, calculate_ema, calculate_atr,
    calculate_macd, calculate_bollinger_bands, calculate_obv,
    calculate_stochastic, calculate_bb_pctb, calculate_roc,
    calculate_vwap, calculate_keltner_channels, calculate_adl,
    add_all_indicators,
)
from data.market_data import get_history

logger = logging.getLogger("stock_agent")

# Cost assumptions
SLIPPAGE_PCT = 0.001   # 0.1% slippage per side
COMMISSION_PER_TRADE = 1.0  # $1 per trade


@dataclass
class BacktestTrade:
    """A simulated trade during backtesting."""
    symbol: str
    entry_date: str
    entry_price: float
    exit_date: str = ""
    exit_price: float = 0.0
    quantity: int = 100
    pnl: float = 0.0
    pnl_pct: float = 0.0
    signal_action: str = ""
    confidence: float = 0.0
    regime: str = ""
    slippage_cost: float = 0.0
    commission_cost: float = 0.0


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    period_months: int
    symbols_tested: List[str]
    mode: str = "full"           # "full" or "fast"
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_return_pct: float = 0.0
    spy_return_pct: float = 0.0
    excess_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    total_costs: float = 0.0
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    monthly_returns: Dict[str, float] = field(default_factory=dict)
    regime_breakdown: Dict[str, dict] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        mode_label = "FULL (real combiner)" if self.mode == "full" else "FAST (quick score)"
        lines = [
            f"Backtest [{mode_label}]: {self.period_months}mo | {len(self.symbols_tested)} symbols | "
            f"{self.total_trades} trades",
            f"Return: {self.total_return_pct:+.1%} (SPY: {self.spy_return_pct:+.1%}, "
            f"Excess: {self.excess_return_pct:+.1%})",
            f"Sharpe: {self.sharpe_ratio:.2f} | Max DD: {self.max_drawdown_pct:.1%} | "
            f"Win Rate: {self.win_rate:.0%}",
            f"Profit Factor: {self.profit_factor:.2f} | "
            f"Avg Win: {self.avg_win_pct:+.1%} | Avg Loss: {self.avg_loss_pct:+.1%}",
        ]
        if self.total_costs > 0:
            lines.append(f"Total Costs: ${self.total_costs:,.2f} (slippage + commission)")
        if self.regime_breakdown:
            lines.append("Regime Breakdown:")
            for regime, stats in self.regime_breakdown.items():
                lines.append(f"  {regime}: {stats['trades']} trades, "
                           f"win rate {stats['win_rate']:.0%}, "
                           f"avg return {stats['avg_return']:+.1%}")
        return "\n".join(lines)


def run_backtest(symbols: List[str], months: int = 12,
                 initial_capital: float = 100000.0, fast: bool = False,
                 progress_callback=None) -> BacktestResult:
    """Run walk-forward backtest.

    Args:
        symbols: List of ticker symbols to test
        months: Total backtest period in months
        initial_capital: Starting capital
        fast: If True, use _quick_score instead of real SignalCombiner
        progress_callback: Optional callable(current, total, message) for progress updates
    """
    mode = "fast" if fast else "full"
    logger.info(f"Starting backtest [{mode}]: {len(symbols)} symbols, {months} months")

    result = BacktestResult(period_months=months, symbols_tested=symbols, mode=mode)

    # Fetch SPY for benchmark
    spy_df = get_history("SPY", period="2y")
    if spy_df.empty:
        logger.error("Could not fetch SPY data for backtest")
        return result

    # Fetch all symbol data upfront
    symbol_data = {}
    for i, sym in enumerate(symbols):
        if progress_callback:
            progress_callback(i, len(symbols), f"Fetching {sym}...")
        df = get_history(sym, period="2y")
        if not df.empty and len(df) >= 100:
            df = add_all_indicators(df)
            symbol_data[sym] = df

    if not symbol_data:
        logger.error("No valid symbol data for backtest")
        return result

    # Set up combiner for full mode
    combiner = None
    if not fast:
        from engines.signal_combiner import SignalCombiner
        combiner = SignalCombiner()

    # Walk-forward simulation
    capital = initial_capital
    peak_capital = initial_capital
    equity_curve = [capital]
    all_trades = []
    daily_returns = []

    # Get the date range
    all_dates = spy_df.index
    start_idx = max(0, len(all_dates) - months * 21)  # ~21 trading days per month
    test_dates = all_dates[start_idx:]

    open_positions = {}  # symbol -> {trade, hwm, entry_atr, remaining_qty, partial_exits}
    max_positions = 5
    position_size_pct = 0.10  # 10% per position

    total_eval_days = len(test_dates)

    for i, date in enumerate(test_dates):
        date_str = date.strftime("%Y-%m-%d")

        if progress_callback and i % 20 == 0:
            progress_callback(i, total_eval_days, f"Simulating {date_str}...")

        # Check exits for open positions
        for sym in list(open_positions.keys()):
            pos = open_positions[sym]
            trade = pos["trade"]
            if sym not in symbol_data:
                continue

            sym_df = symbol_data[sym]
            if date not in sym_df.index:
                continue

            current_price = float(sym_df.loc[date, "Close"])
            entry_price = trade.entry_price
            entry_atr = pos["entry_atr"]

            # Update high water mark
            pos["hwm"] = max(pos["hwm"], current_price)
            hwm = pos["hwm"]

            # Risk per share (for R-multiple)
            risk_per_share = entry_atr * 2.5
            if risk_per_share <= 0:
                risk_per_share = entry_price * 0.02

            profit_per_share = current_price - entry_price
            r_multiple = profit_per_share / risk_per_share if risk_per_share > 0 else 0

            # 1. Trailing stop (matches live: HWM - ATR * mult, tightens at 2R and 3R)
            if r_multiple >= 3.0:
                trail_mult = 1.5
            elif r_multiple >= 2.0:
                trail_mult = 2.0
            else:
                trail_mult = 2.5

            trailing_stop = hwm - (entry_atr * trail_mult)
            should_exit = current_price < trailing_stop
            exit_reason = "trailing_stop"

            # 2. Staged profit taking at 2R, 3R, 5R
            if not should_exit:
                partial_exits = pos.get("partial_exits", set())
                remaining = pos["remaining_qty"]

                if r_multiple >= 5.0 and "5R" not in partial_exits:
                    # Close all remaining
                    should_exit = True
                    exit_reason = "profit_5R"
                elif r_multiple >= 3.0 and "3R" not in partial_exits:
                    # Take 33% of remaining
                    exit_qty = max(1, int(remaining * 0.33))
                    _record_partial_exit(pos, trade, date_str, current_price, exit_qty, fast)
                    pos["partial_exits"].add("3R")
                    capital += (current_price * (1 - SLIPPAGE_PCT) - entry_price) * exit_qty - COMMISSION_PER_TRADE if not fast else (current_price - entry_price) * exit_qty
                elif r_multiple >= 2.0 and "2R" not in partial_exits:
                    exit_qty = max(1, int(remaining * 0.33))
                    _record_partial_exit(pos, trade, date_str, current_price, exit_qty, fast)
                    pos["partial_exits"].add("2R")
                    capital += (current_price * (1 - SLIPPAGE_PCT) - entry_price) * exit_qty - COMMISSION_PER_TRADE if not fast else (current_price - entry_price) * exit_qty

            # 3. Time stop: 20 trading days (~28 calendar) with < 2% gain
            if not should_exit:
                try:
                    entry_dt = datetime.fromisoformat(trade.entry_date)
                    days_held = (date.to_pydatetime().replace(tzinfo=None) - entry_dt).days
                    gain_pct = (current_price - entry_price) / entry_price if entry_price > 0 else 0
                    if days_held > 28 and gain_pct < 0.02:
                        should_exit = True
                        exit_reason = "time_exit"
                except (ValueError, TypeError):
                    pass

            if should_exit:
                remaining = pos["remaining_qty"]
                if remaining <= 0:
                    del open_positions[sym]
                    continue

                if fast:
                    exit_price = current_price
                    slippage = 0.0
                    commission = 0.0
                else:
                    exit_price = current_price * (1 - SLIPPAGE_PCT)
                    slippage = current_price * SLIPPAGE_PCT * remaining
                    commission = COMMISSION_PER_TRADE

                trade.exit_date = date_str
                trade.exit_price = exit_price
                trade.pnl = (exit_price - entry_price) * remaining - commission
                trade.pnl_pct = (exit_price - entry_price) / entry_price if entry_price > 0 else 0
                trade.slippage_cost = trade.slippage_cost + slippage
                trade.commission_cost = trade.commission_cost + commission
                capital += trade.pnl
                all_trades.append(trade)
                del open_positions[sym]

        # Generate signals (every 5 days to simulate weekly rebalance)
        if i % 5 != 0:
            daily_ret = 0
            if len(equity_curve) > 0:
                daily_ret = (capital - equity_curve[-1]) / equity_curve[-1] if equity_curve[-1] > 0 else 0
            daily_returns.append(daily_ret)
            equity_curve.append(capital)
            peak_capital = max(peak_capital, capital)
            continue

        # Score symbols on this date
        scored = []
        for sym, sym_df in symbol_data.items():
            if sym in open_positions:
                continue
            if date not in sym_df.index:
                continue

            try:
                idx = sym_df.index.get_loc(date)
                if idx < 50:
                    continue
                row = sym_df.iloc[idx]
                price = float(row["Close"])

                if fast:
                    score = _quick_score(sym_df, idx)
                    if score > 0.3:
                        scored.append((sym, score, price, "BUY", "UNKNOWN"))
                else:
                    # Full mode: use real SignalCombiner with historical data only.
                    # CRITICAL: Slice DataFrame up to current backtest date to prevent
                    # lookahead bias. Engines receive only data available at this point
                    # in time, never future prices.
                    try:
                        df_to_date = sym_df.iloc[:idx + 1]  # Include current row, nothing after
                        date_str = date.strftime("%Y-%m-%d")
                        sig = combiner.analyze(sym, df=df_to_date, backtest_date=date_str)
                        if sig.is_actionable and sig.action in ("BUY", "STRONG_BUY"):
                            # Check earnings blackout
                            from data.earnings import is_earnings_blackout
                            if not is_earnings_blackout(sym):
                                regime_str = sig.regime.regime.value if sig.regime else "UNKNOWN"
                                scored.append((sym, sig.combined_score, price, sig.action, regime_str))
                    except Exception as e:
                        logger.debug(f"Full backtest signal failed for {sym}: {e}")
                        continue
            except Exception:
                continue

        # Sort by score and take top entries
        scored.sort(key=lambda x: x[1], reverse=True)
        slots = max_positions - len(open_positions)

        for sym, score, price, action, regime_str in scored[:slots]:
            if price <= 0:
                continue

            if fast:
                entry_price = price
                entry_slippage = 0.0
                entry_commission = 0.0
            else:
                entry_price = price * (1 + SLIPPAGE_PCT)
                entry_slippage = price * SLIPPAGE_PCT
                entry_commission = COMMISSION_PER_TRADE

            pos_value = capital * position_size_pct
            qty = int(pos_value / entry_price)
            if qty <= 0:
                continue

            # Get ATR at entry
            sym_df = symbol_data[sym]
            entry_atr = 0.0
            if "ATR" in sym_df.columns and date in sym_df.index:
                atr_val = sym_df.loc[date, "ATR"]
                if not pd.isna(atr_val):
                    entry_atr = float(atr_val)
            if entry_atr <= 0:
                entry_atr = price * 0.02

            trade = BacktestTrade(
                symbol=sym,
                entry_date=date_str,
                entry_price=entry_price,
                quantity=qty,
                signal_action=action,
                confidence=score,
                regime=regime_str,
                slippage_cost=entry_slippage * qty,
                commission_cost=entry_commission,
            )

            capital -= entry_commission  # Deduct entry commission from capital

            open_positions[sym] = {
                "trade": trade,
                "hwm": entry_price,
                "entry_atr": entry_atr,
                "remaining_qty": qty,
                "partial_exits": set(),
            }

        # Track equity
        daily_ret = 0
        if len(equity_curve) > 0:
            daily_ret = (capital - equity_curve[-1]) / equity_curve[-1] if equity_curve[-1] > 0 else 0
        daily_returns.append(daily_ret)
        equity_curve.append(capital)
        peak_capital = max(peak_capital, capital)

    # Close any remaining positions at last price
    for sym, pos in open_positions.items():
        trade = pos["trade"]
        remaining = pos["remaining_qty"]
        if remaining <= 0:
            continue
        if sym in symbol_data:
            df = symbol_data[sym]
            if not df.empty:
                last_price = float(df["Close"].iloc[-1])
                if fast:
                    exit_price = last_price
                else:
                    exit_price = last_price * (1 - SLIPPAGE_PCT)
                    trade.slippage_cost += last_price * SLIPPAGE_PCT * remaining
                    trade.commission_cost += COMMISSION_PER_TRADE

                trade.exit_price = exit_price
                trade.exit_date = df.index[-1].strftime("%Y-%m-%d")
                trade.pnl = (exit_price - trade.entry_price) * remaining
                trade.pnl_pct = (exit_price - trade.entry_price) / trade.entry_price if trade.entry_price > 0 else 0
                capital += trade.pnl
                all_trades.append(trade)

    # Calculate metrics
    result.trades = all_trades
    result.equity_curve = equity_curve
    result.total_trades = len(all_trades)

    if all_trades:
        wins = [t for t in all_trades if t.pnl > 0]
        losses = [t for t in all_trades if t.pnl <= 0]
        result.winning_trades = len(wins)
        result.losing_trades = len(losses)
        result.win_rate = len(wins) / len(all_trades)
        result.avg_win_pct = float(np.mean([t.pnl_pct for t in wins])) if wins else 0
        result.avg_loss_pct = float(np.mean([t.pnl_pct for t in losses])) if losses else 0

        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Total costs
        result.total_costs = sum(t.slippage_cost + t.commission_cost for t in all_trades)

        # Regime breakdown
        regime_trades: Dict[str, List[BacktestTrade]] = {}
        for t in all_trades:
            r = t.regime or "UNKNOWN"
            regime_trades.setdefault(r, []).append(t)

        for regime, trades in regime_trades.items():
            r_wins = [t for t in trades if t.pnl > 0]
            result.regime_breakdown[regime] = {
                "trades": len(trades),
                "win_rate": len(r_wins) / len(trades) if trades else 0,
                "avg_return": float(np.mean([t.pnl_pct for t in trades])) if trades else 0,
            }

    result.total_return_pct = (capital - initial_capital) / initial_capital

    # SPY return over same period
    if not spy_df.empty and len(test_dates) > 0:
        spy_start = spy_df["Close"].loc[test_dates[0]] if test_dates[0] in spy_df.index else spy_df["Close"].iloc[start_idx]
        spy_end = spy_df["Close"].iloc[-1]
        result.spy_return_pct = (spy_end - spy_start) / spy_start
        result.excess_return_pct = result.total_return_pct - result.spy_return_pct

    # Sharpe ratio
    if daily_returns:
        daily_arr = np.array(daily_returns)
        mean_ret = np.mean(daily_arr)
        std_ret = np.std(daily_arr)
        if std_ret > 0:
            result.sharpe_ratio = round((mean_ret - 0.04 / 252) / std_ret * np.sqrt(252), 2)

    # Max drawdown
    if equity_curve:
        peak = equity_curve[0]
        max_dd = 0
        for val in equity_curve:
            peak = max(peak, val)
            dd = (val - peak) / peak if peak > 0 else 0
            max_dd = min(max_dd, dd)
        result.max_drawdown_pct = max_dd

    logger.info(f"Backtest [{mode}] complete: {result.total_trades} trades, return {result.total_return_pct:.1%}")
    return result


def _record_partial_exit(pos: dict, trade: BacktestTrade, date_str: str,
                         price: float, qty: int, fast: bool):
    """Record a partial exit (staged profit taking). Reduces remaining_qty."""
    pos["remaining_qty"] -= qty
    if not fast:
        trade.slippage_cost += price * SLIPPAGE_PCT * qty
        trade.commission_cost += COMMISSION_PER_TRADE


def _quick_score(df: pd.DataFrame, idx: int) -> float:
    """Quick scoring function for backtesting (simplified signal combiner).

    Used in --fast mode for rapid iteration without real engine calls.
    """
    try:
        row = df.iloc[idx]
        score = 0.0

        # Trend
        price = row["Close"]
        sma20 = row.get("SMA_20")
        sma50 = row.get("SMA_50")
        if sma20 is not None and sma50 is not None and not pd.isna(sma20) and not pd.isna(sma50):
            if price > sma20 > sma50:
                score += 0.25
            elif price < sma20 < sma50:
                score -= 0.15

        # RSI
        rsi = row.get("RSI")
        if rsi is not None and not pd.isna(rsi):
            if 40 < rsi < 70:
                score += 0.15
            elif rsi < 30:
                score += 0.2  # Mean reversion
            elif rsi > 80:
                score -= 0.1

        # MACD
        macd_hist = row.get("MACD_Histogram")
        if macd_hist is not None and not pd.isna(macd_hist):
            if macd_hist > 0:
                score += 0.1
            else:
                score -= 0.05

        # Volume
        vol_ratio = row.get("Volume_Ratio")
        if vol_ratio is not None and not pd.isna(vol_ratio):
            if vol_ratio > 1.5 and score > 0:
                score += 0.15

        # BB %B
        pctb = row.get("BB_PctB")
        if pctb is not None and not pd.isna(pctb):
            if 0.3 < pctb < 0.8:
                score += 0.05
            elif pctb < 0.1:
                score += 0.15  # Oversold bounce

        # Stochastic
        stoch_k = row.get("Stoch_K")
        stoch_d = row.get("Stoch_D")
        if stoch_k is not None and stoch_d is not None:
            if not pd.isna(stoch_k) and not pd.isna(stoch_d):
                if stoch_k < 20 and stoch_k > stoch_d:
                    score += 0.15

        return max(0.0, min(1.0, score))
    except Exception:
        return 0.0


def format_backtest_report(result: BacktestResult) -> str:
    """Format a backtest result as a readable text report."""
    mode_label = "FULL (real combiner)" if result.mode == "full" else "FAST (quick score)"
    lines = [
        "=" * 60,
        f"  BACKTEST RESULTS [{mode_label}]",
        "=" * 60,
        f"  Period:          {result.period_months} months",
        f"  Symbols:         {len(result.symbols_tested)}",
        f"  Total Trades:    {result.total_trades}",
        "",
        "  --- Performance ---",
        f"  Total Return:    {result.total_return_pct:+.1%}",
        f"  SPY Return:      {result.spy_return_pct:+.1%}",
        f"  Excess Return:   {result.excess_return_pct:+.1%}",
        f"  Sharpe Ratio:    {result.sharpe_ratio:.2f}",
        f"  Max Drawdown:    {result.max_drawdown_pct:.1%}",
        "",
        "  --- Trade Stats ---",
        f"  Win Rate:        {result.win_rate:.0%}",
        f"  Profit Factor:   {result.profit_factor:.2f}",
        f"  Avg Win:         {result.avg_win_pct:+.1%}",
        f"  Avg Loss:        {result.avg_loss_pct:+.1%}",
        f"  Winners:         {result.winning_trades}",
        f"  Losers:          {result.losing_trades}",
        "",
    ]

    # Costs (full mode only)
    if result.total_costs > 0:
        lines.append("  --- Costs ---")
        lines.append(f"  Total Costs:     ${result.total_costs:,.2f}")
        total_slippage = sum(t.slippage_cost for t in result.trades)
        total_commission = sum(t.commission_cost for t in result.trades)
        lines.append(f"  Slippage:        ${total_slippage:,.2f}")
        lines.append(f"  Commission:      ${total_commission:,.2f}")
        lines.append("")

    # Regime breakdown
    if result.regime_breakdown:
        lines.append("  --- Regime Breakdown ---")
        for regime, stats in sorted(result.regime_breakdown.items()):
            lines.append(f"    {regime:20s}  {stats['trades']:3d} trades  "
                        f"WR {stats['win_rate']:.0%}  Avg {stats['avg_return']:+.1%}")
        lines.append("")

    # Top trades
    if result.trades:
        best = sorted(result.trades, key=lambda t: t.pnl_pct, reverse=True)
        lines.append("  --- Top 5 Trades ---")
        for t in best[:5]:
            lines.append(f"    {t.symbol:6s} {t.entry_date} -> {t.exit_date}  {t.pnl_pct:+.1%}  ${t.pnl:+.0f}")

        lines.append("")
        lines.append("  --- Bottom 5 Trades ---")
        for t in best[-5:]:
            lines.append(f"    {t.symbol:6s} {t.entry_date} -> {t.exit_date}  {t.pnl_pct:+.1%}  ${t.pnl:+.0f}")

    lines.append("=" * 60)
    return "\n".join(lines)
