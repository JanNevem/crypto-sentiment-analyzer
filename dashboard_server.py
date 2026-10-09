"""Flask dashboard for the persisted Bitcoin sentiment analyzer state."""
from __future__ import annotations

import json
import math
import os
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, jsonify, render_template


BASE_DIR = Path(__file__).resolve().parent
VISUAL_STATE_FILE = Path(os.getenv("VISUAL_STATE_FILE", str(BASE_DIR / "visual_state.json")))
SIGNAL_HISTORY_FILE = Path(os.getenv("SIGNAL_HISTORY_FILE", str(BASE_DIR / "signal_history.json")))

app = Flask(__name__, template_folder="dashboard/templates", static_folder="dashboard/static")
BINANCE_KLINES_URL = "https://data-api.binance.vision/api/v3/klines"
CANDLE_CACHE: list[dict[str, Any]] = []


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


def _spot_guidance(latest: dict[str, Any] | None, candles: list[dict[str, Any]]) -> dict[str, Any]:
    """Translate sentiment evidence into non-leveraged spot decision support."""
    latest = latest if isinstance(latest, dict) else {}
    sentiment = str(latest.get("sentiment", "CONSOLIDATION")).upper()
    score = _decimal(latest.get("score"))
    current = _decimal(candles[-1].get("c")) if candles else 0.0
    recent = candles[-30:] if candles else []
    lows = sorted(_decimal(item.get("l")) for item in recent if _decimal(item.get("l")) > 0)
    highs = sorted((_decimal(item.get("h")) for item in recent if _decimal(item.get("h")) > 0))
    support = lows[max(0, int(len(lows) * 0.2) - 1)] if lows else 0.0
    resistance = highs[min(len(highs) - 1, int(len(highs) * 0.8))] if highs else 0.0
    metrics = latest.get("metrics", {}) if isinstance(latest.get("metrics"), dict) else {}
    trend = metrics.get("trend", {}) if isinstance(metrics.get("trend"), dict) else {}
    confirmation = candles[-1].get("confirmation", {}) if candles else {}
    ema20 = _decimal(confirmation.get("ema20"))
    ema50 = _decimal(confirmation.get("ema50"))
    if sentiment in {"ULTRA BULLISH", "BULLISH"}:
        posture, label = "ACCUMULATE_ON_PULLBACKS", "Accumulate on pullbacks"
        rationale = "The sentiment regime is constructive; favor gradual spot buying near support rather than chasing strength."
    elif sentiment in {"ULTRA BEARISH", "BEARISH"}:
        posture, label = "DEFENSIVE_WAIT", "Defensive / wait"
        rationale = "The sentiment regime is weak; avoid aggressive new spot buys and prioritize capital preservation."
    else:
        posture, label = "WAIT_OR_SCALE_SLOWLY", "Wait or scale slowly"
        rationale = "Evidence is mixed; wait for support and clearer confirmation, or use only small staggered spot purchases."
    zones = []
    if support:
        zones.append({"name": "Value / support zone", "low": round(support * 0.985, 2), "high": round(support * 1.015, 2), "basis": "20th percentile of the last 30 daily lows"})
    if ema20 and ema50:
        low, high = sorted((ema20, ema50))
        zones.append({"name": "Trend-retest zone", "low": round(low, 2), "high": round(high, 2), "basis": "Daily EMA20–EMA50 area"})
    return {
        "posture": posture,
        "label": label,
        "rationale": rationale,
        "current_price": current,
        "accumulation_zones": zones,
        "resistance_reference": round(resistance, 2) if resistance else None,
        "invalidation_reference": round(support * 0.97, 2) if support else None,
        "trend_direction": trend.get("direction", "Unknown"),
        "score_context": score,
        "disclaimer": "Spot-market context only — not a guaranteed entry, exit, or financial advice.",
    }


