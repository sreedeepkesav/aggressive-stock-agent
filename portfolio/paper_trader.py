"""Paper trading engine: simulates real trades without real money.

Runs the full signal pipeline, applies risk checks, and tracks virtual positions
with real market data. Designed to prove the system before risking capital.

Usage:
    from portfolio.paper_trader import PaperTrader

    trader = PaperTrader(starting_capital=100000)
    trader.run_daily_cycle(symbols)  # Run once per day
    trader.get_summary()             # Performance snapshot

CLI:
    python -m portfolio.paper_trader --symbols NVDA AAPL MSFT
    python -m portfolio.paper_trader --package mega_cap_tech
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

import numpy as np

from config.settings import Settings, RiskParams
from data.market_data import get_history, get_info
from engines.signal_combiner import SignalCombiner
from engines.timeframe import apply_timeframe_filter
from portfolio import state
from portfolio.memory import save_analysis, check_outcomes, get_adaptive_weights
from portfolio.models import Position, Trade
from portfolio.state import _get_db

logger = logging.getLogger("stock_agent")


# ──────────────────────────────────────────────
# Paper trade database tables
# ──────────────────────────────────────────────

def _ensure_paper_tables(db_path: str = None) -> None:
    """Create paper trading tables if they don't exist."""
    conn = _get_db(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS paper_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            entry_price REAL NOT NULL,
            entry_date TEXT NOT NULL,
            stop_loss REAL NOT NULL,
            target_price REAL NOT NULL,
            sector TEXT DEFAULT '',
            current_price REAL DEFAULT 0,
            signal_score REAL DEFAULT 0,
            signal_action TEXT DEFAULT '',
            signal_confidence REAL DEFAULT 0,
            regime_at_entry TEXT DEFAULT 'UNKNOWN'
        );

        CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL NOT NULL,
            entry_date TEXT NOT NULL,
            exit_date TEXT NOT NULL,
            pnl REAL NOT NULL,
            pnl_pct REAL NOT NULL,
            exit_reason TEXT DEFAULT '',
            signal_score REAL DEFAULT 0,
            regime_at_entry TEXT DEFAULT '',
            regime_at_exit TEXT DEFAULT '',
            hold_days INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS paper_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS paper_daily_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT NOT NULL,
            portfolio_value REAL NOT NULL,
            cash REAL NOT NULL,
            position_count INTEGER NOT NULL,
            regime TEXT DEFAULT 'UNKNOWN',
            actions_taken TEXT DEFAULT '',
            symbols_analyzed INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# Paper trade state helpers
# ──────────────────────────────────────────────

