"""Stable four-hour visual snapshot state for the Bitcoin analyzer."""
import json
import os
from datetime import datetime, timezone

STATE_FILE = os.getenv("VISUAL_STATE_FILE", "visual_state.json")
HISTORY_LIMIT = 180


def _slot(now):
    hour = (now.hour // 4) * 4
    return now.replace(hour=hour, minute=0, second=0, microsecond=0)


def _regime(sentiment):
    if sentiment in {"ULTRA BULLISH", "BULLISH"}:
        return "green"
    if sentiment in {"ULTRA BEARISH", "BEARISH"}:
        return "red"
    return "orange"


def _load():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as handle:
            value = json.load(handle)
            return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def update_visual_state(result):
    """Keep one BTC graph point per four-hour UTC slot."""
    now = datetime.now(timezone.utc)
    slot = _slot(now).isoformat()
    previous = _load()
    history = list(previous.get("history", []))
    updated_now = previous.get("slot_utc") != slot
    if updated_now:
        point = {
            "slot_utc": slot,
            "timestamp": now.isoformat(),
            "asset": "BTC",
            "score": result["total_score"],
            "max_score": result["max_score"],
            "sentiment": result["sentiment"],
            "regime": _regime(result["sentiment"]),
        }
        history = (history + [point])[-HISTORY_LIMIT:]
        state = {**point, "history": history}
        with open(STATE_FILE, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2)
    else:
        state = previous
    return {**state, "updated_now": updated_now}
