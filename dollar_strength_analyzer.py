"""Broad U.S. dollar strength analysis using the Federal Reserve FRED series."""

import csv
import io
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests


class DollarStrengthAnalyzer:
    """Fetch and score the broad nominal dollar index for BTC sentiment."""

    FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTWEXBGS"
    SOURCE = "Federal Reserve FRED DTWEXBGS"

    def __init__(self, timeout: int = 10, lookback_days: int = 5):
        self.timeout = timeout
        self.lookback_days = max(1, lookback_days)

    def _fetch_observations(self) -> List[Dict[str, float]]:
        response = requests.get(self.FRED_CSV_URL, timeout=self.timeout)
        response.raise_for_status()

        observations = []
        reader = csv.DictReader(io.StringIO(response.text))
        for row in reader:
            value = row.get("DTWEXBGS")
            if not value or value == ".":
                continue
            try:
                observations.append({"date": row["observation_date"], "value": float(value)})
            except (KeyError, TypeError, ValueError):
                continue

        if len(observations) < 2:
            raise ValueError("FRED returned fewer than two usable dollar-index observations")
        return observations

    @staticmethod
    def _score(change_pct: float) -> int:
        """Map broad-dollar change to BTC sentiment; stronger USD is bearish for BTC."""
        if change_pct >= 1.0:
            return -2
        if change_pct >= 0.25:
            return -1
        if change_pct <= -1.0:
            return 2
        if change_pct <= -0.25:
            return 1
        return 0

    def get_dollar_strength(self) -> Dict:
        """Return value, daily/weekly change, freshness, trend, and BTC score."""
        try:
            observations = self._fetch_observations()
            latest = observations[-1]
            prior = observations[-2]
            lookback_index = max(0, len(observations) - 1 - self.lookback_days)
            lookback = observations[lookback_index]

            daily_change_pct = ((latest["value"] - prior["value"]) / prior["value"] * 100)
            lookback_change_pct = ((latest["value"] - lookback["value"]) / lookback["value"] * 100)
            score = self._score(lookback_change_pct)

            if score < 0:
                trend = "Strengthening"
            elif score > 0:
                trend = "Weakening"
            else:
                trend = "Stable"

            return {
                "available": True,
                "source": self.SOURCE,
                "value": round(latest["value"], 4),
                "observation_date": latest["date"],
                "daily_change_pct": round(daily_change_pct, 3),
                "lookback_days": self.lookback_days,
                "lookback_change_pct": round(lookback_change_pct, 3),
                "trend": trend,
                "score": score,
                "freshness": "business-day data",
            }
        except (requests.RequestException, ValueError, csv.Error) as exc:
            return {
                "available": False,
                "source": self.SOURCE,
                "value": None,
                "observation_date": None,
                "daily_change_pct": None,
                "lookback_days": self.lookback_days,
                "lookback_change_pct": None,
                "trend": "Unavailable",
                "score": 0,
                "freshness": "unavailable",
                "error": str(exc),
            }
