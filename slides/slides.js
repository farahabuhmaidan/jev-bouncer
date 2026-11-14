// Arrow keys / click to move; slide 6 numbers come live from the Doorman server (/api/metrics).

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

Promise.all([fetch("/api/metrics").then((r) => r.json()), fetch("/api/day").then((r) => r.json())])
  .then(([m, day]) => {
    const row = (name, j, l, fmt, lowerWins = false) => {
      const jw = j !== null && l !== null && (lowerWins ? j < l : j > l);
      const lw = j !== null && l !== null && (lowerWins ? l < j : l > j);
      return `<tr><td>${name}</td><td class="j ${jw ? "win" : ""}">${fmt(j)}</td><td class="l ${lw ? "win" : ""}">${fmt(l)}</td></tr>`;
    };
    document.getElementById("numbers").innerHTML = `<tr><th></th><th>Jev</th><th>LLM baseline</th></tr>` +
      row("Critical misses", m.jev.critical_misses, m.llm.critical_misses, String, true) +
      row("Interrupt precision", m.jev.precision, m.llm.precision, pct) +
      row("Cost per 1,000 events", m.jev.cost_per_1k, m.llm.cost_per_1k, usd, true) +
      row("Median latency per call", m.jev.p50, m.llm.p50, ms, true) +
      row("p95 latency per call", m.jev.p95, m.llm.p95, ms, true) +
      row("Accuracy (ask = wrong)", m.jev.accuracy, m.llm.accuracy, pct) +
      row("Accuracy, excluding asks", m.jev.accuracy_excl_asks, m.llm.accuracy_excl_asks, pct) +
      row("Accuracy, holdout", m.jev.holdout_accuracy, m.llm.holdout_accuracy, pct) +
      row("Asks", m.jev.asks, m.llm.asks, String, true);
    document.getElementById("numbers-meta").textContent =
      `typesafe/jev-1.14 vs anthropic/claude-sonnet-5.5 · n=${m.n} labelled events · run 2026-11-14` +
      (m.settings_changed ? " · settings changed in the app" : "");
  })
  .catch((err) => { document.getElementById("numbers-meta").textContent = `Start the app (make app) to load the numbers: ${err.message}`; });
