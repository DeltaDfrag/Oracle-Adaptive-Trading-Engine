"""
ORACLE Adaptive Trading Engine — Distributional Policy (CVaR-PPO Skeleton)
--------------------------------------------------------------------------

A light integration wrapper for Stable-Baselines3 PPO with hooks for
risk-sensitive (CVaR) reinforcement learning.  Works stand-alone as a
drop-in policy module until a full CVaR-PPO implementation is attached.

Key ideas:
- Learns a *distribution* of returns, not just the mean.
- Produces policy multipliers (risk appetite, sizing bias).
- Feeds final sizing back into risk/sizing.py (never overrides caps).
"""

import os
import numpy as np
from dataclasses import dataclass
from typing import Dict, Any

# stable-baselines3 PPO (requires: pip install stable-baselines3 torch)
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

@dataclass
class RLConfig:
    policy_type: str = "MlpPolicy"
    learning_rate: float = 3e-4
    gamma: float = 0.99
    ent_coef: float = 0.01
    cvar_alpha: float = 0.95        # quantile of downside risk to penalize
    train_timesteps: int = 100_000
    log_dir: str = "./logs/"
    model_path: str = "./models/oracle_cvar_ppo.zip"


# ------------------------------------------------------------
# DUMMY ENVIRONMENT (placeholder until full env connected)
# ------------------------------------------------------------

class OracleEnv:
    """
    Minimal placeholder environment.
    Replace observations/rewards with your own when ready.
    """

    def __init__(self):
        self.action_space = np.array([0.0])     # single scalar output
        self.observation_space = np.zeros(5)    # sample observation vector
        self.current_step = 0

    def reset(self):
        self.current_step = 0
        return np.random.randn(5)

    def step(self, action):
        # Dummy reward: noisy positive drift to test learning loop
        reward = np.random.normal(loc=0.01, scale=0.05)
        obs = np.random.randn(5)
        done = self.current_step > 199
        self.current_step += 1
        return obs, reward, done, {}


# ------------------------------------------------------------
# RL POLICY WRAPPER
# ------------------------------------------------------------

class DistributionalPolicy:
    """
    Lightweight interface for the PPO model.
    Handles training, inference, and safe multiplier generation.
    """

    def __init__(self, cfg: RLConfig = RLConfig()):
        self.cfg = cfg
        self.model = None

    # ---------- Training ----------
    def train(self, env_fn=None):
        """Train PPO on the provided environment function (or dummy)."""
        os.makedirs(self.cfg.log_dir, exist_ok=True)
        env = DummyVecEnv([env_fn or (lambda: OracleEnv())])

        self.model = PPO(
            self.cfg.policy_type,
            env,
            learning_rate=self.cfg.learning_rate,
            gamma=self.cfg.gamma,
            ent_coef=self.cfg.ent_coef,
            verbose=1,
            tensorboard_log=self.cfg.log_dir,
        )
        self.model.learn(total_timesteps=self.cfg.train_timesteps)
        self.model.save(self.cfg.model_path)
        return self.model

    # ---------- Inference ----------
    def load(self, path: str = None):
        """Load an already-trained model."""
        p = path or self.cfg.model_path
        if os.path.exists(p):
            self.model = PPO.load(p)
            return True
        return False

    def act(self, obs: np.ndarray) -> Dict[str, Any]:
        """
        Produce a risk-aware sizing suggestion.
        Output: dictionary with rl_sizing_mult and risk_aversion
        """
        if self.model is None:
            # Default neutral output
            return {"rl_sizing_mult": 1.0, "risk_aversion": 1.0}

        action, _ = self.model.predict(obs, deterministic=False)

        # Convert bounded action → useful multiplier range (0.5 – 1.5)
        mult = float(1.0 + 0.5 * np.tanh(action))
        risk_aversion = 1.0 / mult

        return {
            "rl_sizing_mult": mult,
            "risk_aversion": risk_aversion,
        }


if __name__ == "__main__":
    # Quick smoke-test
    cfg = RLConfig(train_timesteps=10_000)
    policy = DistributionalPolicy(cfg)
    policy.train()           # trains dummy environment
    obs = np.random.randn(5)
    out = policy.act(obs)
    print(out)