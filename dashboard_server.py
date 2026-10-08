"""Flask dashboard for the persisted Bitcoin sentiment analyzer state."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template


BASE_DIR = Path(__file__).resolve().parent
VISUAL_STATE_FILE = Path(os.getenv("VISUAL_STATE_FILE", str(BASE_DIR / "visual_state.json")))
SIGNAL_HISTORY_FILE = Path(os.getenv("SIGNAL_HISTORY_FILE", str(BASE_DIR / "signal_history.json")))

app = Flask(__name__, template_folder="dashboard/templates", static_folder="dashboard/static")


def _read_json(path: Path, fallback: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
        return fallback


def _number(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _decimal(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _label(value: str) -> str:
    return value.replace("_", " ").title()


def _indicator_groups(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, dict):
        return []
    groups = []
    for group_key, group in raw.items():
        if not isinstance(group, dict):
            continue
        indicators = []
        for key, value in group.items():
            if key == "total":
                continue
            indicators.append({
                "key": key,
                "label": _label(key),
                "score": _number(value),
                "max_score": 2,
            })
        groups.append({
            "key": group_key,
            "label": _label(group_key),
            "total": _number(group.get("total")),
            "max_score": len(indicators) * 2,
            "indicators": indicators,
        })
    return groups


def _volume_breakdown(metrics: Any) -> dict[str, Any]:
    metrics = metrics if isinstance(metrics, dict) else {}
    volume = metrics.get("volume", {}) if isinstance(metrics.get("volume"), dict) else {}
    confirmation = volume.get("confirmation", {}) if isinstance(volume.get("confirmation"), dict) else {}
    profile = volume.get("profile", {}) if isinstance(volume.get("profile"), dict) else {}
    current = _decimal(profile.get("current_volume", confirmation.get("current_volume")))
    average = _decimal(profile.get("avg_volume", confirmation.get("average_volume")))
    return {
        "current_volume": current,
        "average_volume": average,
        "volume_ratio": round(current / average, 3) if average else None,
        "volume_trend": profile.get("volume_trend", confirmation.get("volume_trend", "Unavailable")),
        "volume_spike": bool(profile.get("volume_spike", False)),
        "volume_increasing": bool(profile.get("volume_increasing", False)),
        "obv": _decimal(profile.get("on_balance_volume")),
        "obv_trend": profile.get("obv_trend", "Neutral"),
        "confirmation": confirmation.get("confirming"),
        "confirmation_signal": _number(confirmation.get("signal", profile.get("signal"))),
        "profile_signal": _number(profile.get("signal")),
        "confidence": profile.get("confidence", "Unavailable"),
    }


def _historical_trend(history: list[dict[str, Any]]) -> dict[str, Any]:
    points = [point for point in history if point.get("score") is not None]
    scores = [_decimal(point.get("score")) for point in points]
    if not scores:
        return {"status": "No history", "points": 0, "direction": "Unavailable"}
    first = scores[0]
    last = scores[-1]
    delta = last - first
    average = sum(scores) / len(scores)
    variance = sum((score - average) ** 2 for score in scores) / len(scores)
    slope = delta / (len(scores) - 1) if len(scores) > 1 else 0.0
    direction = "Improving" if slope > 0.05 else "Deteriorating" if slope < -0.05 else "Flat"
    return {
        "status": "Ready" if len(scores) > 1 else "Seeded",
        "points": len(scores),
        "direction": direction,
        "first_score": first,
        "latest_score": last,
        "delta": round(delta, 2),
        "slope": round(slope, 3),
        "average_score": round(average, 2),
        "volatility": round(variance ** 0.5, 2),
        "high_score": max(scores),
        "low_score": min(scores),
        "positive_points": sum(score > 0 for score in scores),
        "negative_points": sum(score < 0 for score in scores),
    }


def dashboard_payload() -> dict[str, Any]:
    state = _read_json(VISUAL_STATE_FILE, {})
    if not isinstance(state, dict):
        state = {}
    history = state.get("history", [])
    if not isinstance(history, list):
        history = []
    history = [point for point in history if isinstance(point, dict)]
    signals = _read_json(SIGNAL_HISTORY_FILE, [])
    if not isinstance(signals, list):
        signals = []
    latest = None
    if state:
        latest = {
            "timestamp": state.get("timestamp"),
            "slot_utc": state.get("slot_utc"),
            "score": state.get("score"),
            "max_score": state.get("max_score", 24),
            "sentiment": state.get("sentiment", "CONSOLIDATION"),
            "regime": state.get("regime", "orange"),
            "indicators": _indicator_groups(state.get("indicators")),
            "metrics": state.get("metrics", {}),
            "market_context": state.get("market_context", {}),
            "signal": state.get("signal"),
        }
    return {
        "latest": latest,
        "history": history[-180:],
        "signals": signals[-20:],
        "analytics": {
            "volume_breakdown": _volume_breakdown(state.get("metrics", {})),
            "historical_trend": _historical_trend(history),
        },
        "meta": {
            "has_snapshot": latest is not None,
            "history_count": len(history),
            "refreshed_at": datetime.now(timezone.utc).isoformat(),
            "state_file": VISUAL_STATE_FILE.name,
        },
    }


@app.after_request
def add_headers(response):
    if response.mimetype == "application/json":
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/dashboard")
def api_dashboard():
    return jsonify(dashboard_payload())


@app.get("/health")
@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "bitcoin-sentiment-dashboard"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "3000")), debug=False)
