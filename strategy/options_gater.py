from dataclasses import dataclass
# Support both absolute and package-relative imports for lucid_common to avoid ImportError in different contexts
try:
    from lucid_common import OptionsMetrics, select_expiry_date
except Exception:
    try:
        from .lucid_common import OptionsMetrics, select_expiry_date  # type: ignore
    except Exception:
        # Last-resort placeholders so static analysis/type-checkers won't fail;
        # at runtime you should ensure lucid_common is available on PYTHONPATH or installed.
        OptionsMetrics = object
        def select_expiry_date(*args, **kwargs):
            raise ImportError("Cannot import select_expiry_date from lucid_common")
from ops.config import MAX_GAMMA_LIMIT, MIN_THETA_PREMIUM_SALE

@dataclass
class LucidSignal:
    bias: float
    confidence: float
    trade_prob: float


@dataclass
class OptionTrade:
    strategy: str = "None"
    side: str = "none"
    max_risk_dollars: float = 0.0
    expiry_date: str = ""
    entry_dte: int = 0
    reason: str = ""  # Added field for veto transparency


# --- Constants and Tunables ---
MAX_RISK_PCT = 0.010
LIQUIDITY_MAX_SPREAD_PCT = 0.02  # Tightened liquidity requirement (was 0.10)
DEFAULT_MIN_DTE = 30
DEFAULT_MAX_DTE = 90


# ======================================================================
# Main Gating Function
# ======================================================================

def options_gating_mechanism(
    signal: LucidSignal,
    metrics: OptionsMetrics,
    current_equity: float,
    current_0_1_dte_count: int
) -> OptionTrade:
    """
    Determines the appropriate options strategy to deploy
    based on signal strength, volatility environment, and liquidity constraints.
    """
    max_risk = current_equity * MAX_RISK_PCT

    # 1. Liquidity veto
    if metrics.bid_ask_spread_pct > LIQUIDITY_MAX_SPREAD_PCT:
        return OptionTrade(reason=f"liquidity_veto ({metrics.bid_ask_spread_pct:.2%})")

    abs_bias = abs(signal.bias)

    # 2a. Gamma veto — avoid ultra-high gamma exposure near expiry
    if metrics.gamma > MAX_GAMMA_LIMIT and metrics.theta != 0 and metrics.entry_dte < 5:
        return OptionTrade(reason="excessive_gamma_risk")

    # 2b. Theta veto — premium-selling strategies must have adequate theta benefit
    if metrics.theta <= MIN_THETA_PREMIUM_SALE and metrics.iv_rank > 0.75:
        return OptionTrade(reason="insufficient_theta_for_premium_sale")

    # 3. Strategy Selection Logic
    # -----------------------------------------------------

    # High conviction directional trades
    if abs_bias >= 0.40 and signal.confidence >= 0.75:
        # Ultra-short 0-1 DTE allowed if high confidence and none open
        if abs_bias >= 0.5 and signal.confidence >= 0.90 and current_0_1_dte_count == 0:
            expiry, dte = select_expiry_date(0, 1)
        else:
            expiry, dte = select_expiry_date(DEFAULT_MIN_DTE, DEFAULT_MAX_DTE)

        strat = "Long Debit Vertical Spread" if metrics.iv_rank < 0.35 else "Short Credit Vertical Spread"
        side = "Bullish" if signal.bias > 0 else "Bearish"

        return OptionTrade(
            strategy=strat,
            side=side,
            max_risk_dollars=max_risk,
            expiry_date=expiry,
            entry_dte=dte,
        )

    # Neutral / High-IV Environment
    if abs_bias < 0.20 and signal.confidence >= 0.60 and metrics.iv_rank >= 0.70:
        expiry, dte = select_expiry_date(DEFAULT_MIN_DTE, DEFAULT_MAX_DTE)
        return OptionTrade(
            strategy="Short Iron Condor",
            side="Neutral",
            max_risk_dollars=max_risk,
            expiry_date=expiry,
            entry_dte=dte,
        )

    # Default fallback veto
    return OptionTrade(reason="no_strategy_match")
