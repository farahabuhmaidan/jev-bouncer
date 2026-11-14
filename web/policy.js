// Routing policy (design/04-policy.md). Jev answers the judgments; this file decides.
// Pure functions, no DOM: the page, the slides and node --test all import the same code.

export const DEFAULTS = Object.freeze({
  yesAt: 0.7,
  noAt: 0.3,
  interruptBar: 0.7,
  risingBar: true,
  budget: 5,
  eveningStart: "18:00",
  familyAlways: true,
  silentRerun: true,
  family: ["maha", "school"],
  vip: [],
});

const MORNING = "until 09:00 tomorrow";

/** Keep the "sure" band valid: yesAt must stay above noAt. */
export function effectiveSettings(settings) {
  const s = { ...DEFAULTS, ...settings };
  if (s.yesAt <= s.noAt) s.noAt = s.yesAt - 0.05;
  return s;
}

export function risingBar(settings, budgetLeft) {
  const { interruptBar: bar, budget } = settings;
  if (!settings.risingBar) return bar;
  return Math.min(0.95, bar + (0.15 * (budget - budgetLeft)) / Math.max(1, budget - 1));
}

const p = (answers, q) => (typeof answers[q] === "number" ? answers[q] : null);

function reader(answers, s) {
  const reasons = [];
  const seen = (q) => {
    const v = p(answers, q);
    if (v !== null && !reasons.some((r) => r.q === q)) reasons.push({ q, p: v });
    return v;
  };
  return {
    reasons,
    yes: (q) => (seen(q) ?? -1) >= s.yesAt,
    no: (q) => (seen(q) ?? 2) <= s.noAt,
    unsure: (q) => { const v = seen(q); return v === null || (v > s.noAt && v < s.yesAt); },
    p: seen,
  };
}

function delegateTo(event, snapshot) {
  const person = snapshot.people?.[event.sender];
  const lead = person?.lead && person.lead !== "sanad" ? snapshot.people[person.lead] : null;
  return lead ? `forwarded to ${lead.name}` : "forwarded to the team channel";
}

function decideMessage(event, r, s, day) {
  const out = (action, rule, extra = {}) => ({ action, rule, reasons: r.reasons, usesBudget: false, ...extra });
  const later = { label: day.evening ? MORNING : `until ${day.nextSlot ?? "the next free slot"}` };

  if (s.familyAlways && (s.family.includes(event.sender) || r.yes("family_matter"))) return out("interrupt", 1);
  if (day.evening && !r.yes("blocks_release")) return out("batch", 2, { label: MORNING });
  if (r.yes("is_noise")) return out("drop", 3);
  if (r.yes("blocks_release") && r.yes("needs_sanad")) return out("interrupt", 4);
  if (r.yes("wording_only_urgency") && !r.yes("blocks_release")) return out("batch", 5, later);
  if (r.unsure("needs_sanad")) return out("ask", 6);
  if (r.no("needs_sanad")) {
    // Leadership asked Sanad directly: hold it for him rather than forwarding it.
    if (day.snapshot.people?.[event.sender]?.relationship === "leadership") return out("batch", 7, later);
    return out("delegate", 7, { label: delegateTo(event, day.snapshot) });
  }
  // Timing only matters once Sanad is needed, so an unsure time_sensitive asks only here.
  if (r.unsure("time_sensitive")) return out("ask", 6);
  const vip = s.vip.includes(event.sender);
  if (r.yes("time_sensitive") && (vip || day.budgetLeft >= 1) && r.p("time_sensitive") >= day.bar) {
    return out("interrupt", 8, { usesBudget: !vip });
  }
  return out("batch", 9, later);
}

function topChoice(dist = {}) {
  let best = null;
  for (const [k, v] of Object.entries(dist)) if (best === null || v > dist[best]) best = k;
  return best;
}

function decideCi(event, r, s, day, answers) {
  const type = topChoice(answers.failure_type);
  if (type) r.reasons.push({ q: "failure_type", p: answers.failure_type[type], value: type });
  const out = (action, rule, extra = {}) => ({ action, rule, reasons: r.reasons, usesBudget: false, ...extra });
  const blocks = r.yes("blocks_release");

  if (type === "code_regression" && blocks) return out("interrupt", "ci-regression-blocks", { label: "explanation attached" });
  if (day.evening) return out("batch", "ci-evening", { label: MORNING });
  if (r.no("cause_identifiable")) {
    return r.no("blocks_release") ? out("batch", "ci-unclear", { label: "unclear failure" })
      : out("interrupt", "ci-unclear", { label: "unclear failure" });
  }
  if (type === "flaky_test") return s.silentRerun ? out("drop", "ci-flaky", { label: "rerun silently" }) : out("batch", "ci-flaky");
  if (type === "infra_problem") {
    const devops = day.snapshot.people?.[day.snapshot.devops_contact];
    return out("delegate", "ci-infra", { label: devops ? `pinged DevOps (${devops.name})` : "pinged DevOps" });
  }
  if (type === "config_or_lint") return out("batch", "ci-lint");
  return out("batch", "ci-regression", { label: "explanation in the digest" });
}

/** decide(event, jev, settings, day) -> {action, rule, reasons, usesBudget, label?} */
export function decide(event, jev, settings, day) {
  if (!jev || jev.error) {
    return { action: "error", rule: "error", reasons: [], usesBudget: false, label: jev?.error ?? "no result" };
  }
  const s = effectiveSettings(settings);
  const answers = jev.answers ?? {};
  const r = reader(answers, s);
  return event.type === "ci_failure" ? decideCi(event, r, s, day, answers) : decideMessage(event, r, s, day);
}

/** Replays the whole day from 00:00 under the given settings. Returns Map<eventId, decision>. */
export function replayDay(events, results, snapshot, settings) {
  const s = effectiveSettings(settings);
  const ordered = [...events].sort((a, b) => a.time.localeCompare(b.time) || a.id.localeCompare(b.id));
  const out = new Map();
  let budgetLeft = s.budget;
  for (const event of ordered) {
    const res = results[event.id];
    const day = {
      budgetLeft, snapshot, bar: risingBar(s, budgetLeft),
      evening: event.time >= s.eveningStart, nextSlot: res?.next_free_slot,
    };
    const d = decide(event, res?.jev, s, day);
    if (d.usesBudget) budgetLeft -= 1;
    out.set(event.id, { ...d, bar: day.bar, budgetLeftAfter: budgetLeft });
  }
  return out;
}
