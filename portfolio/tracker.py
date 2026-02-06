"""Performance tracker: Sharpe ratio, win rate, max drawdown, vs SPY."""

import logging
from datetime import datetime
from typing import Dict, List

import numpy as np

from data.market_data import get_history
from portfolio import state

logger = logging.getLogger("stock_agent")


def get_trade_stats() -> Dict:
    """Calculate trade performance statistics."""
    trades = state.get_trades(limit=500)
    if not trades:
        return {"total_trades": 0, "message": "No trade history"}

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    pnls = [t.pnl for t in trades]

    total_pnl = sum(pnls)
    avg_win = np.mean([t.pnl for t in wins]) if wins else 0
    avg_loss = np.mean([t.pnl for t in losses]) if losses else 0

    return {
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(trades) if trades else 0,
        "total_pnl": round(total_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": abs(sum(t.pnl for t in wins) / sum(t.pnl for t in losses)) if losses and sum(t.pnl for t in losses) != 0 else float("inf"),
        "largest_win": round(max(pnls), 2) if pnls else 0,
        "largest_loss": round(min(pnls), 2) if pnls else 0,
    }


def get_portfolio_summary() -> Dict:
    """Get current portfolio state summary."""
    positions = state.get_positions()
    cash = state.get_cash_balance()
    peak = state.get_peak_value()

    position_value = sum(p.market_value for p in positions)
    total_value = cash + position_value
    unrealized_pnl = sum(p.unrealized_pnl for p in positions)
    drawdown = (total_value - peak) / peak if peak > 0 else 0

    return {
        "cash": round(cash, 2),
        "position_value": round(position_value, 2),
        "total_value": round(total_value, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "peak_value": round(peak, 2),
        "drawdown": round(drawdown, 4),
        "position_count": len(positions),
        "positions": [
            {
                "symbol": p.symbol,
                "qty": p.quantity,
                "entry": p.entry_price,
                "current": p.current_price,
                "pnl": round(p.unrealized_pnl, 2),
                "pnl_pct": f"{p.unrealized_pnl_pct:.1%}",
            }
            for p in positions
        ],
    }


def sharpe_ratio(period_days: int = 90) -> float:
    """Calculate Sharpe ratio from trade PnLs (annualized, risk-free = 4%)."""
    trades = state.get_trades(limit=500)
    if len(trades) < 5:
        return 0.0

    daily_returns = [t.pnl_pct for t in trades]
    mean_ret = np.mean(daily_returns)
    std_ret = np.std(daily_returns)

    if std_ret == 0:
        return 0.0

    # Annualize (assume ~252 trading days)
    risk_free_daily = 0.04 / 252
    return round((mean_ret - risk_free_daily) / std_ret * np.sqrt(252), 2)


def vs_spy(period: str = "3mo") -> Dict:
    """Compare portfolio return vs SPY over a period."""
    spy = get_history("SPY", period=period)
    if spy.empty:
        return {"spy_return": 0.0, "message": "Could not fetch SPY data"}

    spy_return = spy["Close"].iloc[-1] / spy["Close"].iloc[0] - 1

    trades = state.get_trades(limit=500)
    total_pnl = sum(t.pnl for t in trades)
    starting_capital = state.get_peak_value()  # Approximation
    portfolio_return = total_pnl / starting_capital if starting_capital > 0 else 0

    return {
        "spy_return": round(spy_return, 4),
        "portfolio_return": round(portfolio_return, 4),
        "excess_return": round(portfolio_return - spy_return, 4),
    }
