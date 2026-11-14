// Metrics for the strip and the slides (design/08-evaluation.md).
// Labels assume default settings; an "ask" or an error always counts as wrong.
import { DEFAULTS } from "./policy.js";

const ALIASES = { "rerun silently": "drop", "pinged DevOps": "delegate" };
export const normalizeAction = (a) => ALIASES[a] ?? a;

const MISSES = new Set(["batch", "drop", "delegate"]);
const share = (hits, n) => (n ? hits / n : null);

function quantile(values, q) {
  const xs = values.filter((v) => typeof v === "number").sort((a, b) => a - b);
  if (!xs.length) return null;
  return xs[Math.min(xs.length - 1, Math.max(0, Math.ceil(q * xs.length) - 1))];
}

/** Mean measured cost per call x 1000; falls back to list price x tokens; null if neither is known. */
function costPer1k(costs, tokens, price) {
  const measured = costs.filter((c) => typeof c === "number");
  if (measured.length) return (measured.reduce((a, b) => a + b, 0) / measured.length) * 1000;
  if (!price || !tokens.length) return null;
  const per = tokens.map((t) => ((t.in ?? 0) * price.input + (t.out ?? 0) * price.output) / 1e6);
  return (per.reduce((a, b) => a + b, 0) / per.length) * 1000;
}

function score(events, actionOf) {
  const right = (e) => normalizeAction(actionOf(e)) === e.label.action;
  const acc = (list) => share(list.filter(right).length, list.length);
  return {
    accuracy: acc(events),
    holdoutAccuracy: acc(events.filter((e) => e.holdout)),
    byType: { message: acc(events.filter((e) => e.type === "message")), ci: acc(events.filter((e) => e.type === "ci_failure")) },
    criticalMisses: events.filter((e) => e.label.action === "interrupt" && MISSES.has(normalizeAction(actionOf(e)))).length,
  };
}

export function settingsDiffer(settings = {}) {
  return Object.entries(DEFAULTS).some(([k, v]) => k in settings && JSON.stringify(settings[k]) !== JSON.stringify(v));
}

/** computeMetrics(events, decisions, results, prices, settings?) */
export function computeMetrics(events, decisions, results, prices = {}, settings = {}) {
  const labelled = events.filter((e) => e.label?.action);
  const jevAction = (e) => decisions.get(e.id)?.action ?? "error";
  const llmAction = (e) => results[e.id]?.baseline?.action ?? "error";
  const jevRes = labelled.map((e) => results[e.id]?.jev ?? {});
  const llmRes = labelled.map((e) => results[e.id]?.baseline ?? {});
  return {
    jev: {
      ...score(labelled, jevAction),
      asks: labelled.filter((e) => jevAction(e) === "ask").length,
      errors: labelled.filter((e) => jevAction(e) === "error").length,
      p50: quantile(jevRes.map((r) => r.latency_ms), 0.5),
      p95: quantile(jevRes.map((r) => r.latency_ms), 0.95),
      costPer1k: costPer1k(jevRes.map((r) => r.usage?.cost), jevRes.map((r) => ({ in: r.usage?.prompt_tokens })).filter((t) => t.in),
        prices["typesafe/jev-1.14"]),
    },
    llm: {
      ...score(labelled, llmAction),
      errors: labelled.filter((e) => llmAction(e) === "error").length,
      p50: quantile(llmRes.map((r) => r.latency_ms), 0.5),
      p95: quantile(llmRes.map((r) => r.latency_ms), 0.95),
      costPer1k: costPer1k(llmRes.map((r) => r.cost), llmRes.map((r) => r.tokens).filter(Boolean), prices["anthropic/claude-sonnet-5.5"]),
    },
    settingsChanged: settingsDiffer(settings),
  };
}
