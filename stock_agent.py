#!/usr/bin/env python3
"""Stock Analysis Agent — entry point.

All functionality lives in the modular codebase:
  - cli/main.py:   Command routing and CLI logic
  - engines/:      Analysis engines (momentum, technical, etc.)
  - portfolio/:    Position management, backtesting, risk
  - data/:         Market data and indicator calculations
  - config/:       Settings and configuration

Usage:
  python stock_agent.py ticker NVDA
  python stock_agent.py scan 10 --package sector_semiconductors
  python stock_agent.py web          # Launch Streamlit dashboard
  python stock_agent.py --help       # Full command list
"""

import sys
from cli.main import main

if __name__ == "__main__":
    main()