def _paper_get(key: str, default: str = "0", db_path: str = None) -> str:
    conn = _get_db(db_path)
    row = conn.execute("SELECT value FROM paper_meta WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def _paper_set(key: str, value: str, db_path: str = None) -> None:
    conn = _get_db(db_path)
    conn.execute("INSERT OR REPLACE INTO paper_meta (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def paper_get_cash(db_path: str = None) -> float:
    return float(_paper_get("cash", "100000", db_path))


def paper_get_peak(db_path: str = None) -> float:
    return float(_paper_get("peak_value", "100000", db_path))


def paper_get_positions(db_path: str = None) -> List[Dict]:
    _ensure_paper_tables(db_path)
    conn = _get_db(db_path)
    rows = conn.execute("SELECT * FROM paper_positions").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def paper_get_trades(limit: int = 100, db_path: str = None) -> List[Dict]:
    _ensure_paper_tables(db_path)
    conn = _get_db(db_path)
    rows = conn.execute(
        "SELECT * FROM paper_trades ORDER BY exit_date DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def paper_get_daily_log(limit: int = 60, db_path: str = None) -> List[Dict]:
    _ensure_paper_tables(db_path)
    conn = _get_db(db_path)
    rows = conn.execute(
        "SELECT * FROM paper_daily_log ORDER BY log_date DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────────
# Kelly Criterion Position Sizing
# ──────────────────────────────────────────────

def kelly_fraction(win_rate: float, avg_win: float, avg_loss: float,
                   fraction: float = 0.5) -> float:
    """Compute fractional Kelly criterion for optimal position sizing.

    Kelly % = W - (1-W)/R
    where W = win rate, R = avg_win / avg_loss (payoff ratio)

    Args:
        win_rate: Historical win rate (0-1)
        avg_win: Average winning trade return (positive)
        avg_loss: Average losing trade return (positive, absolute value)
        fraction: Kelly fraction (0.5 = half-Kelly, safer)

    Returns:
        Optimal fraction of capital to risk (0 to fraction cap)
    """
    if avg_loss <= 0 or win_rate <= 0:
        return 0.0

    payoff_ratio = avg_win / avg_loss
    kelly = win_rate - (1 - win_rate) / payoff_ratio

    # Apply fractional Kelly (half-Kelly is standard for real trading)
    kelly *= fraction

    # Clamp to reasonable range
    return max(0.0, min(0.25, kelly))  # Never risk more than 25%


def kelly_position_size(entry_price: float, stop_loss: float,
                        portfolio_value: float, win_rate: float,
                        avg_win_pct: float, avg_loss_pct: float) -> int:
    """Calculate position size using Kelly criterion with ATR stop.

    Falls back to standard 1% risk sizing if Kelly data is insufficient.
    """
    if entry_price <= 0 or stop_loss >= entry_price or portfolio_value <= 0:
        return 0

    # Need enough history for Kelly
    if win_rate <= 0 or avg_win_pct <= 0 or avg_loss_pct <= 0:
        # Fallback: standard 1% risk
        risk_per_share = entry_price - stop_loss
        risk_budget = portfolio_value * 0.01
        return max(0, int(risk_budget / risk_per_share))

    kf = kelly_fraction(win_rate, avg_win_pct, avg_loss_pct)

    if kf <= 0:
        return 0

    # Kelly says risk kf% of portfolio
    risk_amount = portfolio_value * kf
    risk_per_share = entry_price - stop_loss

    kelly_qty = int(risk_amount / risk_per_share)

    # Also cap by max position size (10% of portfolio)
    max_value = portfolio_value * 0.10
    max_qty = int(max_value / entry_price)

    return max(0, min(kelly_qty, max_qty))


# ──────────────────────────────────────────────
# Paper Trader Engine
# ──────────────────────────────────────────────

class PaperTrader:
    """Simulates trading with real market data and virtual capital."""

    def __init__(self, starting_capital: float = 100000.0, db_path: str = None):
        self.db_path = db_path
        self.settings = Settings.load()

        _ensure_paper_tables(db_path)

        # Initialize capital if not set
        existing_cash = _paper_get("cash", "", db_path)
        if not existing_cash:
            _paper_set("cash", str(starting_capital), db_path)
            _paper_set("peak_value", str(starting_capital), db_path)
            _paper_set("start_date", datetime.now().isoformat(), db_path)

        self.combiner = SignalCombiner()

    def run_daily_cycle(self, symbols: List[str]) -> Dict:
        """Run one daily paper trading cycle:

        1. Update prices on existing positions
        2. Check exit signals on existing positions
        3. Analyze symbols for new entries
        4. Execute paper trades (entries + exits)
        5. Log daily snapshot

        Returns summary dict.
        """
        logger.info(f"Paper trading cycle: {len(symbols)} symbols")
        actions = []

        # Step 1: Update current prices
        positions = paper_get_positions(self.db_path)
        for pos in positions:
            try:
                df = get_history(pos["symbol"], period="5d")
                if not df.empty:
                    current = float(df["Close"].iloc[-1])
                    conn = _get_db(self.db_path)
                    conn.execute(
                        "UPDATE paper_positions SET current_price=? WHERE id=?",
                        (current, pos["id"])
                    )
                    conn.commit()
                    conn.close()
                    pos["current_price"] = current
            except Exception:
                pass

        # Step 2: Check exits
        exits = self._check_exits(positions)
        for exit_info in exits:
            self._execute_exit(exit_info)
            actions.append(f"SELL {exit_info['symbol']} ({exit_info['reason']})")

        # Step 3: Analyze for entries
        check_outcomes()
        adaptive_weights = get_adaptive_weights()
        entries = []

        for sym in symbols:
            try:
                sig = self.combiner.analyze(sym, adaptive_weights=adaptive_weights)
                sig = apply_timeframe_filter(sig)

                # Save to learning system
                price = 0
                mom = sig.engine_results.get("momentum")
                if mom:
                    price = mom.metadata.get("entry", 0)
                regime_str = sig.regime.regime.value if sig.regime else "UNKNOWN"

                save_analysis(
                    symbol=sym, combined_score=sig.combined_score, action=sig.action,
                    confidence=sig.confidence, agreement_pct=sig.agreement_pct,
                    close_price=price, regime=regime_str, engine_results=sig.engine_results,
                )

                if sig.is_actionable and sig.action in ("BUY", "STRONG_BUY"):
                    # Check earnings blackout
                    from data.earnings import is_earnings_blackout
                    if not is_earnings_blackout(sym):
                        entries.append({
                            "symbol": sym,
                            "signal": sig,
                            "price": price,
                            "regime": regime_str,
                        })

            except Exception as e:
                logger.debug(f"Paper analysis failed for {sym}: {e}")

        # Step 4: Execute entries (best signals first)
        entries.sort(key=lambda e: e["signal"].combined_score, reverse=True)
        for entry in entries:
            result = self._try_entry(entry)
            if result:
                actions.append(f"BUY {entry['symbol']} x{result['qty']} @ ${result['price']:.2f}")

        # Step 5: Log daily snapshot
        self._log_daily(len(symbols), actions)

        # Update peak
        total = self._portfolio_value()
        peak = paper_get_peak(self.db_path)
        if total > peak:
            _paper_set("peak_value", str(total), self.db_path)

        return {
            "date": datetime.now().isoformat(),
            "portfolio_value": total,
            "cash": paper_get_cash(self.db_path),
            "positions": len(paper_get_positions(self.db_path)),
            "actions": actions,
            "symbols_analyzed": len(symbols),
        }

    def _check_exits(self, positions: List[Dict]) -> List[Dict]:
        """Check positions for exit conditions."""
        exits = []
        for pos in positions:
            sym = pos["symbol"]
            entry = pos["entry_price"]
            current = pos.get("current_price", 0)
            stop = pos["stop_loss"]
            target = pos["target_price"]

            if current <= 0:
                continue

            # Stop loss hit
            if current <= stop:
                exits.append({
                    "id": pos["id"], "symbol": sym, "price": current,
                    "qty": pos["quantity"], "entry_price": entry,
                    "reason": f"Stop loss hit ({current:.2f} <= {stop:.2f})",
                    "entry_date": pos["entry_date"],
                    "regime_at_entry": pos.get("regime_at_entry", ""),
                })
                continue

            # Target hit
            if target > 0 and current >= target:
                exits.append({
                    "id": pos["id"], "symbol": sym, "price": current,
                    "qty": pos["quantity"], "entry_price": entry,
                    "reason": f"Target reached ({current:.2f} >= {target:.2f})",
                    "entry_date": pos["entry_date"],
                    "regime_at_entry": pos.get("regime_at_entry", ""),
                })
                continue

            # Time-based exit: 20 trading days max hold
            try:
                entry_dt = datetime.fromisoformat(pos["entry_date"])
                hold_days = (datetime.now() - entry_dt).days
                if hold_days > 30:  # ~20 trading days
                    exits.append({
                        "id": pos["id"], "symbol": sym, "price": current,
                        "qty": pos["quantity"], "entry_price": entry,
                        "reason": f"Time exit ({hold_days} days)",
                        "entry_date": pos["entry_date"],
                        "regime_at_entry": pos.get("regime_at_entry", ""),
                    })
            except Exception:
                pass

        return exits

    def _execute_exit(self, exit_info: Dict) -> None:
        """Execute a paper trade exit."""
        conn = _get_db(self.db_path)

        pnl = (exit_info["price"] - exit_info["entry_price"]) * exit_info["qty"]
        pnl_pct = (exit_info["price"] - exit_info["entry_price"]) / exit_info["entry_price"]

        hold_days = 0
        try:
            hold_days = (datetime.now() - datetime.fromisoformat(exit_info["entry_date"])).days
        except Exception:
            pass

        # Get current regime
        regime_now = "UNKNOWN"
        try:
            regime_now = self.combiner.regime_info.regime.value
        except Exception:
            pass

        # Record trade
        conn.execute(
            """INSERT INTO paper_trades
               (symbol, side, quantity, entry_price, exit_price, entry_date, exit_date,
                pnl, pnl_pct, exit_reason, regime_at_entry, regime_at_exit, hold_days)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (exit_info["symbol"], "SELL", exit_info["qty"],
             exit_info["entry_price"], exit_info["price"],
             exit_info["entry_date"], datetime.now().isoformat(),
             pnl, pnl_pct, exit_info["reason"],
             exit_info.get("regime_at_entry", ""),
             regime_now, hold_days),
        )

        # Remove position
        conn.execute("DELETE FROM paper_positions WHERE id=?", (exit_info["id"],))

        # Credit cash
        cash = float(conn.execute(
            "SELECT value FROM paper_meta WHERE key='cash'"
        ).fetchone()["value"])
        cash += exit_info["price"] * exit_info["qty"]
        conn.execute(
            "INSERT OR REPLACE INTO paper_meta (key, value) VALUES ('cash', ?)",
            (str(cash),)
        )

        conn.commit()
        conn.close()

        logger.info(
            f"Paper EXIT: {exit_info['symbol']} x{exit_info['qty']} @ "
            f"${exit_info['price']:.2f} | PnL: ${pnl:+.2f} ({pnl_pct:+.1%}) | "
            f"{exit_info['reason']}"
        )

    def _try_entry(self, entry: Dict) -> Optional[Dict]:
        """Try to execute a paper trade entry. Returns None if blocked by risk."""
        sym = entry["symbol"]
        sig = entry["signal"]
        price = entry["price"]
        regime = entry["regime"]

        if price <= 0:
            return None

        # Check if already holding
        positions = paper_get_positions(self.db_path)
        if any(p["symbol"] == sym for p in positions):
            return None

        cash = paper_get_cash(self.db_path)
        total_value = self._portfolio_value()

        # Max positions check
        if len(positions) >= self.settings.risk.max_simultaneous_positions:
            return None

        # Calculate stop and size
        from data.indicators import calculate_atr
        df = get_history(sym, period="3mo")
        if df.empty or len(df) < 20:
            return None

        atr = calculate_atr(df).iloc[-1]
        stop = round(price - atr * self.settings.risk.stop_loss_atr_swing, 2)
        target = round(price + atr * self.settings.risk.stop_loss_atr_swing * 2, 2)  # 2:1 reward/risk

        # Kelly sizing (use paper trade history)
        trades = paper_get_trades(100, self.db_path)
        if len(trades) >= 10:
            wins = [t for t in trades if t["pnl"] > 0]
            losses = [t for t in trades if t["pnl"] <= 0]
            win_rate = len(wins) / len(trades) if trades else 0
            avg_win = np.mean([abs(t["pnl_pct"]) for t in wins]) if wins else 0
            avg_loss = np.mean([abs(t["pnl_pct"]) for t in losses]) if losses else 0
            qty = kelly_position_size(price, stop, total_value, win_rate, avg_win, avg_loss)
        else:
            # Standard 1% risk sizing
            risk_per_share = price - stop
            risk_budget = total_value * 0.01
            qty = max(0, int(risk_budget / risk_per_share)) if risk_per_share > 0 else 0

        if qty <= 0:
            return None

        # Cash check
        cost = qty * price
        min_cash = total_value * self.settings.risk.cash_reserve_pct
        if cash - cost < min_cash:
            # Reduce quantity to fit
            available = cash - min_cash
            if available <= 0:
                return None
            qty = int(available / price)
            if qty <= 0:
                return None
            cost = qty * price

        # Execute
        conn = _get_db(self.db_path)

        conn.execute(
            """INSERT INTO paper_positions
               (symbol, quantity, entry_price, entry_date, stop_loss, target_price,
                sector, current_price, signal_score, signal_action, signal_confidence,
                regime_at_entry)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (sym, qty, price, datetime.now().isoformat(), stop, target,
             "", price, sig.combined_score, sig.action, sig.confidence, regime),
        )

        # Debit cash
        new_cash = cash - cost
        conn.execute(
            "INSERT OR REPLACE INTO paper_meta (key, value) VALUES ('cash', ?)",
            (str(new_cash),)
        )

        conn.commit()
        conn.close()

        logger.info(
            f"Paper ENTRY: {sym} x{qty} @ ${price:.2f} | "
            f"Stop: ${stop:.2f} | Target: ${target:.2f} | "
            f"Signal: {sig.action} ({sig.combined_score:+.3f}, {sig.confidence:.0%})"
        )

        return {"symbol": sym, "qty": qty, "price": price, "stop": stop, "target": target}

    def _portfolio_value(self) -> float:
        """Total paper portfolio value."""
        cash = paper_get_cash(self.db_path)
        positions = paper_get_positions(self.db_path)
        pos_value = sum(
            p.get("current_price", p["entry_price"]) * p["quantity"]
            for p in positions
        )
        return cash + pos_value

    def _log_daily(self, symbols_analyzed: int, actions: List[str]) -> None:
        """Log daily portfolio snapshot."""
        conn = _get_db(self.db_path)
        regime = "UNKNOWN"
        try:
            regime = self.combiner.regime_info.regime.value
        except Exception:
            pass

        conn.execute(
            """INSERT INTO paper_daily_log
               (log_date, portfolio_value, cash, position_count, regime,
                actions_taken, symbols_analyzed)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (datetime.now().isoformat(),
             self._portfolio_value(),
             paper_get_cash(self.db_path),
             len(paper_get_positions(self.db_path)),
             regime,
             "; ".join(actions) if actions else "No actions",
             symbols_analyzed),
        )
        conn.commit()
        conn.close()

    def get_summary(self) -> Dict:
        """Get comprehensive paper trading summary."""
        trades = paper_get_trades(500, self.db_path)
        positions = paper_get_positions(self.db_path)
        cash = paper_get_cash(self.db_path)
        peak = paper_get_peak(self.db_path)
        total = self._portfolio_value()
        start_date = _paper_get("start_date", "", self.db_path)

        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] <= 0]

        total_pnl = sum(t["pnl"] for t in trades)
        win_rate = len(wins) / len(trades) if trades else 0
        avg_win = np.mean([t["pnl_pct"] for t in wins]) if wins else 0
        avg_loss = np.mean([abs(t["pnl_pct"]) for t in losses]) if losses else 0
        profit_factor = (
            abs(sum(t["pnl"] for t in wins) / sum(t["pnl"] for t in losses))
            if losses and sum(t["pnl"] for t in losses) != 0
            else float("inf")
        )

        drawdown = (total - peak) / peak if peak > 0 else 0

        # Kelly fraction from actual results
        kf = kelly_fraction(win_rate, avg_win, avg_loss) if trades else 0

        # Sharpe from trades
        if len(trades) >= 5:
            returns = [t["pnl_pct"] for t in trades]
            sharpe = (np.mean(returns) - 0.04/252) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe = 0

        return {
            "portfolio_value": round(total, 2),
            "cash": round(cash, 2),
            "peak_value": round(peak, 2),
            "drawdown": round(drawdown, 4),
            "total_trades": len(trades),
            "open_positions": len(positions),
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(win_rate, 4),
            "avg_win_pct": round(avg_win, 4),
            "avg_loss_pct": round(avg_loss, 4),
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(sharpe, 2),
            "kelly_fraction": round(kf, 4),
            "start_date": start_date[:10] if start_date else "",
            "positions": [
                {
                    "symbol": p["symbol"],
                    "qty": p["quantity"],
                    "entry": p["entry_price"],
                    "current": p.get("current_price", p["entry_price"]),
                    "pnl": round((p.get("current_price", p["entry_price"]) - p["entry_price"]) * p["quantity"], 2),
                    "pnl_pct": f"{((p.get('current_price', p['entry_price']) - p['entry_price']) / p['entry_price']):.1%}",
                    "stop": p["stop_loss"],
                    "signal": p.get("signal_action", ""),
                }
                for p in positions
            ],
        }


# ──────────────────────────────────────────────
# CLI interface
# ──────────────────────────────────────────────

def main():
    """Run paper trading cycle from command line."""
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Paper trading engine")
    parser.add_argument("--symbols", nargs="+", help="Symbols to analyze")
    parser.add_argument("--package", help="Watchlist package")
    parser.add_argument("--capital", type=float, default=100000, help="Starting capital")
    parser.add_argument("--summary", action="store_true", help="Show summary only")
    args = parser.parse_args()

    state.init_db()
    trader = PaperTrader(starting_capital=args.capital)

    if args.summary:
        summary = trader.get_summary()
        print(f"\nPaper Trading Summary (started {summary['start_date']})")
        print(f"{'='*50}")
        print(f"Portfolio: ${summary['portfolio_value']:,.2f} (peak: ${summary['peak_value']:,.2f})")
        print(f"Cash:      ${summary['cash']:,.2f}")
        print(f"Drawdown:  {summary['drawdown']:.1%}")
        print(f"Trades:    {summary['total_trades']} (Win: {summary['win_rate']:.0%})")
        print(f"PnL:       ${summary['total_pnl']:+,.2f}")
        print(f"Sharpe:    {summary['sharpe_ratio']:.2f}")
        print(f"Kelly:     {summary['kelly_fraction']:.1%}")
        print(f"Positions: {summary['open_positions']}")
        for p in summary["positions"]:
            print(f"  {p['symbol']}: {p['qty']}x @ ${p['entry']:.2f} -> ${p['current']:.2f} ({p['pnl_pct']})")
        return

    # Determine symbols
    if args.symbols:
        symbols = [s.upper() for s in args.symbols]
    elif args.package:
        from config.watchlists import get_package_symbols
        symbols = get_package_symbols([args.package])
    else:
        symbols = Settings.load().watchlist

    result = trader.run_daily_cycle(symbols)

    print(f"\nPaper Trading Cycle Complete")
    print(f"Portfolio: ${result['portfolio_value']:,.2f} | Cash: ${result['cash']:,.2f}")
    print(f"Positions: {result['positions']} | Analyzed: {result['symbols_analyzed']}")
    for action in result["actions"]:
        print(f"  -> {action}")


if __name__ == "__main__":
    main()
