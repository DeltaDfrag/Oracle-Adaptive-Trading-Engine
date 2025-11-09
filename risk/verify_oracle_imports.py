# verify_oracle_imports.py
import importlib
import sys
import os
from pathlib import Path

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))

modules = [
    "core.oracle",
    "core.lucid_common",
    "risk.black_litterman",
    "risk.pnl_models",
    "risk.sizing",
    "risk.tails_evt",
    "strategy.meta_model",
    "strategy.options_gater",
    "ops.config",
]

print(f"🔍  Verifying modules from root: {root}\n")

for mod in modules:
    try:
        importlib.import_module(mod)
        print(f"✅  {mod} imported successfully")
    except Exception as e:
        print(f"❌  {mod} FAILED -> {e.__class__.__name__}: {e}")

print("\nSearch path:")
for p in sys.path:
    print("   ", p)
