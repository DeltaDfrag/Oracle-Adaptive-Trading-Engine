from dataclasses import dataclass
from typing import Tuple, Dict, Literal
from risk.pnl_models import strategy_greeks, OptionLeg


# ======================================================================
# Data Structures
# ======================================================================

@dataclass
class OptionsMetrics:
    """
    Holds option-related risk and structure information.
    Used by options_gating_mechanism to assess trade feasibility.
    """
    bid_ask_spread_pct: float = 0.0
    iv_rank: float = 0.0
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0


@dataclass
class OptionsTradeDetails:
    """
    Output structure passed from ORACLE to Execution layer.
    Stores actionable trade metadata.
    """
    asset_type: str = "none"
    strategy: str = "None"
    side: str = "none"
    contracts_qty: int = 0
    max_risk_dollars: float = 0.0
    entry_price_px: float = 0.0
    expiry_date: str = ""
    entry_dte: int = 0


# ======================================================================
# Utility Functions
# ======================================================================

def select_expiry_date(min_dte: int, max_dte: int) -> Tuple[str, int]:
    """
    Selects an expiry date given a DTE range.
    In production, this will query available options chain data.
    """
    selected_dte = min_dte if min_dte > 0 else max_dte
    return f"2025-12-{selected_dte}", selected_dte


# ======================================================================
# Options Metrics Computation
# ======================================================================

def compute_options_metrics(
    S_price: float = 100.0,
    iv_level: float = 0.25,
    risk_free_rate: float = 0.05,
    strategy_name: str = "Short Credit Vertical Spread",
    dte_days: int = 45
) -> OptionsMetrics:
    """
    Computes the relevant options metrics and Greeks for a given strategy.
    This function acts as the single interface between ORACLE and the risk engine.

    Args:
        S_price: Current underlying price
        iv_level: Implied volatility
        risk_free_rate: Annualized risk-free rate
        strategy_name: Options strategy (e.g., Short Iron Condor)
        dte_days: Days to expiry
    """
    # --- Simulated Market Context ---
    spread_pct = 0.005     # Tight liquid market
    iv_rank = 0.80         # Slightly elevated volatility environment

    # --- Strategy Structure Definition ---
    if strategy_name == "Short Credit Vertical Spread":
        # Example: Short Put @ 95, Long Put @ 90
        strategy_legs = (
            OptionLeg(side=-1, type="put", strike=95.0, dte=dte_days),
            OptionLeg(side=1, type="put", strike=90.0, dte=dte_days),
        )

    elif strategy_name == "Short Iron Condor":
        # Example: Sell 105C/110C spread and 90P/95P spread
        strategy_legs = (
            OptionLeg(side=-1, type="call", strike=105.0, dte=dte_days),
            OptionLeg(side=1, type="call", strike=110.0, dte=dte_days),
            OptionLeg(side=-1, type="put", strike=95.0, dte=dte_days),
            OptionLeg(side=1, type="put", strike=90.0, dte=dte_days),
        )

    elif strategy_name == "Long Debit Vertical Spread":
        # Example: Long Call @ 100, Short Call @ 105
        strategy_legs = (
            OptionLeg(side=1, type="call", strike=100.0, dte=dte_days),
            OptionLeg(side=-1, type="call", strike=105.0, dte=dte_days),
        )

    else:
        # Unknown or unsupported strategy type
        return OptionsMetrics(spread_pct, iv_rank)

    # --- Calculate Greeks for Multi-Leg Structure ---
    greeks = strategy_greeks(
        S=S_price,
        r=risk_free_rate,
        q=0.0,           # Dividend yield (placeholder)
        iv=iv_level,
        legs=strategy_legs,
    )

    # --- Return Populated Metrics ---
    return OptionsMetrics(
        bid_ask_spread_pct=spread_pct,
        iv_rank=iv_rank,
        delta=greeks["delta"],
        gamma=greeks["gamma"],
        theta=greeks["theta"],
        vega=greeks["vega"],
    )

