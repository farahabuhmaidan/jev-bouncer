import { test } from "node:test";
import assert from "node:assert/strict";
import { DEFAULTS, decide, replayDay, effectiveSettings } from "./policy.js";

const SNAPSHOT = {
  devops_contact: "lina",
  people: {
    rami: { name: "Rami", lead: "yousef" }, yousef: { name: "Yousef", lead: "sanad" },
    noor: { name: "Noor", lead: "hana" }, hana: { name: "Hana", lead: null },
    lina: { name: "Lina", lead: null }, layla: { name: "Layla", lead: null, relationship: "leadership" },
    omar: { name: "Omar", lead: null }, maha: { name: "Maha", lead: null },
    school: { name: "Riverside School office", lead: null }, "github-actions": { name: "GitHub Actions", is_bot: true },
  },
};
const msg = (sender, time = "14:10", id = "e") => ({ id, time, type: "message", sender });
const ci = (time = "14:31", id = "c") => ({ id, time, type: "ci_failure", sender: "github-actions" });
const jev = (answers) => ({ answers, error: null });
const quiet = { needs_sanad: 0.9, time_sensitive: 0.1, wording_only_urgency: 0.1, family_matter: 0.05, blocks_release: 0.1, is_noise: 0.05 };
const day = (over = {}) => ({ budgetLeft: 5, bar: 0.7, evening: false, snapshot: SNAPSHOT, nextSlot: "16:00", ...over });

test("row 8: Rami's quiet time-sensitive message interrupts and uses budget", () => {
  const d = decide(msg("rami"), jev({ ...quiet, time_sensitive: 0.9 }), DEFAULTS, day());
  assert.equal(d.action, "interrupt"); assert.equal(d.rule, 8); assert.equal(d.usesBudget, true);
  assert.ok(d.reasons.some((r) => r.q === "time_sensitive"));
});

test("row 4: blocks the release and needs Sanad interrupts without budget", () => {
  const d = decide(msg("rami"), jev({ ...quiet, blocks_release: 0.93 }), DEFAULTS, day({ budgetLeft: 0 }));
  assert.equal(d.action, "interrupt"); assert.equal(d.rule, 4); assert.equal(d.usesBudget, false);
});

test("row 5: CEO URGENT about wording only is batched until the next free slot", () => {
  const d = decide(msg("layla"), jev({ ...quiet, time_sensitive: 0.8, wording_only_urgency: 0.93 }), DEFAULTS, day());
  assert.equal(d.action, "batch"); assert.equal(d.rule, 5); assert.equal(d.label, "until 16:00");
});

test("row 6: cofounder with p(needs_sanad) = 0.5 is an ask", () => {
  const d = decide(msg("omar"), jev({ ...quiet, needs_sanad: 0.5 }), DEFAULTS, day());
  assert.equal(d.action, "ask"); assert.equal(d.rule, 6);
});

test("row 7: no(needs_sanad) delegates to the sender's lead", () => {
  const d = decide(msg("noor"), jev({ ...quiet, needs_sanad: 0.1 }), DEFAULTS, day());
  assert.equal(d.action, "delegate"); assert.equal(d.label, "forwarded to Hana");
});

test("row 7: no lead (or Sanad is the lead) forwards to the team channel", () => {
  const d = decide(msg("yousef"), jev({ ...quiet, needs_sanad: 0.1 }), DEFAULTS, day());
  assert.equal(d.label, "forwarded to the team channel");
});

test("row 7: leadership is batched, not delegated (they asked Sanad directly)", () => {
  const d = decide(msg("layla"), jev({ ...quiet, needs_sanad: 0.1 }), DEFAULTS, day());
  assert.equal(d.action, "batch"); assert.equal(d.rule, 7);
});

test("row 6: an unsure time_sensitive does not ask when Sanad is clearly not needed", () => {
  const d = decide(msg("noor"), jev({ ...quiet, needs_sanad: 0.1, time_sensitive: 0.5 }), DEFAULTS, day());
  assert.equal(d.action, "delegate");
});

test("row 6: an unsure time_sensitive still asks when Sanad is needed", () => {
  assert.equal(decide(msg("rami"), jev({ ...quiet, time_sensitive: 0.5 }), DEFAULTS, day()).action, "ask");
});

test("row 3: noise is dropped", () => {
  assert.equal(decide(msg("noor"), jev({ ...quiet, is_noise: 0.9 }), DEFAULTS, day()).action, "drop");
});

test("row 9: otherwise batch", () => {
  const d = decide(msg("rami"), jev(quiet), DEFAULTS, day());
  assert.equal(d.action, "batch"); assert.equal(d.rule, 9);
});

test("row 2: evening roadmap is batched to the morning", () => {
  const d = decide(msg("omar", "19:30"), jev({ ...quiet, time_sensitive: 0.9 }), DEFAULTS, day({ evening: true }));
  assert.equal(d.action, "batch"); assert.equal(d.rule, 2); assert.equal(d.label, "until 09:00 tomorrow");
});

test("row 1: evening school message interrupts (family)", () => {
  const d = decide(msg("school", "18:40"), jev({ ...quiet, family_matter: 0.99 }), DEFAULTS, day({ evening: true }));
  assert.equal(d.action, "interrupt"); assert.equal(d.rule, 1); assert.equal(d.usesBudget, false);
});

test("row 1: sender marked family interrupts even if Jev is unsure", () => {
  const d = decide(msg("maha"), jev({ ...quiet, family_matter: 0.5 }), DEFAULTS, day());
  assert.equal(d.rule, 1);
});

