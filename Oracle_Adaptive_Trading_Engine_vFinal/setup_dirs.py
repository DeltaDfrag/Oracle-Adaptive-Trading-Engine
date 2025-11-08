
import os
for d in ["core", "risk", "strategy", "ops", "execution", "data"]:
    os.makedirs(d, exist_ok=True)
