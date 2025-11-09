"""
ORACLE Engine Core

High-level responsibilities:
- Enforce config/sizing integrity (Kelly, CVaR, max position caps).
- Use MetaModel to gate low-quality signals.
- Use Strategy Registry to restrict allowed structures by equity tier.
- Use options_gater to select structures (spreads, condors, etc.).
- Size positions via tempered Kelly + CVaR cap (+ Black-Litterman multiplier hook).
- Provide a single approve(snapshot) entrypoint for backtests and live trading.
"""

import time
import json
from typing import Dict, Any, List, Tuple

import numpy as np

# ---- Internal imports ----
from core.lucid import OptionsMetrics, OptionsTradeDetails
from ops.config import (
    SMALL_ACCOUNT_RISK,
    META_THRESHOLD,
    DTE_STATE,
    CVAR_CAP,
    MAX_POS_PCT,
)
from strategy.options_gater import LucidSignal, options_gating_mechanism, OptionTrade
from strategy.meta_model import MetaModel
from risk.sizing import final_size, KellyConfig
from risk.tails_evt import estimate_cvar

# Black-Litterman is optional; engine must not die if missing
try:
    from risk.black_litterman import black_litterman_weights
    HAS_BLACK_LITTERMAN = True
except ImportError:
    HAS_BLACK_LITTERMAN = False


# ============================================================
# Strategy Registry (Tiered access)
# ============================================================

def load_allowed_strategies(
    equity: float,
    registry_path: str = "core/Strategy_Registry.json",
) -> List[str]:
    """
    Returns list of enabled strategies based on account equity.
    If registry is missing, falls back to a conservative default set.
    """
    try:
        with open(registry_path, "r") as f:
            reg = json.load(f)
    except FileNotFoundError:
        # Safe fallback; you can tighten this if needed.
        return [
            "Short Credit Vertical Spread",
            "Short Iron Condor",
            "Long Debit Vertical Spread",
            "Directional Equity",
        ]

    tiers = sorted(
        reg.get("capital_tiers", []),
        key=lambda x: float(x.get("min_equity", 0.0)),
    )

    allowed: List[str] = []
    for tier in tiers:
        if equity >= float(tier.get("min_equity", 0.0)):
            allowed = tier.get("strategies", [])
        else:
            break

    return allowed


# ============================================================
# Config / Sizing Integrity
# ============================================================

meta_model = MetaModel(threshold=META_THRESHOLD)
lucid_pulse = LucidPulse()

def _check_integrity() -> None:
    """
    Sanity checks so config and sizing do not silently diverge.
    In live trading, any failure here should be treated as fatal.
    """
    cfg = KellyConfig()
    try:
        assert abs(cfg.temper_c - 0.25) < 1e-9, "Kelly temper_c must be 0.25"
        assert abs(cfg.cvar_cap - CVAR_CAP) < 1e-9, "CVAR_CAP mismatch"
        assert abs(cfg.max_pos_pct - MAX_POS_PCT) < 1e-9, "MAX_POS_PCT mismatch"
        assert abs(meta_model.threshold - META_THRESHOLD) < 1e-9, "MetaModel threshold mismatch"
    except AssertionError as e:
        print("[CRITICAL CONFIG ERROR]", str(e))

_check_integrity()


# ============================================================
# Expected alpha / variance model (no hand-wave, deterministic)
# ============================================================

def _expected_alpha_and_var(
    strategy_name: str,
    trade_prob: float,
    entry_dte: int,
) -> Tuple[float, float]:
    """
    Map strategy + probability + tenor to expected edge and variance.

    - trade_prob is model-estimated win probability [0,1].
    - Uses conservative caps so sizing never explodes.
    """

    # Edge over 50/50
    edge = max(0.0, float(trade_prob) - 0.50)

    if edge <= 0.0:
        # No edge, no position (Kelly will zero this)
        return 0.0, 1e-6

    # Baseline per-strategy risk/return profile
    strategy_name = strategy_name or ""

    if strategy_name in ("Short Credit Vertical Spread", "Short Iron Condor"):
        # Premium-selling: high win-rate, limited loss, but tail risk.
        base_alpha_cap = 0.05     # Max 5% expected on allocated capital
        base_var = (0.025 ** 2) * 2.0
    elif strategy_name in ("Long Debit Vertical Spread", "Long Call", "Long Put"):
        # Defined-risk debit structures.
        base_alpha_cap = 0.06
        base_var = (0.035 ** 2) * 1.8
    elif strategy_name == "Directional Equity":
        base_alpha_cap = 0.03
        base_var = (0.02 ** 2) * 1.2
    else:
        # Unknown / exotic: penalize.
        base_alpha_cap = 0.02
        base_var = (0.04 ** 2) * 3.0

    # Time-to-expiry modifiers
    dte = max(1, int(entry_dte) if entry_dte is not None else 30)

    if dte <= 2:
        # 0DTE / 1DTE: violent gamma; explode variance, reduce effective edge.
        base_var *= 5.0
        base_alpha_cap *= 0.5
    elif dte <= 7:
        base_var *= 2.5
    elif dte <= 21:
        base_var *= 1.5

    expected_alpha = min(edge * base_alpha_cap, base_alpha_cap)
    alpha_var = max(base_var, 1e-6)

    return expected_alpha, alpha_var