def _slot_from_ms(value: Any, daily: bool = False) -> str | None:
    try:
        stamp = datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
        return (stamp.replace(hour=0, minute=0, second=0, microsecond=0) if daily else
                stamp.replace(minute=0, second=0, microsecond=0)).isoformat()
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _sentiment_for_slot(slot: str | None, history: list[dict[str, Any]], latest: dict[str, Any] | None) -> str:
    if slot:
        exact = next((point for point in history if point.get("slot_utc") == slot), None)
        if exact and exact.get("sentiment"):
            return str(exact["sentiment"])
    if latest and latest.get("slot_utc") == slot and latest.get("sentiment"):
        return str(latest["sentiment"])
    return "UNRECORDED"


def _ema(values: list[float], period: int, index: int) -> float:
    window = values[:index + 1]
    if not window:
        return 0.0
    seed = sum(window[:period]) / min(period, len(window))
    result = seed
    multiplier = 2 / (period + 1)
    for value in window[min(period, len(window)):]:
        result = (value - result) * multiplier + result
    return result


def _daily_adx(candles: list[dict[str, Any]], index: int, period: int = 14) -> float | None:
    if index < period * 2:
        return None
    true_ranges, plus_dm, minus_dm = [], [], []
    for position in range(1, index + 1):
        high, low = _decimal(candles[position].get("h")), _decimal(candles[position].get("l"))
        previous_close = _decimal(candles[position - 1].get("c"))
        previous_high = _decimal(candles[position - 1].get("h"))
        previous_low = _decimal(candles[position - 1].get("l"))
        true_ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
        up_move, down_move = high - previous_high, previous_low - low
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)
    dx_values = []
    for end in range(period, len(true_ranges) + 1):
        tr = sum(true_ranges[end - period:end])
        plus = 100 * sum(plus_dm[end - period:end]) / tr if tr else 0.0
        minus = 100 * sum(minus_dm[end - period:end]) / tr if tr else 0.0
        dx_values.append(100 * abs(plus - minus) / (plus + minus) if plus + minus else 0.0)
    return sum(dx_values[-period:]) / min(period, len(dx_values)) if dx_values else None


