// `make eval` prints the numbers quoted in the README, from web/results.json at default settings.
import { readFileSync } from "node:fs";
import { DEFAULTS, replayDay } from "./policy.js";
import { computeMetrics } from "./metrics.js";

const read = (f) => JSON.parse(readFileSync(new URL(f, import.meta.url)));
const results = read("./results.json");
const { events, snapshot } = results.day;
const m = computeMetrics(events, replayDay(events, results.events, snapshot, DEFAULTS), results.events, read("./prices.json"), DEFAULTS);
const pct = (x) => (x === null ? "–" : `${Math.round(x * 100)}%`);
const ms = (x) => (x === null ? "–" : `${x} ms`);
const usd = (x) => (x === null ? "–" : `$${x.toFixed(3)}`);
const n = (filter) => events.filter(filter).length;
console.log(`${results.models.jev} vs ${results.models.llm}, run ${results.generated_at}`);
console.log(`n = ${events.length} events (${n((e) => e.type === "message")} messages, ${n((e) => e.type === "ci_failure")} CI), holdout ${n((e) => e.holdout)}\n`);
console.log("| Metric | Jev + rules | LLM only |\n|---|---|---|");
const rows = [
  ["Accuracy, all events", pct(m.jev.accuracy), pct(m.llm.accuracy)],
  ["Accuracy, holdout", pct(m.jev.holdoutAccuracy), pct(m.llm.holdoutAccuracy)],
  ["Accuracy, messages", pct(m.jev.byType.message), pct(m.llm.byType.message)],
  ["Accuracy, CI failures", pct(m.jev.byType.ci), pct(m.llm.byType.ci)],
  ["Critical misses (should have interrupted)", m.jev.criticalMisses, m.llm.criticalMisses],
  ["Asks (counted as wrong)", m.jev.asks, "–"],
  ["Errors", m.jev.errors, m.llm.errors],
  ["Latency per call, p50 / p95", `${ms(m.jev.p50)} / ${ms(m.jev.p95)}`, `${ms(m.llm.p50)} / ${ms(m.llm.p95)}`],
  ["Routing cost per 1,000 events", usd(m.jev.costPer1k), usd(m.llm.costPer1k)],
];
for (const r of rows) console.log(`| ${r.join(" | ")} |`);