test("row 1 off: with the family rule off, family is not special", () => {
  const d = decide(msg("maha"), jev({ ...quiet, family_matter: 0.99 }), { ...DEFAULTS, familyAlways: false }, day());
  assert.notEqual(d.rule, 1);
});

test("row 2 skipped: evening blocks_release is not batched by row 2", () => {
  const d = decide(msg("rami", "19:00"), jev({ ...quiet, blocks_release: 0.95 }), DEFAULTS, day({ evening: true }));
  assert.notEqual(d.rule, 2); assert.equal(d.action, "interrupt");
});

const ciJev = (type, extra = {}) => jev({
  failure_type: { flaky_test: 0.03, infra_problem: 0.03, config_or_lint: 0.03, code_regression: 0.03, [type]: 0.91 },
  cause_identifiable: 0.9, blocks_release: 0.1, ...extra,
});

test("CI flaky: drop, rerun silently", () => {
  const d = decide(ci(), ciJev("flaky_test"), DEFAULTS, day());
  assert.equal(d.action, "drop"); assert.equal(d.label, "rerun silently");
});

test("CI flaky with silent rerun off: batch", () => {
  assert.equal(decide(ci(), ciJev("flaky_test"), { ...DEFAULTS, silentRerun: false }, day()).action, "batch");
});

test("CI infra: delegate, pinged DevOps", () => {
  const d = decide(ci(), ciJev("infra_problem"), DEFAULTS, day());
  assert.equal(d.action, "delegate"); assert.equal(d.label, "pinged DevOps (Lina)");
});

test("CI lint: batch", () => {
  assert.equal(decide(ci(), ciJev("config_or_lint"), DEFAULTS, day()).action, "batch");
});

test("CI regression that blocks the release interrupts, without budget, even in the evening", () => {
  const d = decide(ci("19:00"), ciJev("code_regression", { blocks_release: 0.91 }), DEFAULTS, day({ evening: true, budgetLeft: 0 }));
  assert.equal(d.action, "interrupt"); assert.equal(d.usesBudget, false);
});

test("CI regression otherwise: batch", () => {
  assert.equal(decide(ci(), ciJev("code_regression"), DEFAULTS, day()).action, "batch");
});

test("CI evening regression without blocks: batch", () => {
  assert.equal(decide(ci("19:00"), ciJev("code_regression"), DEFAULTS, day({ evening: true })).action, "batch");
});

test("CI unclear cause interrupts, or batches when no(blocks_release)", () => {
  assert.equal(decide(ci(), ciJev("code_regression", { cause_identifiable: 0.1, blocks_release: 0.5 }), DEFAULTS, day()).action, "interrupt");
  assert.equal(decide(ci(), ciJev("code_regression", { cause_identifiable: 0.1 }), DEFAULTS, day()).action, "batch");
});

test("jev.error is an error, never routed", () => {
  const d = decide(msg("rami"), { answers: {}, error: "HTTP 500" }, DEFAULTS, day());
  assert.equal(d.action, "error");
});

test("a missing result is an error", () => {
  assert.equal(decide(msg("rami"), undefined, DEFAULTS, day()).action, "error");
});

test("yesAt <= noAt is clamped", () => {
  const s = effectiveSettings({ ...DEFAULTS, yesAt: 0.4, noAt: 0.6 });
  assert.equal(s.yesAt, 0.4); assert.ok(Math.abs(s.noAt - 0.35) < 1e-9);
});

const urgent = (id, time) => ({ ev: msg("rami", time, id), res: { jev: jev({ ...quiet, time_sensitive: 0.99 }), next_free_slot: "16:00" } });

function replay(list, settings = DEFAULTS) {
  const events = list.map((x) => x.ev);
  const results = Object.fromEntries(list.map((x) => [x.ev.id, x.res]));
  return replayDay(events, results, SNAPSHOT, settings);
}

test("budget: the 6th time-sensitive interrupt with budget 5 is batched", () => {
  const list = [1, 2, 3, 4, 5, 6].map((i) => urgent(`u${i}`, `1${i}:00`));
  const out = replay(list, { ...DEFAULTS, risingBar: false });
  assert.deepEqual([...out.values()].map((d) => d.action), ["interrupt", "interrupt", "interrupt", "interrupt", "interrupt", "batch"]);
});

test("rising bar: with 1 left the bar is 0.85", () => {
  const list = [1, 2, 3, 4, 5].map((i) => urgent(`u${i}`, `1${i}:00`));
  list[4].res.jev = jev({ ...quiet, time_sensitive: 0.8 });
  const out = replay(list);
  assert.equal(out.get("u5").action, "batch");
  assert.ok(Math.abs(out.get("u5").bar - 0.85) < 1e-9);
});

test("VIP skips the budget", () => {
  const list = [1, 2, 3, 4, 5, 6].map((i) => urgent(`u${i}`, `1${i}:00`));
  const out = replay(list, { ...DEFAULTS, risingBar: false, vip: ["rami"] });
  assert.ok([...out.values()].every((d) => d.action === "interrupt"));
});

test("evening is computed from the event time and eveningStart", () => {
  const out = replay([urgent("late", "18:30")], { ...DEFAULTS, eveningStart: "19:00" });
  assert.equal(out.get("late").action, "interrupt");
  assert.equal(replay([urgent("late", "18:30")]).get("late").rule, 2);
});

test("same-minute events are ordered by id", () => {
  const out = replay([urgent("b", "14:00"), urgent("a", "14:00")]);
  assert.deepEqual([...out.keys()], ["a", "b"]);
});
