(() => {
  let chart;
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

  function renderChart(history) {
    const labels = history.map((point) => shortDate(point.timestamp));
    const values = history.map((point) => Number(point.score) || 0);
    const table = $("#history-table");
    table.innerHTML = history.slice().reverse().map((point) => `<tr><td>${escapeHtml(dateText(point.timestamp))}</td><td>${escapeHtml(signed(point.score))} / ${escapeHtml(point.max_score)}</td><td>${escapeHtml(point.sentiment)}</td></tr>`).join("");
    $("#chart-empty").hidden = history.length > 0;
    $("#chart-summary").textContent = history.length ? `${history.length} persisted point${history.length === 1 ? "" : "s"}; latest score ${signed(values[values.length - 1])}.` : "Chart data will appear after the next analyzer cycle.";
    if (typeof Chart === "undefined") { $("#chart-summary").textContent = "Chart.js could not load; the accessible table below remains available."; return; }
    if (chart) chart.destroy();
    chart = new Chart($("#history-chart"), {
      type: "line",
      data: { labels, datasets: [{ label: "BTC sentiment score", data: values, borderColor: "#56d9ff", backgroundColor: "rgba(86,217,255,.13)", pointBackgroundColor: values.map((value) => value > 0 ? "#63dfa1" : value < 0 ? "#ff7e81" : "#ffb454"), pointBorderColor: "#0b1117", pointBorderWidth: 2, pointRadius: 5, tension: .25, fill: true }] },
      options: { responsive: true, maintainAspectRatio: false, animation: false, plugins: { legend: { labels: { color: "#f4f7f8" } }, tooltip: { callbacks: { label: (context) => ` Score: ${signed(context.raw)}` } } }, scales: { x: { ticks: { color: "#9aadb8", maxTicksLimit: 8 }, grid: { color: "rgba(45,65,79,.45)" } }, y: { suggestedMin: -24, suggestedMax: 24, ticks: { color: "#9aadb8", callback: (value) => signed(value) }, grid: { color: (context) => Number(context.tick.value) === 0 ? "#ffb454" : "rgba(45,65,79,.45)", lineDash: (context) => Number(context.tick.value) === 0 ? [5,5] : [] } } } }
    });
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
      renderOverview(payload); renderChart(payload.history || []); renderIndicators(payload.latest?.indicators || []); renderSignals(payload.signals || []);
      $("#connection-status").textContent = "Live"; $(".live-dot").className = "live-dot live"; $("#data-status").textContent = `Loaded ${payload.meta.history_count || 0} persisted point${payload.meta.history_count === 1 ? "" : "s"}`; $("#updated").textContent = `Updated ${dateText(payload.meta.refreshed_at)}`;
    } catch (error) { $("#connection-status").textContent = "Unavailable"; $(".live-dot").className = "live-dot error"; $("#data-status").textContent = `Dashboard error: ${error.message}`; }
  }

  $("#refresh-now").addEventListener("click", refresh);
  refresh();
  window.setInterval(refresh, 30000);
})();
