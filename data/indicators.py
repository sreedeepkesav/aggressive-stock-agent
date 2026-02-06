"""Canonical technical indicator implementations. ONE function per indicator, used everywhere."""

import numpy as np
import pandas as pd


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder's smoothing)."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def rsi_latest(prices: pd.Series, period: int = 14) -> float:
    """Return the latest RSI value, or 50.0 if insufficient data."""
    if len(prices) < period + 1:
        return 50.0
    rsi = calculate_rsi(prices, period)
    val = rsi.iloc[-1]
    return val if not pd.isna(val) else 50.0


def calculate_sma(prices: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average."""
    return prices.rolling(window=window).mean()


def calculate_ema(prices: pd.Series, span: int) -> pd.Series:
    """Exponential Moving Average."""
    return prices.ewm(span=span).mean()


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(window=period).mean()


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD line, signal line, and histogram."""
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(prices: pd.Series, window: int = 20, num_std: float = 2.0):
    """Bollinger Bands (upper, middle, lower)."""
    middle = prices.rolling(window=window).mean()
    std = prices.rolling(window=window).std()
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    return upper, middle, lower


def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume."""
    direction = np.where(close > close.shift(1), volume,
                         np.where(close < close.shift(1), -volume, 0))
    return pd.Series(direction, index=close.index).cumsum()


def calculate_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3):
    """Stochastic Oscillator (%K, %D). Better than RSI at extremes."""
    lowest_low = df["Low"].rolling(window=k_period).min()
    highest_high = df["High"].rolling(window=k_period).max()
    denom = highest_high - lowest_low
    pct_k = 100 * (df["Close"] - lowest_low) / denom.replace(0, np.nan)
    pct_d = pct_k.rolling(window=d_period).mean()
    return pct_k, pct_d


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """Volume Weighted Average Price (intraday/daily reset approximation)."""
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    cumulative_tp_vol = (typical_price * df["Volume"]).cumsum()
    cumulative_vol = df["Volume"].cumsum()
    return cumulative_tp_vol / cumulative_vol.replace(0, np.nan)


def calculate_roc(prices: pd.Series, period: int = 12) -> pd.Series:
    """Rate of Change (momentum quality)."""
    return (prices / prices.shift(period) - 1) * 100


def calculate_bb_pctb(prices: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.Series:
    """Bollinger %B: where price sits in the bands (0-1 scale, can exceed)."""
    upper, middle, lower = calculate_bollinger_bands(prices, window, num_std)
    band_width = upper - lower
    return (prices - lower) / band_width.replace(0, np.nan)


def calculate_keltner_channels(df: pd.DataFrame, ema_period: int = 20, atr_period: int = 14, multiplier: float = 1.5):
    """Keltner Channels (EMA +/- ATR*multiplier). Upper, middle, lower."""
    middle = calculate_ema(df["Close"], ema_period)
    atr = calculate_atr(df, atr_period)
    upper = middle + (atr * multiplier)
    lower = middle - (atr * multiplier)
    return upper, middle, lower


def calculate_adl(df: pd.DataFrame) -> pd.Series:
    """Accumulation/Distribution Line."""
    high_low = df["High"] - df["Low"]
    clv = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / high_low.replace(0, np.nan)
    clv = clv.fillna(0)
    return (clv * df["Volume"]).cumsum()


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add all standard technical indicators to a DataFrame with OHLCV columns.

    This replaces MomentumBreakoutEngine._add_technical_indicators and all
    duplicated indicator calculations throughout the codebase.
    """
    if df.empty or len(df) < 50:
        return df

    close = df["Close"]

    # Moving averages
    df["SMA_20"] = calculate_sma(close, 20)
    df["SMA_50"] = calculate_sma(close, 50)
    df["SMA_200"] = calculate_sma(close, 200)
    df["EMA_12"] = calculate_ema(close, 12)
    df["EMA_26"] = calculate_ema(close, 26)

    # Volume
    df["Volume_SMA_20"] = calculate_sma(df["Volume"], 20)
    df["Volume_Ratio"] = df["Volume"] / df["Volume_SMA_20"]
    df["OBV"] = calculate_obv(close, df["Volume"])

    # Momentum
    df["RSI"] = calculate_rsi(close, 14)
    df["MACD"], df["MACD_Signal"], df["MACD_Histogram"] = calculate_macd(close)

    # Volatility
    df["ATR"] = calculate_atr(df, 14)
    df["BB_Upper"], df["BB_Middle"], df["BB_Lower"] = calculate_bollinger_bands(close)
    df["BB_PctB"] = calculate_bb_pctb(close)

    # Stochastic
    df["Stoch_K"], df["Stoch_D"] = calculate_stochastic(df)

    # Rate of Change
    df["ROC_12"] = calculate_roc(close, 12)

    # VWAP
    df["VWAP"] = calculate_vwap(df)

    # Keltner Channels
    df["Keltner_Upper"], df["Keltner_Middle"], df["Keltner_Lower"] = calculate_keltner_channels(df)

    # Accumulation/Distribution
    df["ADL"] = calculate_adl(df)

    return df
