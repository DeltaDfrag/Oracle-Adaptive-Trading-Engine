"""
ORACLE Adaptive Trading Engine — LUCID Auditor (Character Mode)
Reads system state and generates human or voice reports in various personalities.
"""

import os, json, datetime, pandas as pd, random

class LucidAuditor:
    def __init__(self, persona="jarvis"):
        self.persona = persona
        self.profiles = self._load_profiles()

    def _load_profiles(self):
        path = "./ops/personality_profiles.json"
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {"jarvis": {"greeting": "Systems online."}}

    def _style_line(self, text):
        """Apply basic persona flavor."""
        if self.persona == "mcduck":
            coins = random.choice(["💰", "🏴‍☠️", "🪙", "💎"])
            return f"{coins} {text}"
        return text

    def gather_status(self):
        status = {}
        if os.path.exists("./ops/metrics/equity_curve.csv"):
            df = pd.read_csv("./ops/metrics/equity_curve.csv")
            eq = df["equity"]
            status["latest_equity"] = float(eq.iloc[-1])
            status["return_pct"] = 100*(eq.iloc[-1]/eq.iloc[0]-1)
        status["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return status

    def narrate(self):
        prof = self.profiles.get(self.persona, {})
        greet = prof.get("greeting", "System status:")
        tone = prof.get("tone", "")
        status = self.gather_status()
        eq = status.get("latest_equity", 0)
        ret = status.get("return_pct", 0)
        line = f"{greet}\nCurrent equity: ${eq:,.2f} ({ret:+.2f}% total).\nTime: {status['timestamp']}."
        if ret > 0:
            line += " Profits glimmer brighter than a vault of gold coins!"
        else:
            line += " A wee drawdown today, but the fortress holds."
        return self._style_line(line)

if __name__ == "__main__":
    mode = input("Choose persona (jarvis/mcduck): ").strip().lower() or "jarvis"
    agent = LucidAuditor(persona=mode)
    print(agent.narrate())
    import pyttsx3
engine = pyttsx3.init()
engine.say(agent.narrate())
engine.runAndWait()
