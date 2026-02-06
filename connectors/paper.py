"""Paper trading connector backed by SQLite portfolio state."""

import logging
from datetime import datetime
from typing import Dict, List

from connectors.base import BrokerConnector
from data.market_data import get_history
from portfolio.models import Order, Position, Trade
from portfolio import state

logger = logging.getLogger("stock_agent")


class PaperTrader(BrokerConnector):
    """Simulated trading using local SQLite database."""

    def connect(self) -> bool:
        state.init_db()
        logger.info("Paper trader connected")
        return True

    def get_positions(self) -> List[Position]:
        positions = state.get_positions()
        # Update current prices
        for pos in positions:
            df = get_history(pos.symbol, period="5d")
            if not df.empty:
                pos.current_price = df["Close"].iloc[-1]
                state.update_position_price(pos.id, pos.current_price)
        return positions

    def place_order(self, order: Order) -> Dict:
        """Execute a paper trade immediately at market price."""
        if order.side == "BUY":
            return self._execute_buy(order)
        elif order.side == "SELL":
            return self._execute_sell(order)
        return {"status": "REJECTED", "reason": f"Unknown side: {order.side}"}

    def get_account_balance(self) -> float:
        return state.get_cash_balance()

    def cancel_order(self, order_id: str) -> bool:
        return True  # Paper trades execute immediately

    def _execute_buy(self, order: Order) -> Dict:
        cash = state.get_cash_balance()
        cost = order.quantity * order.price
        if cost > cash:
            return {"status": "REJECTED", "reason": f"Insufficient cash: ${cash:.2f} < ${cost:.2f}"}

        pos = Position(
            symbol=order.symbol,
            quantity=order.quantity,
            entry_price=order.price,
            entry_date=datetime.now().isoformat(),
            stop_loss=order.stop_loss,
            target_price=order.target_price,
            current_price=order.price,
        )
        pos_id = state.add_position(pos)
        state.set_cash_balance(cash - cost)

        logger.info(f"Paper BUY: {order.quantity} {order.symbol} @ ${order.price:.2f}")
        return {"status": "FILLED", "position_id": pos_id, "cost": cost}

    def _execute_sell(self, order: Order) -> Dict:
        positions = state.get_positions()
        matching = [p for p in positions if p.symbol == order.symbol]
        if not matching:
            return {"status": "REJECTED", "reason": f"No position in {order.symbol}"}

        pos = matching[0]
        proceeds = order.quantity * order.price
        pnl = (order.price - pos.entry_price) * order.quantity
        pnl_pct = (order.price - pos.entry_price) / pos.entry_price

        trade = Trade(
            symbol=order.symbol, side="SELL",
            quantity=order.quantity, entry_price=pos.entry_price,
            exit_price=order.price, entry_date=pos.entry_date,
            exit_date=datetime.now().isoformat(),
            pnl=round(pnl, 2), pnl_pct=round(pnl_pct, 4),
            reason=order.status,
        )
        state.add_trade(trade)
        state.remove_position(pos.id)
        state.set_cash_balance(state.get_cash_balance() + proceeds)

        logger.info(f"Paper SELL: {order.quantity} {order.symbol} @ ${order.price:.2f}, PnL=${pnl:.2f}")
        return {"status": "FILLED", "pnl": pnl, "proceeds": proceeds}
