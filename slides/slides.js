// Arrow keys / click to move; slide 6 numbers come from results.json via the same metrics code as the page.
import { DEFAULTS, replayDay } from "../web/policy.js";
import { computeMetrics } from "../web/metrics.js";

const slides = [...document.querySelectorAll(".slide")];
let i = Math.max(0, Math.min(slides.length - 1, Number(location.hash.slice(1)) - 1 || 0));
function show(n) {
  i = Math.max(0, Math.min(slides.length - 1, n));
  slides.forEach((s, k) => s.classList.toggle("active", k === i));
  document.getElementById("pager").textContent = `${i + 1} / ${slides.length}`;
  history.replaceState(null, "", `#${i + 1}`);
}
document.addEventListener("keydown", (e) => {
  if (["ArrowRight", "PageDown", " "].includes(e.key)) show(i + 1);
  if (["ArrowLeft", "PageUp"].includes(e.key)) show(i - 1);
});
show(i);

const video = document.getElementById("backup");
fetch(video.getAttribute("src"), { method: "HEAD" }).then((r) => { if (r.ok) video.hidden = false; }).catch(() => {});

const pct = (x) => (x === null ? "–" : `${Math.round(x * 100)}%`);
const ms = (x) => (x === null ? "–" : x >= 1000 ? `${(x / 1000).toFixed(1)} s` : `${x} ms`);
const usd = (x) => (x === null ? "–" : `$${x < 0.1 ? x.toFixed(3) : x.toFixed(2)}`);

Promise.all([fetch("../web/results.json").then((r) => r.json()), fetch("../web/prices.json").then((r) => r.json()).catch(() => ({}))])
  .then(([results, prices]) => {
    const { events, snapshot } = results.day;
    const decisions = replayDay(events, results.events, snapshot, DEFAULTS);
    const m = computeMetrics(events, decisions, results.events, prices, DEFAULTS);
    const holdout = events.filter((e) => e.holdout).length;
    const row = (name, j, l, fmt, lowerWins = false) => {
      const jw = j !== null && l !== null && (lowerWins ? j < l : j > l);
      const lw = j !== null && l !== null && (lowerWins ? l < j : l > j);
      return `<tr><td>${name}</td><td class="j ${jw ? "win" : ""}">${fmt(j)}</td><td class="l ${lw ? "win" : ""}">${fmt(l)}</td></tr>`;
    };
    document.getElementById("numbers").innerHTML = `<tr><th></th><th>Jev + rules</th><th>LLM only</th></tr>` +
      row("Accuracy (all)", m.jev.accuracy, m.llm.accuracy, pct) +
      row(`Accuracy (holdout, n=${holdout})`, m.jev.holdoutAccuracy, m.llm.holdoutAccuracy, pct) +
      row("Critical misses", m.jev.criticalMisses, m.llm.criticalMisses, String, true) +
      row("Asks (counted wrong)", m.jev.asks, 0, String, true) +
      row("Median latency per call", m.jev.p50, m.llm.p50, ms, true) +
      row("Cost per 1,000 events", m.jev.costPer1k, m.llm.costPer1k, usd, true);
    document.getElementById("numbers-meta").textContent =
      `${results.models.jev} vs ${results.models.llm} · n=${events.length} events · run ${results.generated_at.slice(0, 10)}`;
  })
  .catch((err) => { document.getElementById("numbers-meta").textContent = `Could not load results: ${err.message}`; });
