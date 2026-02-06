"""Walk-forward backtesting framework.

Design:
- Download 2 years of daily data for symbols
- Walk-forward: train window = 6 months, test window = 1 month, slide forward
- On each test day: run signal combiner logic, simulate trades
- Track: Sharpe ratio, max drawdown, win rate, total return, vs SPY
"""

import logging
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


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    period_months: int
    symbols_tested: List[str]
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
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    monthly_returns: Dict[str, float] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        return (
            f"Backtest: {self.period_months}mo | {len(self.symbols_tested)} symbols | "
            f"{self.total_trades} trades\n"
            f"Return: {self.total_return_pct:+.1%} (SPY: {self.spy_return_pct:+.1%}, "
            f"Excess: {self.excess_return_pct:+.1%})\n"
            f"Sharpe: {self.sharpe_ratio:.2f} | Max DD: {self.max_drawdown_pct:.1%} | "
            f"Win Rate: {self.win_rate:.0%}\n"
            f"Profit Factor: {self.profit_factor:.2f} | "
            f"Avg Win: {self.avg_win_pct:+.1%} | Avg Loss: {self.avg_loss_pct:+.1%}"
        )


def run_backtest(symbols: List[str], months: int = 12,
                 initial_capital: float = 100000.0) -> BacktestResult:
    """Run walk-forward backtest.

    Args:
        symbols: List of ticker symbols to test
        months: Total backtest period in months
        initial_capital: Starting capital
    """
    logger.info(f"Starting backtest: {len(symbols)} symbols, {months} months")

    result = BacktestResult(period_months=months, symbols_tested=symbols)

    # Fetch SPY for benchmark
    spy_df = get_history("SPY", period="2y")
    if spy_df.empty:
        logger.error("Could not fetch SPY data for backtest")
        return result

    # Fetch all symbol data upfront
    symbol_data = {}
    for sym in symbols:
        df = get_history(sym, period="2y")
        if not df.empty and len(df) >= 100:
            df = add_all_indicators(df)
            symbol_data[sym] = df

    if not symbol_data:
        logger.error("No valid symbol data for backtest")
        return result

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

    open_positions = {}  # symbol -> BacktestTrade
    max_positions = 5
    position_size_pct = 0.10  # 10% per position

    for i, date in enumerate(test_dates):
        date_str = date.strftime("%Y-%m-%d")

        # Check exits for open positions
        for sym in list(open_positions.keys()):
            trade = open_positions[sym]
            if sym not in symbol_data:
                continue

            sym_df = symbol_data[sym]
            if date not in sym_df.index:
                continue

            current_price = sym_df.loc[date, "Close"]
            entry_price = trade.entry_price

            # Simple exit rules for backtest:
            # 1. Stop loss: 2 ATR below entry
            atr_at_entry = sym_df.loc[date, "ATR"] if "ATR" in sym_df.columns and not pd.isna(sym_df.loc[date, "ATR"]) else current_price * 0.02
            stop_loss = entry_price - atr_at_entry * 2.0

            # 2. Profit target: 4 ATR above entry
            target = entry_price + atr_at_entry * 4.0

            # 3. Time stop: 20 bars
            bars_held = 0
            try:
                entry_dt = datetime.fromisoformat(trade.entry_date)
                bars_held = (date.to_pydatetime().replace(tzinfo=None) - entry_dt).days
            except (ValueError, TypeError):
                pass

            should_exit = False
            if current_price <= stop_loss:
                should_exit = True
            elif current_price >= target:
                should_exit = True
            elif bars_held > 28 and (current_price - entry_price) / entry_price < 0.02:
                should_exit = True

            if should_exit:
                trade.exit_date = date_str
                trade.exit_price = current_price
                trade.pnl = (current_price - entry_price) * trade.quantity
                trade.pnl_pct = (current_price - entry_price) / entry_price
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

            # Simple scoring using available indicators at this date
            try:
                idx = sym_df.index.get_loc(date)
                if idx < 50:
                    continue

                row = sym_df.iloc[idx]
                score = _quick_score(sym_df, idx)
                if score > 0.3:
                    scored.append((sym, score, row["Close"]))
            except Exception:
                continue

        # Sort by score and take top entries
        scored.sort(key=lambda x: x[1], reverse=True)
        slots = max_positions - len(open_positions)

        for sym, score, price in scored[:slots]:
            if price <= 0:
                continue
            pos_value = capital * position_size_pct
            qty = int(pos_value / price)
            if qty <= 0:
                continue

            trade = BacktestTrade(
                symbol=sym,
                entry_date=date_str,
                entry_price=price,
                quantity=qty,
                signal_action="BUY",
                confidence=score,
            )
            open_positions[sym] = trade

        # Track equity
        daily_ret = 0
        if len(equity_curve) > 0:
            daily_ret = (capital - equity_curve[-1]) / equity_curve[-1] if equity_curve[-1] > 0 else 0
        daily_returns.append(daily_ret)
        equity_curve.append(capital)
        peak_capital = max(peak_capital, capital)

    # Close any remaining positions at last price
    for sym, trade in open_positions.items():
        if sym in symbol_data:
            df = symbol_data[sym]
            if not df.empty:
                trade.exit_price = df["Close"].iloc[-1]
                trade.exit_date = df.index[-1].strftime("%Y-%m-%d")
                trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity
                trade.pnl_pct = (trade.exit_price - trade.entry_price) / trade.entry_price
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
        result.avg_win_pct = np.mean([t.pnl_pct for t in wins]) if wins else 0
        result.avg_loss_pct = np.mean([t.pnl_pct for t in losses]) if losses else 0

        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

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

    logger.info(f"Backtest complete: {result.total_trades} trades, return {result.total_return_pct:.1%}")
    return result


def _quick_score(df: pd.DataFrame, idx: int) -> float:
    """Quick scoring function for backtesting (simplified signal combiner)."""
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
    lines = [
        "=" * 60,
        "  BACKTEST RESULTS",
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

    # Top trades
    if result.trades:
        best = sorted(result.trades, key=lambda t: t.pnl_pct, reverse=True)
        lines.append("  --- Top 5 Trades ---")
        for t in best[:5]:
            lines.append(f"    {t.symbol:6s} {t.entry_date} → {t.exit_date}  {t.pnl_pct:+.1%}  ${t.pnl:+.0f}")

        lines.append("")
        lines.append("  --- Bottom 5 Trades ---")
        for t in best[-5:]:
            lines.append(f"    {t.symbol:6s} {t.entry_date} → {t.exit_date}  {t.pnl_pct:+.1%}  ${t.pnl:+.0f}")

    lines.append("=" * 60)
    return "\n".join(lines)
