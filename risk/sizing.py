from dataclasses import dataclass
import math

@dataclass
class KellyConfig:
    temper_c: float = 0.25      # Kelly tempering factor
    cvar_cap: float = 0.0125    # Max fraction of equity allowed at CVaR level
    max_pos_pct: float = 0.10   # Absolute position cap per trade


def tempered_kelly(mu: float, var: float, cfg: KellyConfig) -> float:
    """
    Kelly sizing with tempering:
        f = c * (mu / var)
    Clamped to [0, cfg.max_pos_pct].
    """
    if var <= 0 or mu <= 0:
        return 0.0
    f = cfg.temper_c * (mu / var)
    return max(0.0, min(f, cfg.max_pos_pct))


def final_size(
    expected_alpha: float,
    alpha_var: float,
    est_cvar: float,
    bl_multiplier: float = 1.0,
    cfg: KellyConfig = KellyConfig()
) -> float:
    """
    Combines tempered Kelly fraction with Black-Litterman overlay
    and CVaR cap.
    """
    base = tempered_kelly(expected_alpha, alpha_var, cfg)
    weighted = base * max(0.0, bl_multiplier)

    if est_cvar <= 0:
        return max(0.0, weighted)

    # Limit fraction so f * CVaR <= cap
    capped = min(weighted, cfg.cvar_cap / est_cvar)
    return max(0.0, capped)
