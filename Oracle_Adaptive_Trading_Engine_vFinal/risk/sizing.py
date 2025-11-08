
from dataclasses import dataclass
from ops.config import CVAR_CAP, MAX_POS_PCT

@dataclass
class KellyConfig:
    temper_c: float = 0.25
    cvar_cap: float = CVAR_CAP
    max_pos_pct: float = MAX_POS_PCT

def tempered_kelly(expected_alpha: float, alpha_var: float, cfg: KellyConfig) -> float:
    if alpha_var <= 0 or expected_alpha <= 0:
        return 0.0
    raw_fraction = cfg.temper_c * (expected_alpha / alpha_var)
    return max(0.0, min(raw_fraction, cfg.max_pos_pct))

def final_size(expected_alpha: float,
               alpha_var: float,
               est_cvar: float,
               hhi: float = 0.0,
               rl_mult: float = 1.0,
               cfg: KellyConfig = KellyConfig()) -> float:
    base_frac = tempered_kelly(expected_alpha, alpha_var, cfg)
    scaled_frac = base_frac * max(0.0, rl_mult)
    diversified_frac = scaled_frac * (1.0 - max(0.0, min(hhi, 1.0)))
    if est_cvar <= 0:
        return max(0.0, diversified_frac)
    cvar_limited = min(diversified_frac, cfg.cvar_cap / est_cvar)
    return max(0.0, cvar_limited)
