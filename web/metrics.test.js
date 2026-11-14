import { test } from "node:test";
import assert from "node:assert/strict";
import { computeMetrics, normalizeAction } from "./metrics.js";

const ev = (id, type, action, holdout = false) => ({ id, type, label: { action }, holdout });
const res = (llmAction, { cost = 1e-5, llmCost = 2e-3, lat = 100, llmLat = 2000, error = null } = {}) => ({
  jev: { answers: {}, latency_ms: lat, usage: { cost }, error },
  baseline: { action: llmAction, latency_ms: llmLat, cost: llmCost, error: null },
});

const EVENTS = [ev("a", "message", "interrupt"), ev("b", "message", "batch", true),
  ev("c", "ci_failure", "drop"), ev("d", "ci_failure", "delegate", true)];
const RESULTS = { a: res("batch"), b: res("batch"), c: res("drop"), d: res("interrupt") };
const decisions = (actions) => new Map(Object.entries(actions).map(([id, action]) => [id, { action }]));

test("a 4-event toy set gives exact accuracy and critical misses", () => {
  const m = computeMetrics(EVENTS, decisions({ a: "interrupt", b: "batch", c: "drop", d: "batch" }), RESULTS, {});
  assert.equal(m.jev.accuracy, 0.75); assert.equal(m.jev.holdoutAccuracy, 0.5);
  assert.deepEqual(m.jev.byType, { message: 1, ci: 0.5 });
  assert.equal(m.jev.criticalMisses, 0);
  assert.equal(m.llm.accuracy, 0.5); assert.equal(m.llm.criticalMisses, 1);
  assert.deepEqual(m.llm.byType, { message: 0.5, ci: 0.5 });
});

test("an ask counts as wrong and is counted in asks", () => {
  const m = computeMetrics(EVENTS, decisions({ a: "ask", b: "batch", c: "drop", d: "delegate" }), RESULTS, {});
  assert.equal(m.jev.accuracy, 0.75); assert.equal(m.jev.asks, 1); assert.equal(m.jev.criticalMisses, 0);
});

test("an error counts as wrong and is counted in errors", () => {
  const m = computeMetrics(EVENTS, decisions({ a: "error", b: "batch", c: "drop", d: "delegate" }), RESULTS, {});
  assert.equal(m.jev.accuracy, 0.75); assert.equal(m.jev.errors, 1);
});

test("cost per 1k comes from measured usage.cost", () => {
  const m = computeMetrics(EVENTS, decisions({}), RESULTS, {});
  assert.ok(Math.abs(m.jev.costPer1k - 0.01) < 1e-12); assert.ok(Math.abs(m.llm.costPer1k - 2) < 1e-12);
});

test("costPer1k is null when nothing was measured and the price is null", () => {
  const bare = Object.fromEntries(Object.keys(RESULTS).map((k) => [k, res("batch", { cost: null, llmCost: null })]));
  const m = computeMetrics(EVENTS, decisions({}), bare, { "typesafe/jev-1.14": null });
  assert.equal(m.jev.costPer1k, null);
});

test("latency p50 and p95 use nearest rank", () => {
  const lat = { a: 100, b: 200, c: 300, d: 400 };
  const r = Object.fromEntries(Object.entries(lat).map(([k, v]) => [k, res("batch", { lat: v })]));
  const m = computeMetrics(EVENTS, decisions({}), r, {});
  assert.equal(m.jev.p50, 200); assert.equal(m.jev.p95, 400);
});

test("settingsChanged reflects the settings passed", () => {
  assert.equal(computeMetrics(EVENTS, decisions({}), RESULTS, {}, { budget: 3 }).settingsChanged, true);
  assert.equal(computeMetrics(EVENTS, decisions({}), RESULTS, {}).settingsChanged, false);
});

test("CI labels map to the four actions", () => {
  assert.equal(normalizeAction("rerun silently"), "drop");
  assert.equal(normalizeAction("pinged DevOps"), "delegate");
});
