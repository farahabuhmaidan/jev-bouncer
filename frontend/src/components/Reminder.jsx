import { useState } from "react";
import { reminderAction } from "../api.js";
import { Icon, niceDate } from "./ui.jsx";

// The calendar reminder Doorman added for a message with a later task (design/16).
export default function Reminder({ eventId, reminder: r, onChange }) {
  const [busy, setBusy] = useState(false);
  if (!r) return null;
  const act = async (action) => { setBusy(true); try { await reminderAction(eventId, action); await onChange?.(); } finally { setBusy(false); } };

  if (r.status === "error") {
    return <section className="card"><h3><Icon name="calendar" size={14} />Reminder</h3>
      <p className="error-line"><Icon name="alert" size={14} />Couldn't check whether this needs a reminder: {r.error}</p></section>;
  }
  if (r.status === "removed") {
    return <section className="card reminder removed"><h3><Icon name="calendar" size={14} />Reminder removed</h3>
      <div className="actions"><button className="btn small" disabled={busy} onClick={() => act("add")}>Add it back</button></div></section>;
  }
  return (
    <section className={`card reminder ${r.clashes.length ? "clash" : ""}`}>
      <h3><Icon name="calendar" size={14} />Added to your calendar</h3>
      <div className="rem-main">
        <div className="rem-date"><b>{niceDate(r.date).split(" ")[1]}</b><span>{niceDate(r.date).split(" ")[2]}</span></div>
        <div>
          <p className="rem-title">{r.title}</p>
          <p className="rem-when">{niceDate(r.date)} · {r.time} · {r.minutes} min <span className="muted">from “{r.phrase}”</span></p>
        </div>
      </div>
      {r.clashes.length > 0 && (
        <div className="rem-clash" role="alert">
          <Icon name="alert" size={14} />
          <span>Clashes with {r.clashes.map((c) => `${c.title} (${c.start}–${c.end})`).join(", ")}</span>
        </div>
      )}
      <div className="actions">
        {r.suggested && <button className="btn small primary" disabled={busy} onClick={() => act("move")}><Icon name="clock" size={14} />Move to {r.suggested}</button>}
        <button className="btn small" disabled={busy} onClick={() => act("remove")}><Icon name="x" size={14} />Remove</button>
      </div>
    </section>
  );
}
