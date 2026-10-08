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
            "market_context": state.get("market_context", {}),
            "signal": state.get("signal"),
        }
    return {
        "latest": latest,
        "history": history[-180:],
        "signals": signals[-20:],
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
