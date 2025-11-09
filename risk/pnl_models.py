"""
PnL Models and Option Pricing Framework
========================================

This module computes theoretical option prices, Greeks, and 
aggregated strategy P&L metrics for ORACLE’s adaptive trading engine.
It supports both single-leg pricing and multi-leg structures
(Condors, Verticals, etc.), enabling full risk attribution.

Author: DeltaDfrag (restored complete model)
"""

import math
from dataclasses import dataclass
from typing import Literal, Tuple, Dict

OptionType = Literal["call", "put"]


# ================================================================
# === Black–Scholes Core Functions ===
# ================================================================

def _norm_cdf(x: float) -> float:
    """Standard normal CDF."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    """Standard normal PDF."""
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)


def _d1_d2(S: float, K: float, T: float, r: float, q: float, iv: float) -> Tuple[float, float]:
    """Compute d1 and d2 parameters."""
    if T <= 0 or S <= 0 or K <= 0 or iv <= 0:
        return 0.0, 0.0

    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * iv * iv) * T) / (iv * sqrt_T)
    d2 = d1 - iv * sqrt_T
    return d1, d2


def bs_price(S: float, K: float, T: float, r: float, q: float, iv: float, typ: OptionType) -> float:
    """Black–Scholes price."""
    if T <= 0:
        return max(0.0, S - K) if typ == "call" else max(0.0, K - S)
    if S <= 0 or K <= 0 or iv <= 0:
        return 0.0

    d1, d2 = _d1_d2(S, K, T, r, q, iv)
    if typ == "call":
        return S * math.exp(-q * T) * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * _norm_cdf(-d2) - S * math.exp(-q * T) * _norm_cdf(-d1)


# ================================================================
# === Greeks Calculator (Per Leg) ===
# ================================================================

def bs_greeks(S: float, K: float, T: float, r: float, q: float, iv: float, typ: OptionType) -> Dict[str, float]:
    """Compute all standard Greeks (Delta, Gamma, Theta, Vega, Rho)."""
    if T <= 0 or S <= 0 or K <= 0 or iv <= 0:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}

    d1, d2 = _d1_d2(S, K, T, r, q, iv)
    pdf_d1 = _norm_pdf(d1)

    # --- Delta ---
    if typ == "call":
        delta = math.exp(-q * T) * _norm_cdf(d1)
    else:
        delta = math.exp(-q * T) * (_norm_cdf(d1) - 1.0)

    # --- Gamma ---
    gamma = math.exp(-q * T) * pdf_d1 / (S * iv * math.sqrt(T))

    # --- Theta (daily) ---
    if typ == "call":
        theta_annual = -(
            S * math.exp(-q * T) * pdf_d1 * iv / (2 * math.sqrt(T))
        ) - r * K * math.exp(-r * T) * _norm_cdf(d2) + q * S * math.exp(-q * T) * _norm_cdf(d1)
    else:
        theta_annual = -(
            S * math.exp(-q * T) * pdf_d1 * iv / (2 * math.sqrt(T))
        ) + r * K * math.exp(-r * T) * _norm_cdf(-d2) - q * S * math.exp(-q * T) * _norm_cdf(-d1)

    theta_daily = theta_annual / 365.0

    # --- Vega ---
    vega = S * math.exp(-q * T) * pdf_d1 * math.sqrt(T) / 100.0

    # --- Rho ---
    if typ == "call":
        rho = K * T * math.exp(-r * T) * _norm_cdf(d2) / 100.0
    else:
        rho = -K * T * math.exp(-r * T) * _norm_cdf(-d2) / 100.0

    return {
        "delta": delta,
        "gamma": gamma,
        "theta": theta_daily,
        "vega": vega,
        "rho": rho,
    }


# ================================================================
# === Strategy-Level Aggregation ===
# ================================================================

@dataclass
class OptionLeg:
    side: Literal[1, -1]  # +1 = long, -1 = short
    type: OptionType
    strike: float
    dte: int


def strategy_greeks(S: float, r: float, q: float, iv: float, legs: Tuple[OptionLeg, ...]) -> Dict[str, float]:
    """Aggregate Greeks across all legs in a multi-leg strategy."""
    total = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}

    for leg in legs:
        T = leg.dte / 365.0
        g = bs_greeks(S, leg.strike, T, r, q, iv, leg.type)
        for key in total:
            total[key] += leg.side * g[key]

    return total


# ================================================================
# === PnL Simulation Models ===
# ================================================================

def calculate_pnl(
    S_start: float,
    S_end: float,
    K: float,
    r: float,
    q: float,
    iv_start: float,
    iv_end: float,
    dte_start: int,
    dte_end: int,
    typ: OptionType,
    side: Literal[1, -1],
) -> float:
    """
    Simulate per-leg P&L across a small move in price and volatility.
    This gives ORACLE and Smith their ground-truth feedback.
    """

    # Normalize time to expiry
    T1 = max(dte_start, 1) / 365.0
    T2 = max(dte_end, 0) / 365.0

    # Compute start and end prices using Black–Scholes
    start_px = bs_price(S_start, K, T1, r, q, iv_start, typ)
    end_px = bs_price(S_end, K, T2, r, q, iv_end, typ)

    # Directional side multiplier (+1 = long, -1 = short)
    return side * (end_px - start_px)


def strategy_pnl(
    S_start: float,
    S_end: float,
    r: float,
    q: float,
    iv_start: float,
    iv_end: float,
    legs: Tuple[OptionLeg, ...],
) -> float:
    """Aggregate total P&L across all legs."""
    pnl = 0.0
    for leg in legs:
        pnl += calculate_pnl(
            S_start,
            S_end,
            leg.strike,
            r,
            q,
            iv_start,
            iv_end,
            leg.dte,
            max(leg.dte - 1, 0),
            leg.type,
            leg.side,
        )
    return pnl


# ================================================================
# === Portfolio Summary Metrics ===
# ================================================================

def compute_strategy_summary(
    S: float,
    r: float,
    q: float,
    iv: float,
    legs: Tuple[OptionLeg, ...],
    iv_shock: float = 0.02,
    price_shock: float = 0.02,
) -> Dict[str, float]:
    """
    Provides quick sensitivity analysis for a strategy:
      ΔPnL for ±2% move in underlying and ±2% change in IV.
    """
    pnl_up = strategy_pnl(S, S * (1 + price_shock), r, q, iv, iv + iv_shock, legs)
    pnl_down = strategy_pnl(S, S * (1 - price_shock), r, q, iv, iv - iv_shock, legs)
    base_greeks = strategy_greeks(S, r, q, iv, legs)

    return {
        "PnL_+2%": pnl_up,
        "PnL_-2%": pnl_down,
        "delta": base_greeks["delta"],
        "gamma": base_greeks["gamma"],
        "theta": base_greeks["theta"],
        "vega": base_greeks["vega"],
        "rho": base_greeks["rho"],
    }
