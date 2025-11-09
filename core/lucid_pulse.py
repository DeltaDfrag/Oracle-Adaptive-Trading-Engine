import numpy as np
from dataclasses import dataclass, field
import time

@dataclass
class LucidPulse:
    """
    Tracks ORACLE's internal 'pulse' — a runtime stability and confidence signal.
    Combines recent trade confidence, realized risk, and expected alpha to measure systemic health.
    """
    recent_confidences: list = field(default_factory=list)
    recent_risks: list = field(default_factory=list)
    recent_alphas: list = field(default_factory=list)
    baseline_stability: float = 1.0
    decay: float = 0.92  # How quickly old data fades

    def register(self, confidence: float, risk_dollars: float, expected_alpha: float) -> dict:
        """Register a new trade event and return updated pulse metrics."""
        self.recent_confidences.append(confidence)
        self.recent_risks.append(risk_dollars)
        self.recent_alphas.append(expected_alpha)

        # Keep rolling history limited
        if len(self.recent_confidences) > 100:
            self.recent_confidences.pop(0)
            self.recent_risks.pop(0)
            self.recent_alphas.pop(0)

        return self.evaluate_pulse()

    def evaluate_pulse(self) -> dict:
        """Compute the current system stability metric."""
        if not self.recent_confidences:
            return {"stability": 1.0, "status": "🟢 Stable"}

        conf_avg = np.mean(self.recent_confidences)
        risk_avg = np.mean(self.recent_risks) or 1e-6
        alpha_avg = np.mean(self.recent_alphas)

        stability = max(0.0, min(1.5, (alpha_avg / risk_avg) * conf_avg * self.baseline_stability))
        status = "🟢 Stable" if stability >= 0.9 else "🟡 Deviating" if stability >= 0.6 else "🔴 Unstable"

        return {"stability": stability, "status": status, "timestamp": time.time()}

    def calibrate(self):
        """Slowly recalibrate baseline stability toward recent behavior."""
        if self.recent_confidences:
            recent_stab = np.mean([c for c in self.recent_confidences if c > 0])
            self.baseline_stability = (
                self.baseline_stability * self.decay + recent_stab * (1 - self.decay)
            )
        return self.baseline_stability
