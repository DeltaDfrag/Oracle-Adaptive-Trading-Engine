
import time, math
from typing import Dict, Any
import numpy as np

from lucid_common import OptionsTradeDetails, compute_options_metrics
from ops.config import SMALL_ACCOUNT_RISK, META_THRESHOLD, DTE_STATE
from strategy.options_gater import LucidSignal, options_gating_mechanism
from strategy.meta_model import MetaModel
from risk.sizing import final_size
from risk.tails_evt import estimate_cvar

meta_model = MetaModel(threshold=META_THRESHOLD)

def assess_macro_state(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    return {"macro_regime": "Normal"}

def approve(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    decision = assess_macro_state(snapshot)
    risk = SMALL_ACCOUNT_RISK

    price = float(snapshot.get("price", 0.0) or 0.0)
    bias = float(snapshot.get("bias", 0.0))
    conf = float(snapshot.get("confidence", 0.0))
    prob = float(snapshot.get("trade_prob", 0.5))

    feats = np.array([bias, conf, prob, snapshot.get("dispersion", 0.0)], dtype=float)
    if not meta_model.approve(feats):
        decision.update({"approve": False, "reason": "meta_model_reject", "heartbeat": time.time()})
        return decision

    options_metrics = compute_options_metrics()
    lucid_sig = LucidSignal(bias=bias, confidence=conf, trade_prob=prob)
    current_0_1 = int(DTE_STATE.get("count", 0))

    rec = options_gating_mechanism(lucid_sig, options_metrics, risk.portfolio_equity, current_0_1)
    details = OptionsTradeDetails()

    edge = (prob - 0.5)
    expected_alpha = max(0.0, edge * 0.02)
    alpha_var = max(1e-6, (0.01 ** 2))

    est_cvar = estimate_cvar([0.01, 0.015, 0.02, 0.03])
    hhi = 0.30
    rl_mult = 1.0

    alloc_frac = final_size(expected_alpha, alpha_var, est_cvar, hhi=hhi, rl_mult=rl_mult)

    approved = False
    if rec.strategy != "None" and decision["macro_regime"] != "Liquidity Fracture":
        notional = risk.portfolio_equity * alloc_frac
        if notional >= max(price, 0.01):
            contracts = max(1, int(notional / max(price, 0.01)))
            details.asset_type = 'option'
            details.strategy = rec.strategy
            details.side = rec.side
            details.contracts_qty = contracts
            details.max_risk_dollars = rec.max_risk_dollars
            details.entry_price_px = price
            details.expiry_date = rec.expiry_date
            details.entry_dte = rec.entry_dte
            approved = True
    elif prob >= 0.60:
        notional = risk.portfolio_equity * alloc_frac
        shares = int(notional / max(price, 0.01))
        if shares > 0:
            details.asset_type = 'equity'
            details.strategy = 'Directional Equity'
            details.side = 'buy' if bias > 0 else 'sell'
            details.contracts_qty = shares
            details.max_risk_dollars = risk.max_risk_per_trade
            details.entry_price_px = price
            approved = True

    decision.update({
        "approve": approved,
        "asset_type": details.asset_type,
        "strategy": details.strategy,
        "side": details.side,
        "qty": details.contracts_qty,
        "max_risk_dollars": details.max_risk_dollars,
        "allocation_fraction": float(alloc_frac),
        "expiry_date": details.expiry_date,
        "entry_dte": details.entry_dte,
        "entry_price_px": details.entry_price_px,
        "heartbeat": time.time()
    })
    return decision
