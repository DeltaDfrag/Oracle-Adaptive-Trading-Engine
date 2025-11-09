import os

# === Root Path ===
ROOT = r"C:\Users\delta\OneDrive\Desktop\Oracle_Core"

# === Directory Tree ===
folders = [
    "core",
    "data",
    "research",
    "strategy",
    "risk",
    "execution",
    "ops",
    "rl"
]

# === Base Files (with header content) ===
base_files = {
    "core/smith.py": "# ORACLE_SMITH: Signal generation, meta-model gating, regime detection\n",
    "core/oracle.py": "# ORACLE_ENGINE: Risk sizing, Kelly/CVaR governance, Black-Litterman integration\n",
    "core/lucid_common.py": "# ORACLE_LUCID: Market feature extraction, snapshot creation, feed to SMITH\n",
    "core/circuit_breaker.py": "# ORACLE_CIRCUIT_BREAKER: Tail risk monitoring and kill switch logic\n",
    "core/hedger.py": "# ORACLE_HEDGER: Systemic hedge management (HMM state / SVI based)\n",
    "data/loaders.py": "# ORACLE_DATA_LOADERS: Fetch and cache market/option data\n",
    "data/quality.py": "# ORACLE_DATA_QUALITY: Schema checks, outlier clamps, timezone normalization\n",
    "data/feature_store.py": "# ORACLE_FEATURE_STORE: Rolling features, purging, embargo logic\n",
    "data/options_surface.py": "# ORACLE_OPTIONS_SURFACE: SABR fit, IV surface, risk-neutral density\n",
    "data/labels.py": "# ORACLE_LABELS: Triple-barrier and meta-label generation\n",
    "research/regime.py": "# ORACLE_REGIME: HMM / Bayesian CPD for market regime detection\n",
    "research/factors.py": "# ORACLE_FACTORS: PCA/ICA, Black-Litterman model\n",
    "research/pairs.py": "# ORACLE_PAIRS: Cointegration and mean-reversion analysis\n",
    "strategy/meta_model.py": "# ORACLE_META_MODEL: XGBoost/LGBM meta-label classifier\n",
    "strategy/signal_router.py": "# ORACLE_SIGNAL_ROUTER: Map regime to strategy type\n",
    "risk/sizing.py": "# ORACLE_SIZING: Tempered Kelly + CVaR + concentration penalty\n",
    "risk/tails_evt.py": "# ORACLE_TAILS_EVT: Extreme Value Theory POT tail modeling\n",
    "risk/constraints.py": "# ORACLE_CONSTRAINTS: Liquidity, exposure, compliance limits\n",
    "execution/sor.py": "# ORACLE_SOR: Smart Order Routing (VWAP/TWAP/POV)\n",
    "execution/slippage.py": "# ORACLE_SLIPPAGE: Impact and cost modeling\n",
    "execution/broker.py": "# ORACLE_BROKER: Broker API integration\n",
    "ops/backtest.py": "# ORACLE_BACKTEST: Walk-forward purged K-fold testing\n",
    "ops/monitor.py": "# ORACLE_MONITOR: Feature drift (PSI) and performance tracking\n",
    "ops/config.py": "# ORACLE_CONFIG: Central runtime configuration\n",
    "rl/cvar_ppo.py": "# ORACLE_RL_CVAR_PPO: Risk-sensitive PPO agent\n",
    "rl/offline_cql.py": "# ORACLE_RL_OFFLINE_CQL: Conservative Q-learning trainer\n",
    "rl/policy_decode.py": "# ORACLE_POLICY_DECODE: Action decoding with constraints\n",
}

def create_oracle_structure():
    print(f"\n📁 Creating Oracle System X structure under: {ROOT}\n")

    for folder in folders:
        dir_path = os.path.join(ROOT, folder)
        os.makedirs(dir_path, exist_ok=True)
        print(f"✅ Created folder: {dir_path}")

    for relative_path, content in base_files.items():
        file_path = os.path.join(ROOT, relative_path)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📄 Created file: {file_path}")

    print("\n🎯 Done! Oracle System X directory is fully set up.\n")

if __name__ == "__main__":
    create_oracle_structure()
