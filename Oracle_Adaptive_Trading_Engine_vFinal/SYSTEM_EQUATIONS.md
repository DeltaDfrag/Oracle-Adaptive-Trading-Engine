
# ORACLE Engine System Equations — vFinal (2025-11-08)

1. Tempered Kelly:
   f_kelly = c * (mu / sigma^2), capped at MAX_POS_PCT.

2. Final size:
   base = f_kelly
   scaled = base * rl_mult
   diversified = scaled * (1 - HHI)
   f_final = min(diversified, CVAR_CAP / est_cvar)

3. CVaR:
   EVT-style POT over 95% threshold, 99% tail; est_cvar >= 1% conservative.

4. Meta-model:
   p_meta = predict_proba(features); require p_meta >= META_THRESHOLD.

5. Options gating:
   Encoded as rules in strategy/options_gater.py for spreads/condors.

6. Oracle:
   Combines meta veto, options gating, and f_final sizing
   to return an approved trade with allocation_fraction.
