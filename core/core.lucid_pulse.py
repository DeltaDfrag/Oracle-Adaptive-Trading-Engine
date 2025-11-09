from core.lucid_pulse import LucidPulse

# Instantiate the pulse monitor
pulse = LucidPulse()

# Simulate three different trade events
samples = [
    {"confidence": 0.90, "risk_dollars": 500, "expected_alpha": 0.04},
    {"confidence": 0.75, "risk_dollars": 1200, "expected_alpha": 0.02},
    {"confidence": 0.55, "risk_dollars": 2500, "expected_alpha": -0.01},
]

print("\n--- LucidPulse Sanity Test ---")
for s in samples:
    out = pulse.register(**s)
    print(out)
print("\n ALIVE.\n")
