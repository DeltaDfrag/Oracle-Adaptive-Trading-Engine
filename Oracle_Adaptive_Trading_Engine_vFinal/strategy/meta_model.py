
import numpy as np

class MetaModel:
    def __init__(self, threshold: float = 0.60):
        self.threshold = threshold

    def predict_proba(self, features: np.ndarray) -> float:
        if features.size == 0:
            return 0.5
        z = float(np.tanh(features.mean()))
        p = 0.5 + 0.4 * z
        return max(0.05, min(0.95, p))

    def approve(self, features: np.ndarray) -> bool:
        return self.predict_proba(features) >= self.threshold
