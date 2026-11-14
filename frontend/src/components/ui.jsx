// Shared pieces: icons, plain-language status and explanations, sender names.

// Lucide-style 24px stroke icons (MIT), inlined so the app works offline.
const PATHS = {
  door: <><path d="M13 4h3a2 2 0 0 1 2 2v14" /><path d="M2 20h3" /><path d="M13 20h9" /><path d="M10 12v.01" /><path d="M13 4.56v16.16a1 1 0 0 1-1.24.97L5 20V5.56a2 2 0 0 1 1.52-1.94l4-1A2 2 0 0 1 13 4.56Z" /></>,
  bell: <><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" /></>,
  clock: <><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></>,
  forward: <><path d="m15 17 5-5-5-5" /><path d="M4 18v-2a4 4 0 0 1 4-4h12" /></>,
  filter: <path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z" />,
  help: <><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" /><path d="M12 17h.01" /></>,
  alert: <><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" /><path d="M12 9v4" /><path d="M12 17h.01" /></>,
  play: <path d="m6 3 14 9-14 9V3z" />,
  pause: <><rect x="6" y="4" width="4" height="16" rx="1" /><rect x="14" y="4" width="4" height="16" rx="1" /></>,
  next: <><path d="m5 4 10 8-10 8V4z" /><path d="M19 5v14" /></>,
  reset: <><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /><path d="M3 3v5h5" /></>,
  sliders: <><path d="M4 21v-7" /><path d="M4 10V3" /><path d="M12 21v-9" /><path d="M12 8V3" /><path d="M20 21v-5" /><path d="M20 12V3" /><path d="M2 14h4" /><path d="M10 8h4" /><path d="M18 16h4" /></>,
  chart: <><path d="M3 3v18h18" /><path d="M18 17V9" /><path d="M13 17V5" /><path d="M8 17v-3" /></>,
  inbox: <><path d="M22 12h-6l-2 3h-4l-2-3H2" /><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" /></>,
  phone: <><rect x="5" y="2" width="14" height="20" rx="2" /><path d="M12 18h.01" /></>,
  flask: <><path d="M9 3h6" /><path d="M10 9V3" /><path d="M14 9V3" /><path d="M10 9 4.5 19a1.5 1.5 0 0 0 1.3 2h12.4a1.5 1.5 0 0 0 1.3-2L14 9" /><path d="M7 15h10" /></>,
  user: <><circle cx="12" cy="8" r="4" /><path d="M20 21a8 8 0 0 0-16 0" /></>,
  send: <><path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" /></>,
  moon: <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />,
  x: <><path d="M18 6 6 18" /><path d="m6 6 12 12" /></>,
  check: <path d="M20 6 9 17l-5-5" />,
  reply: <><path d="m9 17-5-5 5-5" /><path d="M20 18v-2a4 4 0 0 0-4-4H4" /></>,
  file: <><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" /><path d="M14 2v4a2 2 0 0 0 2 2h4" /><path d="M10 13H8" /><path d="M16 17H8" /></>,
  timer: <><circle cx="12" cy="13" r="8" /><path d="M12 9v4l2 2" /><path d="M10 2h4" /></>,
  code: <><path d="m16 18 6-6-6-6" /><path d="m8 6-6 6 6 6" /></>,
  calendar: <><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4" /><path d="M8 2v4" /><path d="M3 10h18" /></>,
  link: <><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></>,
  shield: <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />,
};

export function Icon({ name, size = 16, className = "", label }) {
  return (
    <svg className={`icon ${className}`} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" role={label ? "img" : undefined}
      aria-label={label} aria-hidden={label ? undefined : true}>
      {PATHS[name]}
    </svg>
  );
}

// What happened, in words an employee uses. One entry per action.
export const STATUS = {
  interrupt: { text: "Interrupted you", icon: "bell" },
  ask: { text: "Needs your call", icon: "help" },
  batch: { text: "Held for later", icon: "clock" },
  delegate: { text: "Forwarded", icon: "forward" },
  drop: { text: "Filtered out", icon: "filter" },
  error: { text: "Not routed", icon: "alert" },
};

export function statusText(d) {
  if (!d) return "";
  if (d.action === "drop" && d.label === "rerun silently") return "Rerun silently";
  if (d.action === "delegate" && d.label) return d.label.replace(/^forwarded to /, "Forwarded to ").replace(/^pinged/, "Pinged");
  if (d.action === "batch" && d.label) return `Held ${d.label}`;
  return STATUS[d.action]?.text ?? d.action;
}

