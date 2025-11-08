
import numpy as np

def estimate_cvar(losses, alpha: float = 0.99) -> float:
    losses = np.asarray(losses, dtype=float)
    losses = losses[losses > 0]
    if len(losses) < 50:
        return 0.02
    thresh = np.quantile(losses, 0.95)
    tail = losses[losses > thresh]
    if len(tail) < 10:
        return max(float(thresh), 0.02)
    excess = tail - thresh
    mean_excess = float(excess.mean())
    var_excess = float(excess.var())
    if var_excess <= mean_excess**2:
        return max(float(thresh), 0.02)
    xi = 0.5 * (1 - (mean_excess**2 / var_excess))
    beta = mean_excess * (1 - xi)
    p_tail = 1 - 0.95
    prob = max((1 - alpha) / p_tail, 1e-6)
    if xi != 0:
        var_alpha = thresh + (beta / xi) * ((prob ** (-xi)) - 1)
    else:
        var_alpha = thresh - beta * np.log(prob)
    cvar = max(var_alpha, thresh, 0.01)
    return float(cvar)
