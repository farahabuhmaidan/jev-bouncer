// Small shared pieces: action chip, sender name, urgency badge.
export function Chip({ action, label }) {
  const a = action ?? "error";
  const text = a === "drop" && label === "rerun silently" ? "rerun silently" : a;
  return <span className={`chip ${a}`}>{a === "interrupt" ? "🔔 " : ""}{text}</span>;
}

export function senderName(e, people) {
  if (e.type === "ci_failure") return `CI · ${e.test_name}`;
  return people[e.sender]?.name ?? e.sender.replace(/^unknown:/, "");
}

export function eventText(e) {
  return e.type === "ci_failure" ? `${e.branch}: ${e.commit_message ?? ""}` : e.text;
}

export function Urgency({ result }) {
  const u = result?.jev?.answers?.urgency;
  if (!u || typeof u.score !== "number") return null;
  return <span className="urg" title="Urgency 1–5 (Jev Score, display only)">U{Math.round(u.score) + 1}</span>;
}

export const askChoice = (e) => e.feedback?.find((f) => f.kind === "ask")?.value;
export const isUrgent = (e) => e.feedback?.some((f) => f.kind === "urgent");
