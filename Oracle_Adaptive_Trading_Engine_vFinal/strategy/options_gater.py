
from dataclasses import dataclass
from lucid_common import OptionsMetrics, select_expiry_date

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

MAX_RISK_PCT = 0.010
LIQUIDITY_MAX_SPREAD_PCT = 0.10
DEFAULT_MIN_DTE = 30
DEFAULT_MAX_DTE = 90

def options_gating_mechanism(signal: LucidSignal,
                             metrics: OptionsMetrics,
                             current_equity: float,
                             current_0_1_dte_count: int) -> OptionTrade:
    max_risk = current_equity * MAX_RISK_PCT
    if metrics.bid_ask_spread_pct > LIQUIDITY_MAX_SPREAD_PCT:
        return OptionTrade()
    abs_bias = abs(signal.bias)
    if abs_bias >= 0.40 and signal.confidence >= 0.75:
        if abs_bias >= 0.5 and signal.confidence >= 0.90 and current_0_1_dte_count == 0:
            expiry, dte = select_expiry_date(0, 1)
        else:
            expiry, dte = select_expiry_date(DEFAULT_MIN_DTE, DEFAULT_MAX_DTE)
        strat = "Long Debit Vertical Spread" if metrics.iv_rank < 0.35                 else "Short Credit Vertical Spread"
        side = "Bullish" if signal.bias > 0 else "Bearish"
        return OptionTrade(strat, side, max_risk, expiry, dte)
    if signal.confidence >= 0.60 and metrics.iv_rank >= 0.70 and abs_bias < 0.20:
        expiry, dte = select_expiry_date(DEFAULT_MIN_DTE, DEFAULT_MAX_DTE)
        return OptionTrade("Short Iron Condor", "Neutral", max_risk, expiry, dte)
    return OptionTrade()
