"""
ORACLE Adaptive Trading Engine — Risk Sizing
--------------------------------------------

Centralized position sizing logic for ORACLE.

Implements:
- Tempered Kelly sizing
- CVaR-based hard cap
- Concentration / HHI penalty hook
- Optional Riskfolio-Lib validation helper

This module is intentionally deterministic & auditable:
no model, no RL policy, no meta learner is allowed to
override these hard constraints.
"""

from dataclasses import dataclass
from typing import Optional, Dict
import numpy as np

# ------------------------------------------------------------
# Optional: Riskfolio-Lib for validation (not required to run)
# ------------------------------------------------------------
try:
    import riskfolio as rp  # type: ignore
    HAS_RISKFOLIO = True
except ImportError:
    HAS_RISKFOLIO = False


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

@dataclass
class KellyConfig:
    # Tempering factor: 0 < c <= 0.5 is conservative
    temper_c: float = 0.25

    # Hard per-trade CVaR cap (fraction of portfolio)
    cvar_cap: float = 0.0125  # 1.25%

    # Max fraction of portfolio per single position
    max_pos_pct: float = 0.10  # 10%

    # Max fraction after concentration penalty
    max_after_concentration: float = 0.06  # 6% default ceiling


# ------------------------------------------------------------
# Core Kelly / CVaR Logic
# ------------------------------------------------------------

def tempered_kelly(expected_alpha: float,
                   alpha_var: float,
                   cfg: KellyConfig) -> float:
    """
    Conservative Kelly fraction: f = c * mu / sigma^2

    expected_alpha: expected excess return per trade (in fraction, e.g. 0.01 = 1%)
    alpha_var: variance of that edge estimate
    """
    if alpha_var <= 0 or expected_alpha <= 0:
        return 0.0

    raw = cfg.temper_c * expected_alpha / alpha_var
    # Bound by max_pos_pct
    return float(max(0.0, min(raw, cfg.max_pos_pct)))


def cap_by_cvar(size_frac: float,
                est_cvar: float,
                cfg: KellyConfig) -> float:
    """
    Apply a hard cap based on estimated CVaR.

    size_frac: proposed Kelly fraction
    est_cvar: estimated CVaR_XX of the position (as fraction of equity)
    """
    if est_cvar is None or est_cvar <= 0:
        # If we don't know tail risk, be ultra conservative
        return min(size_frac, cfg.cvar_cap * 0.5)

    # Ensure: size_frac * est_cvar <= cvar_cap
    max_allowed = cfg.cvar_cap / est_cvar
    return float(max(0.0, min(size_frac, max_allowed)))


def apply_concentration_penalty(size_frac: float,
                                hhi: Optional[float],
                                cfg: KellyConfig) -> float:
    """
    Penalize size if portfolio is concentrated.

    hhi: Herfindahl-Hirschman index of current exposures (0-1+).
         Higher = more concentrated.
    """
    if hhi is None:
        return size_frac

    # Simple rule: if HHI is high, shrink aggressively
    # Example: hhi 0.10 (diverse) -> ~100%, hhi 0.25 -> 70%, hhi 0.50 -> 40%
    penalty = max(0.3, 1.2 - 1.6 * hhi)
    adjusted = size_frac * penalty
    return float(min(adjusted, cfg.max_after_concentration))


# ------------------------------------------------------------
# Public API: Final Sizing Function
# ------------------------------------------------------------