def _daily_regimes(candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    closes = [_decimal(candle.get("c")) for candle in candles]
    regimes = []
    state = "UNCERTAIN"
    pending = None
    pending_count = 0
    for index, candle in enumerate(candles):
        ema20 = _ema(closes, 20, index)
        ema50 = _ema(closes, 50, index)
        prior_ema20 = _ema(closes, 20, index - 1) if index else ema20
        momentum = closes[index] / closes[index - 20] - 1 if index >= 20 and closes[index - 20] else 0.0
        adx = _daily_adx(candles, index)
        volumes = [_decimal(item.get("volume")) for item in candles]
        average_volume = sum(volumes[index - 20:index]) / 20 if index >= 20 else 0.0
        volume_ratio = volumes[index] / average_volume if average_volume else None
        volume_confirmed = volume_ratio is not None and volume_ratio >= 0.8
        bullish = index >= 50 and closes[index] > ema20 > ema50 and ema20 > prior_ema20 and momentum >= 0.05 and adx is not None and adx >= 20
        bearish = index >= 50 and closes[index] < ema20 < ema50 and ema20 < prior_ema20 and momentum <= -0.05 and adx is not None and adx >= 20
        candidate = "BULLISH" if bullish else "BEARISH" if bearish else "UNCERTAIN"
        if candidate == state:
            pending = None
            pending_count = 0
        elif candidate == pending:
            pending_count += 1
        else:
            pending = candidate
            pending_count = 1
        # Volume validates directional transitions, not every day inside an
        # already-established zone. Uncertain transitions need three days.
        required_days = 3 if candidate == "UNCERTAIN" else 2
        transition_allowed = candidate == "UNCERTAIN" or volume_confirmed
        if pending and pending_count >= required_days and transition_allowed:
            state = pending
            pending = None
            pending_count = 0
        regime = state
        regimes.append({
            **candle,
            "regime": regime,
            "regime_source": "DAILY_CONFIRMATION",
            "confirmation": {"ema20": round(ema20, 2), "ema50": round(ema50, 2), "adx": round(adx, 2) if adx is not None else None, "momentum_20d_pct": round(momentum * 100, 2), "volume_ratio": round(volume_ratio, 2) if volume_ratio is not None else None, "volume_confirmed": volume_confirmed, "volume_role": "transition_filter"},
        })
    return regimes


def _daily_candles() -> list[dict[str, Any]]:
    """Fetch completed BTCUSDT daily candles for a conservative confirmation view."""
    query = urlencode({"symbol": "BTCUSDT", "interval": "1d", "limit": 400})
    request = Request(f"{BINANCE_KLINES_URL}?{query}", headers={"User-Agent": "BTC-Sentiment-Dashboard/1.0"})
    global CANDLE_CACHE
    try:
        with urlopen(request, timeout=8) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, TypeError):
        return CANDLE_CACHE
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    candles = []
    for row in raw if isinstance(raw, list) else []:
        if not isinstance(row, list) or len(row) < 7:
            continue
        slot = _slot_from_ms(row[0], daily=True)
        try:
            candles.append({
                "x": int(row[0]),
                "o": _decimal(row[1]),
                "h": _decimal(row[2]),
                "l": _decimal(row[3]),
                "c": _decimal(row[4]),
                "volume": _decimal(row[7]) if len(row) > 7 else 0,
                "slot_utc": slot,
                "closed": _decimal(row[6]) <= now_ms,
            })
        except (TypeError, ValueError):
            continue
    closed = [candle for candle in candles if candle["closed"]]
    if closed:
        regimes = _daily_regimes(closed)
        # The daily classifier is intentionally slow and can preserve an old
        # trend through a sharp move. For the freshest completed candle, use
        # the analyzer snapshot when it is recent so the chart cannot show a
        # green zone while the cockpit says CONSOLIDATION or BEARISH.
        snapshot = _read_json(VISUAL_STATE_FILE, {})
        sentiment = str(snapshot.get("sentiment", "")).upper() if isinstance(snapshot, dict) else ""
        timestamp = snapshot.get("timestamp") if isinstance(snapshot, dict) else None
        try:
            snapshot_time = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            if snapshot_time.tzinfo is None:
                snapshot_time = snapshot_time.replace(tzinfo=timezone.utc)
            snapshot_age = (datetime.now(timezone.utc) - snapshot_time).total_seconds()
        except (TypeError, ValueError):
            snapshot_age = float("inf")
        if regimes and sentiment in {"BULLISH", "ULTRA BULLISH", "BEARISH", "ULTRA BEARISH", "CONSOLIDATION"} and snapshot_age <= 48 * 3600:
            mapped = "BULLISH" if "BULLISH" in sentiment else "BEARISH" if "BEARISH" in sentiment else "UNCERTAIN"
            regimes[-1] = {
                **regimes[-1],
                "regime": mapped,
                "regime_source": "ANALYZER_SNAPSHOT",
                "confirmation": {**regimes[-1].get("confirmation", {}), "analyzer_sentiment": sentiment, "snapshot_age_hours": round(snapshot_age / 3600, 1)},
            }
        CANDLE_CACHE = regimes
    return CANDLE_CACHE


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
            "data_quality": state.get("data_quality", {}),
            "market_context": state.get("market_context", {}),
            "signal": state.get("signal"),
        }
    candles = _daily_candles()
    return {
        "latest": latest,
        "history": history[-180:],
        "candles": candles,
        "signals": signals[-20:],
        "spot_guidance": _spot_guidance(latest, candles),
        "analytics": {
            "volume_breakdown": _volume_breakdown(state.get("metrics", {})),
            "historical_trend": _historical_trend(history),
        },
        "meta": {
            "has_snapshot": latest is not None,
            "history_count": len(history),
            "candle_count": len(candles),
            "candle_timeframe": "1d",
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
