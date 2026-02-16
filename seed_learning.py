#!/usr/bin/env python3
"""Seed the learning system by running analyses and recording predictions.

Run this daily (via cron or scheduler) to build up the analysis_history database.
After 30+ days with 30+ outcomes, the adaptive weight system kicks in.

Usage:
    python seed_learning.py                    # Analyze default package
    python seed_learning.py --symbols AAPL MSFT NVDA   # Specific symbols
    python seed_learning.py --package mega_cap_tech     # Specific package
    python seed_learning.py --check-outcomes           # Only check outcomes (no new analysis)
    python seed_learning.py --all-packages             # Scan all active packages

Cron example (run at 6pm EST every weekday):
    0 18 * * 1-5 cd /path/to/project && python seed_learning.py >> logs/seed.log 2>&1
"""

import argparse
import logging
import sys
import time
from datetime import datetime

# Project imports
from portfolio import state
from portfolio.memory import save_analysis, check_outcomes, compute_engine_accuracy
from engines.signal_combiner import SignalCombiner
from config.settings import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/seed_learning.log", mode="a"),
    ],
)
logger = logging.getLogger("seed_learning")


def seed_analyses(symbols: list, combiner: SignalCombiner = None) -> int:
    """Run analysis on each symbol and save to database.

    Returns number of successfully analyzed symbols.
    """
    if combiner is None:
        combiner = SignalCombiner()

    saved = 0
    for i, symbol in enumerate(symbols):
        try:
            logger.info(f"[{i+1}/{len(symbols)}] Analyzing {symbol}...")
            sig = combiner.analyze(symbol)

            # Extract price from momentum engine metadata
            price = 0
            momentum_result = sig.engine_results.get("momentum")
            if momentum_result:
                price = momentum_result.metadata.get("entry", 0)

            regime_str = sig.regime.regime.value if sig.regime else "UNKNOWN"

            analysis_id = save_analysis(
                symbol=symbol,
                combined_score=sig.combined_score,
                action=sig.action,
                confidence=sig.confidence,
                agreement_pct=sig.agreement_pct,
                close_price=price,
                regime=regime_str,
                engine_results=sig.engine_results,
            )

            if analysis_id:
                saved += 1
                logger.info(
                    f"  -> {sig.action} (score={sig.combined_score:+.3f}, "
                    f"conf={sig.confidence:.0%}, regime={regime_str})"
                )

            # Rate limiting: avoid hammering yfinance
            if i < len(symbols) - 1:
                time.sleep(1.5)

        except Exception as e:
            logger.error(f"  Failed to analyze {symbol}: {e}")

    return saved


def main():
    parser = argparse.ArgumentParser(description="Seed the learning system with daily analyses")
    parser.add_argument("--symbols", nargs="+", help="Specific symbols to analyze")
    parser.add_argument("--package", help="Watchlist package to scan")
    parser.add_argument("--all-packages", action="store_true", help="Scan all active packages")
    parser.add_argument("--check-outcomes", action="store_true", help="Only check outcomes, no new analysis")
    parser.add_argument("--max-symbols", type=int, default=20, help="Max symbols to analyze per run")
    args = parser.parse_args()

    state.init_db()
    settings = Settings.load()

    logger.info(f"{'='*60}")
    logger.info(f"Seed Learning System - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"{'='*60}")

    # Step 1: Always check outcomes for past analyses
    logger.info("Checking outcomes for past analyses...")
    filled = check_outcomes()
    logger.info(f"Filled {filled} outcome(s)")

    if args.check_outcomes:
        # Recompute accuracy and exit
        accuracy = compute_engine_accuracy()
        for eng, data in accuracy.items():
            logger.info(f"  {eng}: {data['accuracy']:.0%} ({data['total']} signals)")
        return

    # Step 2: Determine which symbols to analyze
    if args.symbols:
        symbols = [s.upper() for s in args.symbols]
    elif args.package:
        from config.watchlists import get_package_symbols
        symbols = get_package_symbols([args.package])
    elif args.all_packages:
        symbols = settings.watchlist
    else:
        # Default: use active watchlist
        symbols = settings.watchlist

    # Limit to max_symbols
    if len(symbols) > args.max_symbols:
        # Rotate through symbols each day
        day_of_year = datetime.now().timetuple().tm_yday
        start_idx = (day_of_year * args.max_symbols) % len(symbols)
        symbols = symbols[start_idx:start_idx + args.max_symbols]
        if len(symbols) < args.max_symbols:
            symbols += settings.watchlist[:args.max_symbols - len(symbols)]

    logger.info(f"Analyzing {len(symbols)} symbols: {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")

    # Step 3: Run analyses
    combiner = SignalCombiner()
    saved = seed_analyses(symbols, combiner)

    # Step 4: Record regime for alerting
    try:
        from alerts.regime_alerts import record_regime
        if combiner.regime_info:
            change = record_regime(combiner.regime_info)
            if change:
                logger.warning(f"REGIME CHANGE: {change['previous']} -> {change['current']}")
    except Exception as e:
        logger.debug(f"Regime recording skipped: {e}")

    # Step 5: Recompute engine accuracy
    logger.info("Recomputing engine accuracy...")
    accuracy = compute_engine_accuracy()
    for eng, data in accuracy.items():
        if data.get("total", 0) > 0:
            logger.info(f"  {eng}: {data['accuracy']:.0%} ({data['total']} signals)")

    logger.info(f"{'='*60}")
    logger.info(f"Done: {saved}/{len(symbols)} symbols analyzed successfully")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()
