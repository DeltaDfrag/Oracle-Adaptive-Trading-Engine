"""
ORACLE Adaptive Trading Engine — Feature Store
------------------------------------------------
Generates robust, statistically sound features and labels for model training
using mlfinlab.  Compatible with both live feature computation and
offline backtesting.
"""

import pandas as pd
import numpy as np

# mlfinlab imports (requires: pip install mlfinlab)
from mlfinlab.labeling import get_events, add_vertical_barrier
from mlfinlab.filters import cusum_filter
from mlfinlab.features.fracdiff import frac_diff

# ------------------------------------------------------------
# 1. VOLATILITY ESTIMATION
# ------------------------------------------------------------

def get_volatility(close: pd.Series, span: int = 100) -> pd.Series:
    """
    Exponentially weighted moving volatility estimate.
    """
    returns = np.log(close).diff()
    return returns.ewm(span=span).std()


# ------------------------------------------------------------
# 2. EVENT FILTERING AND LABELING
# ------------------------------------------------------------

def generate_triple_barrier_labels(close: pd.Series,
                                   volatility: pd.Series,
                                   profit_taking_multiple: float = 2.0,
                                   stop_loss_multiple: float = 1.0,
                                   vertical_barrier_days: int = 5):
    """
    Applies CUSUM filter and triple-barrier labeling.
    Returns a DataFrame with timestamps and label information.
    """
    # Detect significant moves
    events = cusum_filter(close, threshold=volatility.mean())
    vertical_barriers = add_vertical_barrier(events, close, num_days=vertical_barrier_days)

    # Use mlfinlab’s triple-barrier logic
    labels = get_events(
        close=close,
        t_events=events,
        pt_sl=[profit_taking_multiple, stop_loss_multiple],
        target=volatility,
        min_ret=volatility.median(),
        num_threads=1,
        vertical_barrier_times=vertical_barriers,
        side_prediction=None
    )
    return labels


# ------------------------------------------------------------
# 3. FRACTIONAL DIFFERENTIATION (STATIONARY FEATURES)
# ------------------------------------------------------------

def generate_fracdiff_features(df: pd.DataFrame, d: float = 0.5) -> pd.DataFrame:
    """
    Fractionally differentiate price series to achieve stationarity while preserving memory.
    """
    fd = frac_diff(df, d)
    fd.columns = [f"{c}_fracdiff" for c in df.columns]
    return fd


# ------------------------------------------------------------
# 4. MASTER PIPELINE
# ------------------------------------------------------------

def build_feature_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Main entry point for SMITH++ and ORACLE++.
    Adds volatility, fractional-diff features, and event labels.
    """
    close = df['Close']
    vol = get_volatility(close)
    labels = generate_triple_barrier_labels(close, vol)
    fd = generate_fracdiff_features(df[['Close']])

    # merge everything
    dataset = df.copy()
    dataset['volatility'] = vol
    dataset = dataset.join(fd)
    dataset = dataset.join(labels, how='left', rsuffix='_label')

    return dataset


if __name__ == "__main__":
    # Example usage / quick test
    sample = pd.DataFrame({'Close': np.linspace(100, 110, 100)})
    features = build_feature_dataset(sample)
    print(features.head())# ORACLE_FEATURE_STORE: Rolling features, purging, embargo logic
