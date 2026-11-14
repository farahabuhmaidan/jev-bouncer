import { useState } from "react";
import { reminderAction } from "../api.js";
import { Icon, niceDate } from "./ui.jsx";

// The calendar reminder Doorman added for a message with a later task (design/16).
export default function Reminder({ eventId, reminder: r, onChange, google }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  if (!r) return null;
  const act = async (action) => {
    setBusy(true); setErr(null);
    try { await reminderAction(eventId, action); await onChange?.(); } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

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
      <h3><Icon name="calendar" size={14} />{google && !r.google ? "Reminder · not in Google Calendar yet" : "Added to your calendar"}</h3>
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
        {google && !r.google && <button className="btn small" disabled={busy} onClick={() => act("push")}><Icon name="calendar" size={14} />Add to Google Calendar</button>}
        {r.google?.link && <a className="btn small" href={r.google.link} target="_blank" rel="noreferrer"><Icon name="check" size={14} />In Google Calendar</a>}
        <button className="btn small" disabled={busy} onClick={() => act("remove")}><Icon name="x" size={14} />Remove</button>
      </div>
      {err && <p className="error-line"><Icon name="alert" size={14} />{err}</p>}
    </section>
  );
}
