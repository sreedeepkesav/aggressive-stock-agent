"""Risk manager: enforces position limits, drawdown circuit breaker, sector caps."""

import logging
from typing import List, Optional

import numpy as np

from config.settings import RiskParams
from data.market_data import get_history
from data.indicators import calculate_atr
from portfolio.models import Position
from portfolio import state

logger = logging.getLogger("stock_agent")


class RiskManager:
    """Enforces all risk rules before allowing a trade."""

    def __init__(self, risk_params: Optional[RiskParams] = None):
        self.params = risk_params or RiskParams.from_env()

    def check_can_open_position(self, symbol: str, proposed_value: float, sector: str = "") -> dict:
        """Check all risk rules. Returns {'allowed': bool, 'reasons': [...]}."""
        reasons = []
        positions = state.get_positions()
        cash = state.get_cash_balance()
        peak = state.get_peak_value()

        total_value = cash + sum(p.market_value for p in positions)

        # 1. Cash reserve check
        min_cash = total_value * self.params.cash_reserve_pct
        if cash - proposed_value < min_cash:
            reasons.append(f"Insufficient cash: ${cash:.0f} - ${proposed_value:.0f} < ${min_cash:.0f} reserve")

        # 2. Max position size
        max_pos = total_value * self.params.max_position_pct
        if proposed_value > max_pos:
            reasons.append(f"Position ${proposed_value:.0f} exceeds max ${max_pos:.0f} ({self.params.max_position_pct:.0%})")

        # 3. Max simultaneous positions
        if len(positions) >= self.params.max_simultaneous_positions:
            reasons.append(f"Max positions reached ({self.params.max_simultaneous_positions})")

        # 4. Sector concentration
        if sector:
            sector_value = sum(p.market_value for p in positions if p.sector == sector) + proposed_value
            if sector_value / total_value > self.params.max_sector_concentration:
                reasons.append(f"Sector '{sector}' would exceed {self.params.max_sector_concentration:.0%} cap")

        # 5. Correlation check — prevent correlated position clustering
        if positions and self.params.max_position_correlation < 1.0:
            correlations = []
            for pos in positions:
                corr = self._calculate_correlation(symbol, pos.symbol)
                correlations.append((pos.symbol, corr))

            avg_corr = np.mean([c for _, c in correlations])
            if avg_corr > self.params.max_position_correlation:
                corr_details = ", ".join(f"{s}:{c:.2f}" for s, c in correlations)
                reasons.append(
                    f"High correlation to holdings: avg {avg_corr:.2f} > "
                    f"{self.params.max_position_correlation:.2f} ({corr_details})"
                )

        # 6. Drawdown circuit breaker
        drawdown = (total_value - peak) / peak if peak > 0 else 0
        if drawdown < self.params.drawdown_circuit_breaker:
            reasons.append(f"Drawdown circuit breaker: {drawdown:.1%} < {self.params.drawdown_circuit_breaker:.1%}")

        # 7. Portfolio heat
        total_risk = sum(
            abs(p.entry_price - p.stop_loss) * p.quantity
            for p in positions if p.stop_loss > 0
        )
        proposed_risk_pct = total_risk / total_value if total_value > 0 else 0
        if proposed_risk_pct > self.params.max_portfolio_heat:
            reasons.append(f"Portfolio heat {proposed_risk_pct:.1%} exceeds {self.params.max_portfolio_heat:.0%}")

        # 8. Duplicate position check
        existing = [p for p in positions if p.symbol == symbol]
        if existing:
            reasons.append(f"Already holding {symbol}")

        return {
            "allowed": len(reasons) == 0,
            "reasons": reasons,
            "portfolio_value": total_value,
            "cash": cash,
            "position_count": len(positions),
            "drawdown": drawdown,
        }

    def _calculate_correlation(self, symbol: str, existing_symbol: str,
                               lookback_days: int = 60) -> float:
        """Calculate correlation of daily returns between two symbols.

        Returns 1.0 (assume high correlation) if data is insufficient or fetch fails.
        This is the conservative choice — it prevents adding correlated positions when
        we can't tell.
        """
        try:
            df1 = get_history(symbol, period="3mo")
            df2 = get_history(existing_symbol, period="3mo")

            if df1.empty or df2.empty or len(df1) < 20 or len(df2) < 20:
                return 1.0

            returns1 = df1["Close"].pct_change().dropna().tail(lookback_days)
            returns2 = df2["Close"].pct_change().dropna().tail(lookback_days)

            # Align on common dates
            common_idx = returns1.index.intersection(returns2.index)
            if len(common_idx) < 20:
                return 1.0

            corr = returns1.loc[common_idx].corr(returns2.loc[common_idx])
            return float(corr) if not np.isnan(corr) else 1.0
        except Exception as e:
            logger.debug(f"Correlation calc failed {symbol} vs {existing_symbol}: {e}")
            return 1.0

    def calculate_stop_loss(self, symbol: str, entry_price: float, trade_type: str = "swing") -> float:
        """Calculate ATR-based stop loss."""
        df = get_history(symbol, period="3mo")
        if df.empty or len(df) < 20:
            # Fallback: 5% stop
            return entry_price * 0.95

        atr = calculate_atr(df).iloc[-1]
        multiplier = self.params.stop_loss_atr_swing if trade_type == "swing" else self.params.stop_loss_atr_position
        return round(entry_price - (atr * multiplier), 2)

    def calculate_position_size(self, entry_price: float, stop_loss: float) -> int:
        """Calculate position size based on risk per trade."""
        if entry_price <= 0 or stop_loss <= 0 or stop_loss >= entry_price:
            return 0

        cash = state.get_cash_balance()
        positions = state.get_positions()
        total_value = cash + sum(p.market_value for p in positions)

        # Max position value
        max_value = total_value * self.params.max_position_pct

        # Risk-based sizing: risk per trade = 1% of portfolio
        risk_per_share = entry_price - stop_loss
        risk_budget = total_value * 0.01  # 1% risk per trade
        risk_based_qty = int(risk_budget / risk_per_share)

        # Value-based sizing
        value_based_qty = int(max_value / entry_price)

        # Take the smaller of the two
        qty = min(risk_based_qty, value_based_qty)
        return max(0, qty)

    def check_exit_signals(self) -> list:
        """Check all open positions for exit signals (trailing stops, profit taking, time exits)."""
        from portfolio.exits import check_exit_signals
        positions = state.get_positions()
        return check_exit_signals(positions)

    def update_peak_value(self) -> float:
        """Update peak portfolio value for drawdown tracking."""
        positions = state.get_positions()
        cash = state.get_cash_balance()
        total = cash + sum(p.market_value for p in positions)
        current_peak = state.get_peak_value()
        if total > current_peak:
            state.set_peak_value(total)
            return total
        return current_peak
