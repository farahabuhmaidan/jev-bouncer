// The demo page (design/07-ui.md). It only replays: Jev's answers and the LLM text come from
// results.json; routing (policy.js) and the numbers (metrics.js) are computed here, live.
import { DEFAULTS, replayDay, effectiveSettings } from "./policy.js";
import { computeMetrics } from "./metrics.js";

const DAY_START = 8 * 60, DAY_END = 20 * 60;
const STORE = "bouncer.settings.v1";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const toMin = (hhmm) => { const [h, m] = hhmm.split(":").map(Number); return h * 60 + m; };
const toHHMM = (min) => `${String(Math.floor(min / 60)).padStart(2, "0")}:${String(Math.floor(min % 60)).padStart(2, "0")}`;
const pct = (x) => (x === null || x === undefined ? "–" : `${Math.round(x * 100)}%`);

const ui = {
  clock: DAY_START, playing: false, speed: 1, selected: null, senderView: false,
  settings: loadSettings(), decisions: new Map(),
  askChoices: new Map(), // eventId -> action Sanad clicked (display only)
  asked: new Set(), rerouted: new Set(), digestShown: false,
};
let data;

function loadSettings() {
  try { return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(STORE) || "{}") }; } catch { return { ...DEFAULTS }; }
}
function saveSettings() {
  try { localStorage.setItem(STORE, JSON.stringify(ui.settings)); } catch { /* private mode: keep in memory */ }
}

