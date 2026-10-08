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


def _json_default(value):
    """Convert NumPy scalar values from analyzer modules to JSON primitives."""
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _snapshot_point(result, now, slot):
    """Build a display snapshot from the existing analyzer result."""
    return {
        "slot_utc": slot,
        "timestamp": result.get("timestamp", now.isoformat()),
        "asset": "BTC",
        "score": result["total_score"],
        "max_score": result["max_score"],
        "sentiment": result["sentiment"],
        "regime": _regime(result["sentiment"]),
        "indicators": result.get("indicators", {}),
        "metrics": result.get("metrics", {}),
        "signal": result.get("signal"),
        "changed": result.get("changed", False),
        "previous_sentiment": result.get("previous_sentiment"),
    }


def _replace_slot(history, point):
    """Replace the current four-hour point or append a new one."""
    next_history = []
    replaced = False
    for item in history:
        if isinstance(item, dict) and item.get("slot_utc") == point["slot_utc"]:
            next_history.append(point)
            replaced = True
        else:
            next_history.append(item)
    if not replaced:
        next_history.append(point)
    return next_history[-HISTORY_LIMIT:]


def update_visual_state(result):
    """Keep one BTC graph point per four-hour UTC slot and refresh current details."""
    now = datetime.now(timezone.utc)
    slot = _slot(now).isoformat()
    previous = _load()
    history = previous.get("history", [])
    if not isinstance(history, list):
        history = []
    updated_now = previous.get("slot_utc") != slot
    point = _snapshot_point(result, now, slot)
    history = _replace_slot(history, point)
    state = {**previous, **point, "history": history}
    temporary_file = f"{STATE_FILE}.tmp"
    with open(temporary_file, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, ensure_ascii=False, default=_json_default)
    os.replace(temporary_file, STATE_FILE)
    return {**state, "updated_now": updated_now}
