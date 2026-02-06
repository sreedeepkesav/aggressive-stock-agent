"""SQLite-backed portfolio state persistence."""

import logging
import os
import sqlite3
from datetime import datetime
from typing import List, Optional

from portfolio.models import Position, Trade, Order

logger = logging.getLogger("stock_agent")

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "portfolio.db")


def _get_db(path: str = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or _DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(path: str = None) -> None:
    """Create tables if they don't exist."""
    conn = _get_db(path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            entry_price REAL NOT NULL,
            entry_date TEXT NOT NULL,
            stop_loss REAL NOT NULL DEFAULT 0,
            target_price REAL NOT NULL DEFAULT 0,
            sector TEXT DEFAULT '',
            current_price REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS trades (
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
            reason TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            order_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            stop_loss REAL DEFAULT 0,
            target_price REAL DEFAULT 0,
            status TEXT DEFAULT 'PENDING',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS portfolio_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def get_cash_balance(path: str = None) -> float:
    """Get current cash balance."""
    conn = _get_db(path)
    row = conn.execute("SELECT value FROM portfolio_meta WHERE key='cash_balance'").fetchone()
    conn.close()
    return float(row["value"]) if row else 100000.0


def set_cash_balance(amount: float, path: str = None) -> None:
    conn = _get_db(path)
    conn.execute("INSERT OR REPLACE INTO portfolio_meta (key, value) VALUES ('cash_balance', ?)", (str(amount),))
    conn.commit()
    conn.close()


def get_peak_value(path: str = None) -> float:
    """Get historical peak portfolio value (for drawdown calculation)."""
    conn = _get_db(path)
    row = conn.execute("SELECT value FROM portfolio_meta WHERE key='peak_value'").fetchone()
    conn.close()
    return float(row["value"]) if row else 100000.0


def set_peak_value(value: float, path: str = None) -> None:
    conn = _get_db(path)
    conn.execute("INSERT OR REPLACE INTO portfolio_meta (key, value) VALUES ('peak_value', ?)", (str(value),))
    conn.commit()
    conn.close()


# --- Positions ---

def add_position(pos: Position, path: str = None) -> int:
    conn = _get_db(path)
    cur = conn.execute(
        "INSERT INTO positions (symbol, quantity, entry_price, entry_date, stop_loss, target_price, sector, current_price) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (pos.symbol, pos.quantity, pos.entry_price, pos.entry_date, pos.stop_loss, pos.target_price, pos.sector, pos.current_price),
    )
    conn.commit()
    pos_id = cur.lastrowid
    conn.close()
    return pos_id


def get_positions(path: str = None) -> List[Position]:
    conn = _get_db(path)
    rows = conn.execute("SELECT * FROM positions").fetchall()
    conn.close()
    return [Position(
        id=r["id"], symbol=r["symbol"], quantity=r["quantity"],
        entry_price=r["entry_price"], entry_date=r["entry_date"],
        stop_loss=r["stop_loss"], target_price=r["target_price"],
        sector=r["sector"], current_price=r["current_price"],
    ) for r in rows]


def remove_position(position_id: int, path: str = None) -> None:
    conn = _get_db(path)
    conn.execute("DELETE FROM positions WHERE id=?", (position_id,))
    conn.commit()
    conn.close()


def update_position_price(position_id: int, price: float, path: str = None) -> None:
    conn = _get_db(path)
    conn.execute("UPDATE positions SET current_price=? WHERE id=?", (price, position_id))
    conn.commit()
    conn.close()


# --- Trades ---

def add_trade(trade: Trade, path: str = None) -> int:
    conn = _get_db(path)
    cur = conn.execute(
        "INSERT INTO trades (symbol, side, quantity, entry_price, exit_price, entry_date, exit_date, pnl, pnl_pct, reason) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (trade.symbol, trade.side, trade.quantity, trade.entry_price, trade.exit_price,
         trade.entry_date, trade.exit_date, trade.pnl, trade.pnl_pct, trade.reason),
    )
    conn.commit()
    trade_id = cur.lastrowid
    conn.close()
    return trade_id


def get_trades(limit: int = 50, path: str = None) -> List[Trade]:
    conn = _get_db(path)
    rows = conn.execute("SELECT * FROM trades ORDER BY exit_date DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [Trade(
        id=r["id"], symbol=r["symbol"], side=r["side"], quantity=r["quantity"],
        entry_price=r["entry_price"], exit_price=r["exit_price"],
        entry_date=r["entry_date"], exit_date=r["exit_date"],
        pnl=r["pnl"], pnl_pct=r["pnl_pct"], reason=r["reason"],
    ) for r in rows]


# --- Orders ---

def add_order(order: Order, path: str = None) -> int:
    conn = _get_db(path)
    cur = conn.execute(
        "INSERT INTO orders (symbol, side, order_type, quantity, price, stop_loss, target_price, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (order.symbol, order.side, order.order_type, order.quantity, order.price,
         order.stop_loss, order.target_price, order.status, order.created_at),
    )
    conn.commit()
    order_id = cur.lastrowid
    conn.close()
    return order_id


def get_pending_orders(path: str = None) -> List[Order]:
    conn = _get_db(path)
    rows = conn.execute("SELECT * FROM orders WHERE status='PENDING' ORDER BY created_at DESC").fetchall()
    conn.close()
    return [Order(
        id=r["id"], symbol=r["symbol"], side=r["side"], order_type=r["order_type"],
        quantity=r["quantity"], price=r["price"], stop_loss=r["stop_loss"],
        target_price=r["target_price"], status=r["status"], created_at=r["created_at"],
    ) for r in rows]
