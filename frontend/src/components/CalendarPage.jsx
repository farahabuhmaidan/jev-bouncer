import { useEffect, useState } from "react";
import { getCalendar } from "../api.js";
import Reminder from "./Reminder.jsx";
import { Icon, niceDate } from "./ui.jsx";

const toMin = (t) => { const [h, m] = t.split(":").map(Number); return h * 60 + m; };

function DayAgenda({ r }) {
  const end = (() => { const m = toMin(r.time) + r.minutes; return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`; })();
  const rows = [...r.day.map((e) => ({ ...e, kind: "event" })), { title: r.title, start: r.time, end, kind: "reminder" }]
    .sort((a, b) => a.start.localeCompare(b.start));
  const clash = new Set(r.clashes.map((c) => c.title));
  return (
    <ol className="agenda">
      {rows.map((e, i) => (
        <li key={i} className={`${e.kind} ${clash.has(e.title) ? "clashing" : ""}`}>
          <span className="ag-time">{e.start}–{e.end}</span>
          <span className="ag-title">{e.kind === "reminder" && <Icon name="door" size={12} />}{e.title}</span>
          {clash.has(e.title) && <span className="pill warn">Clash</span>}
        </li>
      ))}
    </ol>
  );
}

export default function CalendarPage({ version }) {
  const [cal, setCal] = useState(null);
  const load = () => getCalendar().then(setCal);
  useEffect(() => { load(); }, [version]);
  if (!cal) return <div className="page"><p className="muted">Loading…</p></div>;
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Calendar</h1>
          <p>When a message gives you something to do later, Doorman adds a reminder at the time it implies and checks it against your calendar.</p>
        </div>
        <span className="conn"><span className="dot" />{cal.connection.provider} · {cal.connection.account}{cal.connection.demo && <span className="pill">Demo data</span>}</span>
      </div>
      {cal.reminders.length === 0 && (
        <div className="panel-card empty">
          <Icon name="calendar" size={28} />
          <p><b>No reminders yet.</b><br />Try a test message like “you need to pay school fees next month”.</p>
        </div>
      )}
      {cal.reminders.map((r) => (
        <section key={r.event_id} className="panel-card rem-day">
          <div className="rem-day-head">
            <h2>{niceDate(r.date)}</h2>
            <span className="muted small">From {r.sender?.split(/ [(,]|,/)[0]}: “{r.message}”</span>
          </div>
          <div className="rem-day-body">
            <DayAgenda r={r} />
            <Reminder eventId={r.event_id} reminder={r} onChange={load} google={!cal.connection.demo} />
          </div>
        </section>
      ))}
    </div>
  );
}
