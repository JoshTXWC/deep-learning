# SPDX-License-Identifier: AGPL-3.0-or-later
"""Token/cost tracking with local budgets (advisory — not a billing hard stop)."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path


class UsageTracker:
    def __init__(self, store_path: Path, pricing_path: Path, cfg: dict):
        self.store_path = store_path
        self.pricing_path = pricing_path
        self.cfg = cfg
        self._lock = threading.Lock()
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self.store_path.is_file():
            try:
                return json.loads(self.store_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
        return {"events": [], "totals": {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}}

    def _save(self) -> None:
        self.store_path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def _pricing(self, model: str) -> dict:
        try:
            doc = json.loads(self.pricing_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"input_per_mtok": 1.0, "output_per_mtok": 4.0}
        models = doc.get("models") or {}
        return models.get(model) or models.get("default") or {
            "input_per_mtok": 1.0,
            "output_per_mtok": 4.0,
        }

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        p = self._pricing(model)
        return (input_tokens / 1_000_000) * float(p["input_per_mtok"]) + (
            output_tokens / 1_000_000
        ) * float(p["output_per_mtok"])

    def record(self, *, provider: str, model: str, input_tokens: int, output_tokens: int) -> dict:
        cost = self.estimate_cost(model, input_tokens, output_tokens)
        event = {
            "ts": time.time(),
            "day": time.strftime("%Y-%m-%d"),
            "month": time.strftime("%Y-%m"),
            "provider": provider,
            "model": model,
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "cost_usd": round(cost, 6),
        }
        with self._lock:
            self._data.setdefault("events", []).append(event)
            # keep last 5000 events
            self._data["events"] = self._data["events"][-5000:]
            t = self._data.setdefault(
                "totals", {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
            )
            t["input_tokens"] += int(input_tokens)
            t["output_tokens"] += int(output_tokens)
            t["cost_usd"] = round(float(t["cost_usd"]) + cost, 6)
            self._save()
        return event

    def _sum(self, key: str, value: str) -> float:
        return sum(
            float(e.get("cost_usd") or 0)
            for e in self._data.get("events") or []
            if e.get(key) == value
        )

    def snapshot(self) -> dict:
        day = time.strftime("%Y-%m-%d")
        month = time.strftime("%Y-%m")
        daily = self._sum("day", day)
        monthly = self._sum("month", month)
        daily_budget = float(self.cfg.get("daily_budget_usd") or 0)
        monthly_budget = float(self.cfg.get("monthly_budget_usd") or 0)
        warn_pct = float(self.cfg.get("budget_warn_pct") or 80) / 100.0
        warnings = []
        if daily_budget and daily >= daily_budget * warn_pct:
            warnings.append(f"Daily usage ${daily:.4f} reached {warn_pct*100:.0f}% of ${daily_budget}")
        if monthly_budget and monthly >= monthly_budget * warn_pct:
            warnings.append(
                f"Monthly usage ${monthly:.4f} reached {warn_pct*100:.0f}% of ${monthly_budget}"
            )
        return {
            "provider": self.cfg.get("provider"),
            "model": self.cfg.get("model"),
            "totals": self._data.get("totals"),
            "daily_cost_usd": round(daily, 6),
            "monthly_cost_usd": round(monthly, 6),
            "daily_budget_usd": daily_budget,
            "monthly_budget_usd": monthly_budget,
            "warnings": warnings,
            "note": (
                "Local budgets are advisory. Configure hard spend limits on your "
                "OpenAI project at platform.openai.com — local caps alone do not "
                "guarantee protection from API charges."
            ),
        }

    def allow_request(self) -> tuple[bool, str]:
        snap = self.snapshot()
        if snap["daily_budget_usd"] and snap["daily_cost_usd"] >= snap["daily_budget_usd"]:
            return False, "Local daily budget reached. Raise daily_budget_usd or wait."
        if snap["monthly_budget_usd"] and snap["monthly_cost_usd"] >= snap["monthly_budget_usd"]:
            return False, "Local monthly budget reached. Raise monthly_budget_usd or wait."
        return True, ""