export function Status({ decision: d, chosen, compact }) {
  const action = chosen ?? d?.action ?? "error";
  const text = chosen ? (chosen === "interrupt" ? "You said: show me" : "You said: later") : statusText(d);
  return (
    <span className={`status s-${action} ${compact ? "compact" : ""}`}>
      <Icon name={STATUS[action]?.icon ?? "alert"} size={13} />{text}
    </span>
  );
}

// The rule that fired, as one sentence. Rule numbers stay in "technical details".
export function explain(e, d, people) {
  const name = senderName(e, people);
  const deadline = e.result?.facts?.deadline_in_minutes;
  const r = d.rule;
  if (d.action === "error") return "Doorman couldn't reach the model, so it didn't guess. A failed call is never treated as a no.";
  if (r === 1) {
    if (d.action === "interrupt") return `${name} is family, and this can't wait. Family always gets through.`;
    const loud = d.reasons.some((x) => x.q === "wording_only_urgency");
    return loud ? `${name} is family, but the urgency is only in the wording. Held for your next break.` : `${name} is family, but this can wait. Held for your next break.`;
  }
  if (r === 2) return "It's after hours and this doesn't block the release. Held until the morning.";
  if (r === 3) return "There's nothing for you to do or reply to here, so it was filtered out.";
  if (r === 4) return "It blocks today's release or the demo, and it needs you specifically.";
  if (r === 5) return `It has a deadline in ${deadline} minutes. Deadlines always get through and don't use your budget.`;
  if (r === 6) return "It sounds urgent, but nothing in it is time-critical. Held, and the sender got an auto-reply.";
  if (r === 7) return "Doorman isn't sure whether this needs you, so it's asking instead of guessing.";
  if (r === 8) return d.action === "delegate" ? `Someone else can handle this, so it was ${d.label}.` : "It doesn't need your hands, but leadership asked you directly. Held for your next break.";
  if (r === 9) return "It's time-sensitive and needs you, so it used one of today's interruptions.";
  if (r === 10) return "It needs you, but not right now. Held for your next break.";
  return {
    "ci-regression-blocks": "A code change broke a test on a release branch. Doorman attached an explanation.",
    "ci-evening": "A CI failure after hours. Held until the morning.",
    "ci-unclear": "The CI log doesn't show what failed, so a person needs to look.",
    "ci-flaky": "A flaky test. Doorman reran it silently.",
    "ci-infra": `The CI machinery failed, not the code. ${d.label ? d.label[0].toUpperCase() + d.label.slice(1) : "DevOps was pinged"}.`,
    "ci-lint": "A lint or config failure. Held for your next break.",
    "ci-regression": "A code regression that doesn't block the release. It's in your digest with an explanation.",
  }[r] ?? "";
}

// Human names for Jev's questions.
export const SIGNALS = {
  needs_sanad: "Needs you specifically",
  time_sensitive: "Can't wait a few hours",
  wording_only_urgency: "Urgent tone only",
  family_matter: "Family or personal",
  blocks_release: "Blocks the release",
  is_noise: "Nothing to act on",
  cause_identifiable: "Log shows the cause",
};

export function senderName(e, people) {
  if (e.type === "ci_failure") return "CI pipeline";
  return people[e.sender]?.name ?? e.sender.replace(/^unknown:/, "");
}

export function senderRole(e, people) {
  if (e.type === "ci_failure") return e.test_name;
  return people[e.sender]?.role ?? "Outside sender";
}

export function eventText(e) {
  return e.type === "ci_failure" ? `${e.test_name} failed on ${e.branch}${e.commit_message ? ` · "${e.commit_message}"` : ""}` : e.text;
}

const SOURCES = { slack: "Slack", email: "Email", gmail: "Gmail", github_actions: "GitHub Actions", compose: "Test message", teams: "Teams", whatsapp: "WhatsApp", calendar: "Calendar" };
export const sourceName = (s) => SOURCES[s] ?? s;

export function Avatar({ e, people }) {
  if (e.type === "ci_failure") return <span className="avatar ci"><Icon name="code" size={15} /></span>;
  const n = senderName(e, people);
  const initials = n.split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  return <span className={`avatar ${people[e.sender]?.is_bot ? "bot" : ""}`}>{initials}</span>;
}

export function niceDate(iso) {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
}

export const askChoice = (e) => e.feedback?.find((f) => f.kind === "ask")?.value;
export const isUrgent = (e) => e.feedback?.some((f) => f.kind === "urgent");

// Kept for the test bench.
export function Chip({ action, label }) {
  return <Status decision={{ action, label }} />;
}
