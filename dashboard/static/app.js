(() => {
  let candleChart;
  let volumeChart;
  const $ = (selector) => document.querySelector(selector);
  const signed = (value) => value === null || value === undefined ? "—" : `${Number(value) > 0 ? "+" : ""}${value}`;
  const escapeHtml = (value) => String(value ?? "—").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[char]));
  const dateText = (value) => { if (!value) return "—"; const date = new Date(value); return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString(); };
  const shortDate = (value) => { if (!value) return "—"; const date = new Date(value); return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString([], {month:"short", day:"numeric", hour:"numeric"}); };
  const groupLabel = (value) => String(value ?? "").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

  function renderOverview(payload) {
    const latest = payload.latest;
    const meta = payload.meta || {};
    const hasScore = latest && latest.score !== null && latest.score !== undefined;
    const score = hasScore ? Number(latest.score) : 0;
    const maxScore = Number(latest?.max_score || 24);
    $("#score").textContent = hasScore ? signed(score) : "—";
    $("#score-max").textContent = `/ ${maxScore}`;
    $("#score-note").textContent = hasScore ? `${Math.abs(score)} points from neutral` : "Waiting for an analyzer snapshot.";
    const sentiment = latest?.sentiment || "No snapshot";
    const sentimentElement = $("#sentiment");
    sentimentElement.textContent = sentiment;
    sentimentElement.className = `sentiment ${sentiment.includes("BULLISH") ? "bullish" : sentiment.includes("BEARISH") ? "bearish" : "neutral"}`;
    $("#sentiment-note").textContent = latest ? `Source: ${meta.state_file || "visual_state.json"}` : "The dashboard reads visual_state.json.";
    $("#timestamp").textContent = dateText(latest?.timestamp);
    $("#slot").textContent = shortDate(latest?.slot_utc);
    $("#history-count").textContent = `${meta.history_count || 0} point${meta.history_count === 1 ? "" : "s"}`;
    $("#score-marker").style.left = `${50 + Math.max(-50, Math.min(50, (score / maxScore) * 50))}%`;
    $("#empty-state").hidden = Boolean(meta.has_snapshot);
  }

  const sentimentFill = (sentiment) => {
    const value = String(sentiment || "CONSOLIDATION");
    if (value.includes("BULLISH")) return "rgba(99,223,161,.24)";
    if (value.includes("BEARISH")) return "rgba(255,126,129,.24)";
    if (value === "UNRECORDED") return "rgba(106,119,130,.18)";
    return "rgba(255,180,84,.24)";
  };

  const sentimentBandsPlugin = {
    id: "sentimentBands",
    beforeDatasetsDraw(chartInstance) {
      const area = chartInstance.chartArea;
      const scale = chartInstance.scales.x;
      const points = chartInstance.data.datasets[0]?.data || [];
      if (!area || !scale || !points.length) return;
      const context = chartInstance.ctx;
      context.save();
      points.forEach((point, index) => {
        const start = Math.max(area.left, scale.getPixelForValue(point.x));
        const next = index + 1 < points.length ? scale.getPixelForValue(points[index + 1].x) : area.right;
        const end = Math.min(area.right, next);
        if (end > start) {
          context.fillStyle = sentimentFill(point.sentiment);
          context.fillRect(start, area.top, end - start, area.bottom - area.top);
        }
      });
      context.restore();
    }
  };

  function renderChart(candles, history) {
    const table = $("#history-table");
    table.innerHTML = history.slice().reverse().map((point) => `<tr><td>${escapeHtml(dateText(point.timestamp))}</td><td>${escapeHtml(signed(point.score))} / ${escapeHtml(point.max_score)}</td><td>${escapeHtml(point.sentiment)}</td></tr>`).join("");
    const ready = Array.isArray(candles) && candles.length > 0;
    $("#candle-empty").hidden = ready;
    const closedCount = candles.filter((candle) => candle.closed !== false).length;
    const activeCount = candles.length - closedCount;
    $("#chart-summary").textContent = ready ? `${closedCount} closed 4H candles${activeCount ? ` + ${activeCount} current formation` : ""}. Amber, green, and red bands are recorded sentiment; slate bands are unrecorded slots.` : "Closed 4H candle data is temporarily unavailable.";
    if (typeof Chart === "undefined" || !ready) return;
    if (candleChart) candleChart.destroy();
    candleChart = new Chart($("#candle-chart"), {
      type: "candlestick",
      data: { datasets: [{ label: "BTCUSDT / 4H", data: candles, backgroundColors: { up: "#2b3138", down: "#2b3138", unchanged: "#2b3138" }, borderColors: { up: "#2b3138", down: "#2b3138", unchanged: "#2b3138" }, barThickness: 3 }] },
      plugins: [sentimentBandsPlugin],
      options: { responsive: true, maintainAspectRatio: false, animation: false, interaction: { mode: "none" }, plugins: { legend: { display: false }, tooltip: { enabled: false } }, scales: { x: { type: "time", time: { unit: "day", displayFormats: { day: "MMM d" } }, ticks: { color: "#9aadb8", maxTicksLimit: 10 }, grid: { color: "rgba(45,65,79,.45)" } }, y: { ticks: { color: "#9aadb8", callback: (value) => `$${Number(value).toLocaleString()}` }, grid: { color: "rgba(45,65,79,.45)" } } } }
    });
  }

  function renderAnalytics(analytics) {
    const volume = analytics?.volume_breakdown || {};
    const trend = analytics?.historical_trend || {};
    const currentVolume = Number(volume.current_volume) || 0;
    const averageVolume = Number(volume.average_volume) || 0;
    const ratio = volume.volume_ratio === null || volume.volume_ratio === undefined ? "—" : `${Number(volume.volume_ratio).toFixed(2)}×`;
    $("#volume-confidence").textContent = volume.confidence ? `${volume.confidence} confidence` : "Awaiting metrics";
    $("#volume-stats").innerHTML = [["Current", currentVolume ? currentVolume.toLocaleString() : "—"], ["Average", averageVolume ? averageVolume.toLocaleString() : "—"], ["Ratio", ratio], ["Profile", volume.volume_trend || "Unavailable"], ["OBV", volume.obv ? volume.obv.toLocaleString() : "—"], ["Spike", volume.volume_spike ? "Detected" : "None"]].map(([label, value]) => `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("");
    $("#volume-empty").hidden = currentVolume > 0 || averageVolume > 0;
    if (volumeChart) volumeChart.destroy();
    if (typeof Chart !== "undefined" && (currentVolume > 0 || averageVolume > 0)) {
      volumeChart = new Chart($("#volume-chart"), { type: "bar", data: { labels: ["Current", "Average"], datasets: [{ label: "Quote volume", data: [currentVolume, averageVolume], backgroundColor: ["#56d9ff", "#425766"], borderRadius: 6 }] }, options: { responsive: true, maintainAspectRatio: false, animation: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: (context) => ` ${Number(context.raw).toLocaleString()}` } } }, scales: { x: { ticks: { color: "#9aadb8" }, grid: { display: false } }, y: { ticks: { color: "#9aadb8", callback: (value) => Number(value).toLocaleString() }, grid: { color: "rgba(45,65,79,.45)" } } } } });
    }
    const points = Number(trend.points) || 0;
    $("#trend-status").textContent = trend.status ? `${trend.status} / ${points} point${points === 1 ? "" : "s"}` : "Awaiting history";
    $("#trend-summary").textContent = points > 1 ? `${trend.direction} trend; ${signed(trend.delta)} points from first to latest, with ${trend.volatility} points of volatility.` : "Add another four-hour snapshot to calculate direction and volatility.";
    $("#trend-stats").innerHTML = [["Direction", trend.direction || "—"], ["Average", signed(trend.average_score)], ["High", signed(trend.high_score)], ["Low", signed(trend.low_score)], ["Positive", trend.positive_points ?? "—"], ["Negative", trend.negative_points ?? "—"]].map(([label, value]) => `<div class="trend-stat"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("");
  }

  function renderIndicators(groups) {
    const container = $("#indicator-groups");
    const count = groups.reduce((total, group) => total + (group.indicators || []).length, 0);
    $("#indicator-count").textContent = `${count} feed${count === 1 ? "" : "s"}`;
    if (!groups.length) { container.innerHTML = '<p class="empty">Indicator details appear when the analyzer writes them.</p>'; return; }
    container.innerHTML = groups.map((group) => `<section class="indicator-group"><div class="indicator-group-head"><h3>${escapeHtml(group.label)}</h3><span class="muted">${escapeHtml(signed(group.total))} / ${escapeHtml(group.max_score)}</span></div><div class="indicator-list">${(group.indicators || []).map((indicator) => { const score = Number(indicator.score) || 0; const kind = score > 0 ? "pos" : score < 0 ? "neg" : "zero"; return `<div><div class="indicator-line"><span class="indicator-label">${escapeHtml(indicator.label)}</span><span class="indicator-score ${kind}">${escapeHtml(signed(score))}</span></div><div class="bar ${kind}"><span style="width:${Math.max(4, Math.abs(score) / 2 * 100)}%"></span></div></div>`; }).join("")}</div></section>`).join("");
  }

  function renderSignals(signals) {
    const rows = $("#signal-table");
    rows.innerHTML = signals.slice().reverse().map((signal) => `<tr><td>${escapeHtml(dateText(signal.timestamp))}</td><td>${escapeHtml(signal.type)}</td><td>${escapeHtml(signal.direction)}</td></tr>`).join("");
    $("#signal-empty").hidden = signals.length > 0;
  }

  async function refresh() {
    try {
      const response = await fetch(`/api/dashboard?ts=${Date.now()}`, {cache: "no-store"});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      renderOverview(payload); renderChart(payload.candles || [], payload.history || []); renderAnalytics(payload.analytics || {}); renderIndicators(payload.latest?.indicators || []); renderSignals(payload.signals || []);
      $("#connection-status").textContent = "Live"; $(".live-dot").className = "live-dot live"; $("#data-status").textContent = `Loaded ${payload.meta.history_count || 0} persisted point${payload.meta.history_count === 1 ? "" : "s"}`; $("#updated").textContent = `Updated ${dateText(payload.meta.refreshed_at)}`;
    } catch (error) { $("#connection-status").textContent = "Unavailable"; $(".live-dot").className = "live-dot error"; $("#data-status").textContent = `Dashboard error: ${error.message}`; }
  }

  $("#refresh-now").addEventListener("click", refresh);
  refresh();
  window.setInterval(refresh, 15 * 60 * 1000);
})();
