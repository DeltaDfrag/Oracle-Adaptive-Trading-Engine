# lucid_common.py

from dataclasses import dataclass
from typing import Tuple, Dict, Literal
from risk.pnl_models import strategy_greeks, OptionLeg

# --- Shared Data Structures ---

@dataclass
class OptionsMetrics:
    """
    Aggregated options metrics used by the options_gating_mechanism.
    Populated by compute_options_metrics.
    """
    bid_ask_spread_pct: float = 0.0
    iv_rank: float = 0.0

    # Net strategy Greeks (per 1 underlying unit exposure)
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0      # daily theta
    vega: float = 0.0

@dataclass
class OptionsTradeDetails:
    """
    Structure passed from ORACLE to the execution layer.
    """
    asset_type: str = "none"       # 'option' or 'equity'
    strategy: str = "None"
    side: str = "none"             # 'Bullish'/'Bearish'/'Neutral' or 'buy'/'sell'
    contracts_qty: int = 0
    max_risk_dollars: float = 0.0
    entry_price_px: float = 0.0
    expiry_date: str = ""
    entry_dte: int = 0

def select_expiry_date(min_dte: int, max_dte: int) -> Tuple[str, int]:
    """
    Placeholder expiry selector. In production, this would query live option chains.
    """
    selected_dte = min_dte if min_dte > 0 else max_dte
    return f"2025-12-{max(1, min(28, selected_dte))}", selected_dte

# ----------------------------------------------------------------
# Risk Metric Generator (OptionsMetrics Factory)
# ----------------------------------------------------------------

def compute_options_metrics(
    S_price: float = 100.0,
    iv_level: float = 0.25,
    risk_free_rate: float = 0.05,
    strategy_name: str = "Short Credit Vertical Spread",
    dte_days: int = 45
) -> OptionsMetrics:
    """
    Computes liquidity, IV, and aggregated Greeks for a candidate strategy.
    In production, this consumes real chain data; here it's structured and pluggable.
    """
    # 1. Example Liquidity & IV Rank (to be replaced with live data)
    spread_pct = 0.005
    iv_rank = 0.85

    # 2. Define legs for the chosen strategy
    if strategy_name == "Short Credit Vertical Spread":
        legs = (
            OptionLeg(side=-1, type='put', strike=95.0, dte=dte_days),
            OptionLeg(side=1, type='put', strike=90.0, dte=dte_days),
        )
    elif strategy_name == "Short Iron Condor":
        legs = (
            OptionLeg(side=-1, type='call', strike=105.0, dte=dte_days),
            OptionLeg(side=1, type='call', strike=110.0, dte=dte_days),
            OptionLeg(side=-1, type='put', strike=95.0, dte=dte_days),
            OptionLeg(side=1, type='put', strike=90.0, dte=dte_days),
        )
    else:
        return OptionsMetrics(bid_ask_spread_pct=spread_pct, iv_rank=iv_rank)

    # 3. Aggregate Greeks
    greeks = strategy_greeks(
        S=S_price,
        r=risk_free_rate,
        q=0.0,
        iv=iv_level,
        legs=legs
    )

    return OptionsMetrics(
        bid_ask_spread_pct=spread_pct,
        iv_rank=iv_rank,
        delta=greeks["delta"],
        gamma=greeks["gamma"],
        theta=greeks["theta"],
        vega=greeks["vega"]
    )