async function load() {
  const get = (url) => fetch(url).then((r) => { if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`); return r.json(); });
  const [results, prices] = await Promise.all([get("results.json"), get("prices.json").catch(() => ({}))]);
  data = { results, prices, events: results.day.events, snapshot: results.day.snapshot, byId: {} };
  for (const e of data.events) data.byId[e.id] = e;
  data.moments = [];
  for (const e of [...data.events].sort((a, b) => a.time.localeCompare(b.time))) {
    if (e.demo_moment && !data.moments.some((m) => m.name === e.demo_moment)) data.moments.push({ name: e.demo_moment, at: toMin(e.time) });
  }
}

const person = (key) => data.snapshot.people[key];
const senderName = (e) => (e.type === "ci_failure" ? "CI · " + e.test_name : person(e.sender)?.name ?? e.sender.replace(/^unknown:/, ""));
const isPerson = (e) => e.type === "message" && person(e.sender) && !person(e.sender).is_bot;
const visible = () => data.events.filter((e) => toMin(e.time) <= ui.clock).sort((a, b) => b.time.localeCompare(a.time) || b.id.localeCompare(a.id));
const res = (id) => data.results.events[id];
const shownAction = (id) => ui.askChoices.get(id) ?? ui.decisions.get(id)?.action;
const evening = () => ui.clock >= toMin(effectiveSettings(ui.settings).eveningStart);

function reroute() {
  ui.decisions = replayDay(data.events, data.results.events, data.snapshot, ui.settings);
  render();
}

// ---------- rendering ----------
function chip(d, id) {
  const action = shownAction(id) ?? "error";
  const text = action === "drop" && d?.label === "rerun silently" ? "rerun silently" : action;
  const icon = action === "interrupt" ? "🔔 " : "";
  return `<span class="chip ${action}">${icon}${esc(text)}</span>`;
}

function urgencyBadge(id) {
  const u = res(id)?.jev?.answers?.urgency;
  return u && typeof u.score === "number" ? `<span class="urg" title="Urgency (display only)">U${Math.round(u.score) + 1}</span>` : "";
}

function renderFeed() {
  const list = visible();
  if (ui.senderView) return renderSenderView(list);
  $("feed-title").textContent = "Event feed";
  $("feed").innerHTML = list.map((e) => {
    const d = ui.decisions.get(e.id), r = res(e.id);
    const text = e.type === "ci_failure" ? `${e.branch}: ${e.commit_message ?? ""}` : e.text;
    const label = d?.label && d.label !== "rerun silently" ? `<span class="tag">${esc(d.label)}</span>` : "";
    const asked = ui.askChoices.has(e.id) ? `<span class="tag">you chose this (Jev was unsure)</span>` : "";
    const reply = d?.action === "batch" && isPerson(e) && r?.auto_reply ? `<div class="reply">↩ ${esc(r.auto_reply)}</div>` : "";
    return `<li class="item ${ui.selected === e.id ? "selected" : ""}" data-id="${e.id}">
      <div class="top"><span class="time">${e.time}</span><span class="who">${esc(senderName(e))}</span>${urgencyBadge(e.id)}</div>
      <div class="text">${esc(text)}</div>
      <div class="meta">${chip(d, e.id)}${label}${asked}</div>${reply}</li>`;
  }).join("") || `<li class="muted">Nothing yet. Press ▶ or ⏭.</li>`;
}

function renderSenderView(list) {
  $("feed-title").textContent = "Sender view: what people see back";
  const held = list.filter((e) => isPerson(e) && ui.decisions.get(e.id)?.action === "batch");
  $("feed").innerHTML = held.map((e) => {
    const done = ui.rerouted.has(e.id);
    return `<li class="item" data-id="${e.id}">
      <div class="top"><span class="time">${e.time}</span><span class="who">${esc(senderName(e))} sent:</span></div>
      <div class="text">${esc(e.text)}</div>
      <div class="reply">Auto-reply: ${esc(res(e.id)?.auto_reply ?? "(no reply generated)")}</div>
      ${done ? `<span class="tag">→ sent to Sanad's phone</span>` : `<button class="urgent-btn" data-urgent="${e.id}">truly urgent</button>`}
    </li>`;
  }).join("") || `<li class="muted">No one is waiting on Sanad yet.</li>`;
}

function bar(q, p, used, s) {
  const cls = p >= s.yesAt ? "yes" : p > s.noAt ? "unsure" : "";
  return `<div class="q ${used ? "used" : ""}">${esc(q)}</div><div class="track"><div class="fill ${cls}" style="width:${(p * 100).toFixed(0)}%"></div></div><div class="val">${p.toFixed(2)}</div>`;
}

function renderWhy() {
  const id = ui.selected;
  if (!id) return;
  const e = data.byId[id], r = res(id), d = ui.decisions.get(id), s = effectiveSettings(ui.settings);
  if (!r) { $("why").innerHTML = `<p class="muted">No result for ${esc(id)}.</p>`; return; }
  const used = new Set((d?.reasons ?? []).map((x) => x.q));
  const answers = r.jev?.answers ?? {};
  let bars = "";
  for (const [q, v] of Object.entries(answers)) {
    if (typeof v === "number") bars += bar(q, v, used.has(q), s);
    else if (q === "failure_type") for (const [opt, p] of Object.entries(v)) bars += bar(`failure: ${opt}`, p, used.has(q), s);
  }
  const rule = d?.rule === undefined ? "–" : typeof d.rule === "number" ? `message row ${d.rule}` : d.rule;
  const base = r.baseline?.error ? `<span class="chip error">error</span> ${esc(r.baseline.error)}`
    : `<span class="chip ${esc(r.baseline?.action)}">${esc(r.baseline?.action ?? "–")}</span> <span class="muted">${esc(r.baseline?.reason ?? "")}</span>`;
  const ci = r.ci_explanation ? `<div class="explain"><b>LLM explanation</b><br>${esc(r.ci_explanation.likely_cause)}
      ${(r.ci_explanation.suspicious_lines || []).map((l) => `<br><code>${esc(l)}</code>`).join("")}<br><i>Fix:</i> ${esc(r.ci_explanation.suggested_fix)}</div>` : "";
  $("why").innerHTML = `
    <dl class="facts">
      <dt>Bouncer did</dt><dd>${chip(d, id)} ${esc(d?.label ?? "")}</dd>
      <dt>Rule fired</dt><dd>${esc(rule)}${d?.usesBudget ? " · used 1 interrupt" : ""}${d?.bar ? ` · bar ${d.bar.toFixed(2)}` : ""}</dd>
      <dt>LLM-only said</dt><dd>${base}</dd>
      <dt>Label</dt><dd><span class="chip ${e.label?.action}">${esc(e.label?.action ?? "–")}</span>${e.holdout ? ' <span class="tag">holdout</span>' : ""}</dd>
    </dl>
    <h2 style="margin-top:16px">Jev's answers ${r.jev?.latency_ms ? `<span class="muted">· ${r.jev.latency_ms} ms</span>` : ""}</h2>
    ${r.jev?.error ? `<p><span class="chip error">error</span> ${esc(r.jev.error)}</p>` : `<div class="bars">${bars}</div>`}
    ${ci}
    <h2 style="margin-top:16px">State sent to Jev</h2>
    <pre>${esc(JSON.stringify(r.state, null, 2))}</pre>`;
}

function renderPhoneClock() {
  $("phone-time").textContent = toHHMM(ui.clock);
  $("phone-mode").textContent = evening() ? "🌙 evening" : "";
  $("phone-frame").classList.toggle("evening", evening());
}

function renderPhone() {
  renderPhoneClock();
  const items = visible().filter((e) => shownAction(e.id) === "interrupt" || ui.rerouted.has(e.id));
  $("phone").innerHTML = items.map((e) => {
    const r = res(e.id), body = e.type === "ci_failure" ? `${e.test_name} failed on ${e.branch}` : e.text;
    const why = r?.ci_explanation && shownAction(e.id) === "interrupt" ? `<div class="x">Likely cause: ${esc(r.ci_explanation.likely_cause)}</div>` : "";
    const tag = ui.rerouted.has(e.id) ? `<div class="x">Sender tapped "truly urgent"</div>` : "";
    return `<li class="notif ${ui.rerouted.has(e.id) ? "rerouted" : ""}" data-id="${e.id}"><div class="h"><span>${esc(senderName(e))}</span><span>${e.time}</span></div>
      <div class="b">${esc(body).slice(0, 140)}</div>${why}${tag}</li>`;
  }).join("") || `<li class="muted small">Quiet. Nothing has needed Sanad yet.</li>`;
}

function renderHeader() {
  $("clock").textContent = toHHMM(ui.clock);
  $("clock").classList.toggle("evening", evening());
  $("speed").textContent = `${ui.speed}x`;
  $("play").classList.toggle("on", ui.playing);
  const s = effectiveSettings(ui.settings);
  const used = visible().filter((e) => ui.decisions.get(e.id)?.usesBudget).length;
  $("budget").innerHTML = `<span class="label">interrupts</span>` +
    Array.from({ length: s.budget }, (_, i) => `<span class="dot ${i < s.budget - used ? "left" : ""}"></span>`).join("");
}

function renderMetrics() {
  const m = computeMetrics(data.events, ui.decisions, data.results.events, data.prices, ui.settings);
  const pair = (j, l) => `<span class="j">${j}</span> <span class="l">/ ${l}</span>`;
  const money = (x) => (x === null ? "–" : x < 0.1 ? `$${x.toFixed(3)}` : `$${x.toFixed(2)}`);
  const ms = (x) => (x === null ? "–" : x >= 1000 ? `${(x / 1000).toFixed(1)}s` : `${x}ms`);
  const cell = (k, v) => `<div class="metric"><div class="k">${k}</div><div class="v">${v}</div></div>`;
  $("metrics").innerHTML = `<div class="legend"><b style="color:var(--ok)">Jev + rules</b> / LLM-only<br>${data.events.length} events, full day</div>` +
    cell("accuracy", pair(pct(m.jev.accuracy), pct(m.llm.accuracy))) +
    cell("holdout", pair(pct(m.jev.holdoutAccuracy), pct(m.llm.holdoutAccuracy))) +
    cell("critical misses", pair(m.jev.criticalMisses, m.llm.criticalMisses)) +
    cell("asks", `<span class="j">${m.jev.asks}</span>`) +
    cell("errors", pair(m.jev.errors, m.llm.errors)) +
    cell("p50 latency", pair(ms(m.jev.p50), ms(m.llm.p50))) +
    cell("cost / 1k events", pair(money(m.jev.costPer1k), money(m.llm.costPer1k))) +
    (m.settingsChanged ? `<div class="note">settings changed: labels assume defaults</div>` : "");
}

function render() {
  renderHeader(); renderFeed(); renderPhone(); renderWhy(); renderMetrics();
}

// ---------- settings ----------
function renderSettings() {
  const s = ui.settings;
  const range = (k, label, min, max, step) => `<label>${label}<input type="range" name="${k}" min="${min}" max="${max}" step="${step}" value="${s[k]}"><span class="val">${s[k]}</span></label>`;
  const check = (k, label) => `<label>${label}<input type="checkbox" name="${k}" ${s[k] ? "checked" : ""}></label>`;
  const people = Object.entries(data.snapshot.people).filter(([, p]) => !p.is_bot && p.relationship !== "self");
  $("settings-form").innerHTML = `
    <fieldset><legend>How sure is "sure"</legend>
      ${range("yesAt", "yes at ≥", 0.5, 0.95, 0.05)}${range("noAt", "no at ≤", 0.05, 0.5, 0.05)}</fieldset>
    <fieldset><legend>Interrupts</legend>
      ${range("interruptBar", "interrupt bar", 0.5, 0.95, 0.05)}${check("risingBar", "bar rises as budget runs out")}
      ${range("budget", "daily budget", 1, 10, 1)}
      <label>evening starts<input type="time" name="eveningStart" value="${s.eveningStart}"></label></fieldset>
    <fieldset><legend>Rules</legend>${check("familyAlways", "family always interrupts")}${check("silentRerun", "rerun flaky CI silently")}</fieldset>
    <fieldset><legend>People</legend><div class="person muted"><span></span><span>family</span><span>VIP</span></div>
      ${people.map(([k, p]) => `<div class="person"><span>${esc(p.name)} <span class="muted">${esc(p.role ?? "")}</span></span>
        <input type="checkbox" data-list="family" value="${k}" ${s.family.includes(k) ? "checked" : ""}>
        <input type="checkbox" data-list="vip" value="${k}" ${s.vip.includes(k) ? "checked" : ""}></div>`).join("")}</fieldset>
    <button type="button" id="reset-settings">Reset to defaults</button>`;
}

function onSettingsInput(ev) {
  const t = ev.target;
  if (t.id === "reset-settings") { ui.settings = { ...DEFAULTS }; renderSettings(); }
  else if (t.dataset.list) {
    const list = new Set(ui.settings[t.dataset.list]);
    t.checked ? list.add(t.value) : list.delete(t.value);
    ui.settings = { ...ui.settings, [t.dataset.list]: [...list] };
  } else if (t.name) {
    const v = t.type === "checkbox" ? t.checked : t.type === "range" ? Number(t.value) : t.value;
    ui.settings = { ...ui.settings, [t.name]: v };
    const out = t.parentElement.querySelector(".val");
    if (out) out.textContent = t.value;
  } else return;
  saveSettings(); ui.askChoices.clear(); ui.asked.clear(); reroute();
}

// ---------- modals ----------
function openModal(html) { $("modal-card").innerHTML = html; $("modal").hidden = false; }
function closeModal() { $("modal").hidden = true; }

function showAsk(e) {
  const d = ui.decisions.get(e.id);
  const unsure = d.reasons.filter((r) => r.p > effectiveSettings(ui.settings).noAt && r.p < effectiveSettings(ui.settings).yesAt);
  const other = unsure.some((r) => r.q === "needs_sanad") ? "delegate" : "batch";
  ui.playing = false;
  openModal(`<h3>Jev isn't sure. Your call, Sanad.</h3>
    <p><b>${esc(senderName(e))}</b> at ${e.time}: “${esc(e.text)}”</p>
    <p class="muted">${unsure.map((r) => `${esc(r.q)} = ${r.p.toFixed(2)}`).join(" · ")} (between ${ui.settings.noAt} and ${ui.settings.yesAt})</p>
    <div class="choices"><button data-ask="${e.id}" data-choice="interrupt">🔔 Show me now</button>
      <button data-ask="${e.id}" data-choice="${other}">${other === "delegate" ? "Forward it" : "Later is fine"}</button></div>
    <p class="muted small">Your click changes what you see here only. It never changes Jev's answers or the metrics.</p>`);
}

function showDigest() {
  const held = new Set(data.events.filter((e) => ui.decisions.get(e.id)?.action === "batch").map((e) => e.id));
  const groups = (data.results.digest?.groups ?? [])
    .map((g) => ({ ...g, items: g.items.filter((i) => held.has(i.event_id)) })).filter((g) => g.items.length);
  openModal(`<h3>End-of-day digest</h3><p class="muted">Everything Bouncer held back for you today, written by the LLM after the rules decided.</p>
    ${groups.map((g) => `<div class="digest-group"><h4>${esc(g.title)}</h4>${g.items.map((i) => `<div class="digest-item">
      <span class="muted">${esc(data.byId[i.event_id]?.time ?? "")}</span> ${esc(i.summary)}${i.draft_reply ? `<div class="draft">Draft reply: ${esc(i.draft_reply)}</div>` : ""}</div>`).join("")}</div>`).join("")
    || "<p>Nothing was held back.</p>"}
    <div class="choices"><button data-close>Close</button></div>`);
}

// ---------- replay loop ----------
function advance(to) {
  const from = ui.clock;
  ui.clock = Math.min(DAY_END, to);
  const crossed = data.events.filter((e) => toMin(e.time) > from && toMin(e.time) <= ui.clock).sort((a, b) => a.time.localeCompare(b.time) || a.id.localeCompare(b.id));
  const newest = crossed.at(-1);
  if (newest) ui.selected = newest.id;
  const ask = crossed.find((e) => ui.decisions.get(e.id)?.action === "ask" && !ui.asked.has(e.id));
  if (ask) { ui.clock = toMin(ask.time); ui.selected = ask.id; ui.asked.add(ask.id); render(); showAsk(ask); return; }
  if (ui.clock >= DAY_END) { ui.playing = false; if (!ui.digestShown) { ui.digestShown = true; render(); showDigest(); return; } }
  if (crossed.length) render();
  else if (Math.floor(ui.clock) !== Math.floor(from)) renderHeader(), renderPhoneClock();
}

let last = performance.now();
function tick(now) {
  const dt = (now - last) / 1000; last = now;
  if (ui.playing && $("modal").hidden) advance(ui.clock + dt * ui.speed);
  requestAnimationFrame(tick);
}

function jump() {
  const next = data.moments.find((m) => m.at - 1 > ui.clock + 0.01);
  ui.playing = false;
  if (next) advance(next.at - 1); else advance(DAY_END);
}

function restart() {
  ui.clock = DAY_START; ui.playing = false; ui.selected = null; ui.askChoices.clear(); ui.asked.clear(); ui.rerouted.clear(); ui.digestShown = false;
  $("why").innerHTML = `<p class="muted">Click an event to see what Jev was shown, what it answered and which rule fired.</p>`;
  render();
}

function wire() {
  $("play").onclick = () => { ui.playing = true; render(); };
  $("pause").onclick = () => { ui.playing = false; render(); };
  $("jump").onclick = jump;
  $("restart").onclick = restart;
  $("speed").onclick = () => { ui.speed = ui.speed === 1 ? 10 : 1; render(); };
  $("open-settings").onclick = () => { renderSettings(); $("settings").hidden = false; };
  $("close-settings").onclick = () => { $("settings").hidden = true; };
  $("toggle-sender").onclick = () => { ui.senderView = !ui.senderView; $("toggle-sender").classList.toggle("on", ui.senderView); render(); };
  $("open-digest").onclick = showDigest;
  $("settings-form").addEventListener("input", onSettingsInput);
  $("settings-form").addEventListener("click", (ev) => { if (ev.target.id === "reset-settings") onSettingsInput(ev); });
  document.body.addEventListener("click", (ev) => {
    const t = ev.target.closest("[data-id],[data-urgent],[data-ask],[data-close]");
    if (!t) { if (ev.target === $("modal")) closeModal(); return; }
    if (t.dataset.urgent) { ui.rerouted.add(t.dataset.urgent); render(); }
    else if (t.dataset.ask) { ui.askChoices.set(t.dataset.ask, t.dataset.choice); closeModal(); render(); }
    else if ("close" in t.dataset) closeModal();
    else if (t.dataset.id) { ui.selected = t.dataset.id; render(); }
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.target.tagName === "INPUT") return;
    if (ev.key === " ") { ev.preventDefault(); ui.playing = !ui.playing; render(); }
    if (ev.key === "n") jump();
    if (ev.key === "Escape") { closeModal(); $("settings").hidden = true; }
  });
}

load().then(() => { wire(); reroute(); requestAnimationFrame(tick); })
  .catch((err) => { document.body.innerHTML = `<p style="padding:20px">Could not load the day: ${esc(err.message)}. Run <code>make demo</code> and open <code>localhost:8000/web/</code>.</p>`; });