def final_size_frac(expected_alpha: float,
                    alpha_var: float,
                    est_cvar: Optional[float],
                    meta_p: Optional[float],
                    meta_uncertainty: Optional[float],
                    regime_risk_multiplier: float,
                    rl_sizing_mult: float,
                    hhi: Optional[float],
                    cfg: KellyConfig = KellyConfig()) -> Dict[str, float]:
    """
    Compute the final, constrained position size fraction.

    Inputs:
    - expected_alpha: model-estimated edge (fractional return)
    - alpha_var: variance of the edge estimate
    - est_cvar: estimated tail loss (CVaR) as fraction of equity for this trade
    - meta_p: meta-model probability that this trade is 'good'
    - meta_uncertainty: epistemic uncertainty (higher = less trust)
    - regime_risk_multiplier: (0-1+) scales risk per regime (e.g. 0.5 in 'volatile')
    - rl_sizing_mult: RL-proposed sizing factor (0-2, for example)
    - hhi: portfolio concentration metric (0-1+)
    - cfg: KellyConfig

    Returns dict with:
    - size_frac: final approved fraction of equity to allocate
    - base_kelly: raw tempered Kelly suggestion
    - cvar_limited: after CVaR cap
    - post_meta_regime_rl: after meta/uncertainty/regime/RL adjustments
    - post_concentration: after HHI penalty
    """

    # 1) Base tempered Kelly
    base_kelly = tempered_kelly(expected_alpha, alpha_var, cfg)

    # 2) CVaR hard cap
    cvar_limited = cap_by_cvar(base_kelly, est_cvar, cfg)

    # Early exit if no risk budget
    if cvar_limited <= 0:
        return {
            "size_frac": 0.0,
            "base_kelly": base_kelly,
            "cvar_limited": cvar_limited,
            "post_meta_regime_rl": 0.0,
            "post_concentration": 0.0,
        }

    # 3) Meta-model confidence adjustment
    if meta_p is not None:
        # Below 0.5 -> kill. 0.5-0.6 -> heavy shrink. 0.6+ -> allow.
        if meta_p < 0.50:
            meta_scaled = 0.0
        elif meta_p < 0.60:
            meta_scaled = cvar_limited * 0.25
        else:
            # Scale up between 0.6 and 0.8; above 0.8 = full
            meta_scaled = cvar_limited * min(1.0, (meta_p - 0.40) / 0.40)
    else:
        # If no meta-model, be conservative
        meta_scaled = cvar_limited * 0.5

    # 4) Uncertainty adjustment (epistemic)
    if meta_uncertainty is not None:
        # Higher uncertainty => shrink toward zero
        # e.g. unc=0.0 -> 100%, unc=0.5 -> 70%, unc=1.0 -> 40%
        unc_penalty = max(0.4, 1.0 - 0.6 * float(meta_uncertainty))
        meta_scaled *= unc_penalty

    # 5) Regime risk multiplier (e.g. 1.0 normal, 0.5 volatile, 0.25 crash)
    regime_scaled = meta_scaled * float(max(0.0, regime_risk_multiplier))

    # 6) RL sizing multiplier (soft — cannot break caps)
    # Bound RL suggestion between 0 and 2x, then apply but respect all prior caps
    rl_mult = float(min(max(rl_sizing_mult, 0.0), 2.0))
    rl_scaled = min(regime_scaled * rl_mult, cvar_limited, cfg.max_pos_pct)

    # 7) Concentration / HHI penalty
    final_size = apply_concentration_penalty(rl_scaled, hhi, cfg)

    return {
        "size_frac": float(max(0.0, final_size)),
        "base_kelly": float(base_kelly),
        "cvar_limited": float(cvar_limited),
        "post_meta_regime_rl": float(rl_scaled),
        "post_concentration": float(max(0.0, final_size)),
    }


# ------------------------------------------------------------
# Optional: Riskfolio-Lib sanity check
# ------------------------------------------------------------

def validate_with_riskfolio(returns_df) -> Dict[str, float]:
    """
    OPTIONAL helper: uses Riskfolio-Lib to compute a CVaR-optimized
    portfolio weight vector as a reference.

    Not required for runtime. Safe no-op if Riskfolio-Lib is missing.
    """
    if not HAS_RISKFOLIO:
        return {"used_riskfolio": 0.0}

    port = rp.Portfolio(returns=returns_df)
    port.assets_stats(method_mu="hist", method_cov="ledoit")
    weights = port.optimization(model="Classic", rm="CVaR", obj="Sharpe")
    # This is more for offline analysis / tuning:
    return {
        "used_riskfolio": 1.0,
        "max_weight": float(weights.max()),
        "min_weight": float(weights.min()),
    }


if __name__ == "__main__":
    # Simple smoke test
    cfg = KellyConfig()
    demo = final_size_frac(
        expected_alpha=0.01,
        alpha_var=0.0004,
        est_cvar=0.02,
        meta_p=0.65,
        meta_uncertainty=0.2,
        regime_risk_multiplier=0.8,
        rl_sizing_mult=1.1,
        hhi=0.15,
        cfg=cfg,
    )
    print(demo)