# ============================================================
# Macro / regime assessment (hook point)
# ============================================================

def assess_macro_state(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Placeholder for regime logic. Keep behavior deterministic & explicit.

    You can extend using:
      - snapshot["vix"]
      - snapshot["correlation_index"]
      - snapshot["credit_spread"]
      - snapshot["liquidity_stress"]
    """
    # Basic stub: always Normal for now.
    return {"macro_regime": "Normal"}


# ============================================================
# Black-Litterman multiplier (optional)
# ============================================================

def _black_litterman_multiplier(snapshot: Dict[str, Any]) -> float:
    """
    Converts portfolio-level BL signal into a scalar [0.0, >1.0]
    that scales Kelly output.

    If BL not available, returns 1.0 (neutral).
    """
    if not HAS_BLACK_LITTERMAN:
        return 1.0

    # Expected keys (if wired): asset_returns, market_weights, views_P, views_Q
    try:
        asset_returns = np.array(snapshot["bl_asset_returns"])
        market_weights = np.array(snapshot["bl_market_weights"])
        P = np.array(snapshot["bl_P"])
        Q = np.array(snapshot["bl_Q"])
    except KeyError:
        # No BL inputs => neutral
        return 1.0

    try:
        er_bl, _ = black_litterman_weights(  # type: ignore[arg-type]
            asset_returns=asset_returns,
            market_weights=market_weights,
            views_P=P,
            views_Q=Q,
        )
    except Exception:
        return 1.0

    # Simple heuristic:
    # If BL expected returns strongly positive -> >1, negative -> <1.
    # Here we compress into [0.5, 1.5] as a safety band.
    tilt = float(np.mean(er_bl))
    if tilt >= 0.0:
        mult = 1.0 + min(0.5, tilt * 5.0)
    else:
        mult = 1.0 + max(-0.5, tilt * 5.0)

    return max(0.5, min(mult, 1.5))


# ============================================================
# Options metrics input
# ============================================================

def _build_options_metrics(snapshot: Dict[str, Any]) -> OptionsMetrics:
    """
    Build OptionsMetrics from snapshot.

    If you have full options surface & Greeks, populate from there.
    For now, uses explicit, reasonable defaults or snapshot overrides.
    """
    spread = float(snapshot.get("opt_bid_ask_spread_pct", 0.01))
    iv_rank = float(snapshot.get("opt_iv_rank", 0.50))
    delta = float(snapshot.get("opt_delta", 0.0))
    gamma = float(snapshot.get("opt_gamma", 0.0))
    theta = float(snapshot.get("opt_theta", 0.0))
    vega = float(snapshot.get("opt_vega", 0.0))

    return OptionsMetrics(
        bid_ask_spread_pct=spread,
        iv_rank=iv_rank,
        delta=delta,
        gamma=gamma,
        theta=theta,
        vega=vega,
    )


# ============================================================
# Core approve() – this is what everything calls
# ============================================================

def approve(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Primary ORACLE decision entrypoint.

    Expects snapshot approx like:
      {
        "price": float,
        "bias": float (-1..1),
        "confidence": float (0..1),
        "trade_prob": float (0..1),
        "dispersion": float,
        ... optional BL / options / regime fields ...
      }
    """

    decision = assess_macro_state(snapshot)
    macro_regime = decision.get("macro_regime", "Normal")

    risk = SMALL_ACCOUNT_RISK
    equity = float(risk.portfolio_equity)

    price = float(snapshot.get("price", 0.0) or 0.0)
    bias = float(snapshot.get("bias", 0.0) or 0.0)
    conf = float(snapshot.get("confidence", 0.0) or 0.0)
    prob = float(snapshot.get("trade_prob", 0.5) or 0.5)
    dispersion = float(snapshot.get("dispersion", 0.0) or 0.0)

    # ---- 1) Meta-model gating ----
    feats = np.array([bias, conf, prob, dispersion], dtype=float)
    if not meta_model.approve(feats):
        decision.update({
            "approve": False,
            "reason": "meta_model_reject",
            "heartbeat": time.time(),
        })
        return decision

    # ---- 2) Tiered strategy permissions ----
    allowed_strats = set(load_allowed_strategies(equity))

    # ---- 3) Build Lucid signal & metrics ----
    lucid_sig = LucidSignal(
        bias=bias,
        confidence=conf,
        trade_prob=prob,
    )

    metrics = _build_options_metrics(snapshot)
    current_0_1 = int(DTE_STATE.get("count", 0))

    # ---- 4) Run options gating (structure selection) ----
    rec: OptionTrade = options_gating_mechanism(
        signal=lucid_sig,
        metrics=metrics,
        current_equity=equity,
        current_0_1_dte_count=current_0_1,
    )

    # Enforce equity-tier permissions
    if rec.strategy not in allowed_strats and rec.strategy != "None":
        rec = OptionTrade(
            strategy="None",
            side="none",
            max_risk_dollars=0.0,
            expiry_date="",
            entry_dte=0,
            reason="strategy_not_allowed_for_equity_tier",
        )

    details = OptionsTradeDetails()

    # ---- 5) Expected alpha / variance ----
    strategy_name = rec.strategy if rec.strategy != "None" else "Directional Equity"
    entry_dte = int(getattr(rec, "entry_dte", 30) or 30)

    expected_alpha, alpha_var = _expected_alpha_and_var(
        strategy_name=strategy_name,
        trade_prob=prob,
        entry_dte=entry_dte,
    )

    # If gating returned "None", zero the edge so we either fall back or veto.
    if rec.strategy == "None":
        expected_alpha = 0.0

    # ---- 6) CVaR estimate (uses EVT tails) ----
    # In full deployment, feed actual P&L distribution samples.
    est_cvar = estimate_cvar([0.01, 0.015, 0.02, 0.03])

    # ---- 7) Black-Litterman multiplier ----
    bl_mult = _black_litterman_multiplier(snapshot)

    # ---- 8) Final allocation via tempered Kelly + CVaR + BL ----
    alloc_frac = final_size(
        expected_alpha=expected_alpha,
        alpha_var=alpha_var,
        est_cvar=est_cvar,
        bl_multiplier=bl_mult,
    )

    # Enforce global hard cap
    alloc_frac = float(max(0.0, min(alloc_frac, MAX_POS_PCT)))

    approved = False

    # ---- 9) Primary path: options structure ----
    if (
        rec.strategy != "None"
        and macro_regime != "Liquidity Fracture"
        and alloc_frac > 0.0
        and price > 0.0
    ):
        notional = equity * alloc_frac
        if notional >= price:
            contracts = max(1, int(notional / price))

            details.asset_type = "option"
            details.strategy = rec.strategy
            details.side = rec.side
            details.contracts_qty = contracts
            details.max_risk_dollars = min(rec.max_risk_dollars, notional)
            details.entry_price_px = price
            details.expiry_date = rec.expiry_date
            details.entry_dte = entry_dte

            approved = True

    # ---- 10) Fallback: directional equity if we have real edge ----
    if (not approved) and (prob >= 0.60) and (alloc_frac > 0.0) and (price > 0.0):
        notional = equity * alloc_frac
        shares = int(notional / price)
        if shares > 0:
            details.asset_type = "equity"
            details.strategy = "Directional Equity"
            details.side = "buy" if bias > 0 else "sell"
            details.contracts_qty = shares
            details.max_risk_dollars = risk.max_risk_per_trade
            details.entry_price_px = price
            details.expiry_date = ""
            details.entry_dte = 0

            approved = True

    # ---- 11) Compile decision ----
    decision.update({
        "approve": approved,
        "asset_type": details.asset_type,
        "strategy": details.strategy,
        "side": details.side,
        "qty": details.contracts_qty,
        "max_risk_dollars": details.max_risk_dollars,
        "allocation_fraction": alloc_frac,
        "expiry_date": details.expiry_date,
        "entry_dte": details.entry_dte,
        "entry_price_px": details.entry_price_px,
        "heartbeat": time.time(),
        "veto_reason": getattr(rec, "reason", "") if not approved else "",
    })

    # --- Update LucidPulse with the latest trade event ---
    pulse_update = lucid_pulse.register(
        confidence=conf,
        risk_dollars=details.max_risk_dollars or 0.0,
        expected_alpha=expected_alpha,
    )

    decision["lucid_pulse"] = pulse_update

    return decision


if __name__ == "__main__":
    print("ORACLE Engine initialized and ready.")
