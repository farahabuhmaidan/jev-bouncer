import { Chip, Urgency, askChoice, eventText, isUrgent, senderName } from "./ui.jsx";

export default function Inbox({ events, people, selected, onSelect }) {
  if (!events.length) return <p className="muted">Nothing yet. Press ▶ or ⏭, or send a message.</p>;
  return (
    <ol className="list">
      {events.map((e) => {
        const d = e.decision, r = e.result;
        const isPerson = e.type === "message" && people[e.sender] && !people[e.sender].is_bot;
        const chosen = askChoice(e);
        return (
          <li key={e.id} className={`item ${selected === e.id ? "selected" : ""} ${e.origin === "live" ? "live" : ""}`} onClick={() => onSelect(e.id)}>
            <div className="top">
              <span className="time">{e.time}</span>
              <span className="who">{senderName(e, people)}</span>
              <Urgency result={r} />
              {e.origin === "live" && <span className="tag live-tag">live</span>}
              <span className="src">{e.source}</span>
            </div>
            <div className="text">{eventText(e)}</div>
            <div className="meta">
              <Chip action={chosen ?? d.action} label={d.label} />
              {d.label && d.label !== "rerun silently" && d.action !== "error" && <span className="tag">{d.label}</span>}
              {chosen && <span className="tag">you chose this · Jev was unsure</span>}
              {isUrgent(e) && <span className="tag urgent-tag">sender: truly urgent</span>}
              {d.action === "error" && <span className="tag">{d.label}</span>}
            </div>
            {d.action === "batch" && isPerson && (r?.auto_reply
              ? <div className="reply">↩ {r.auto_reply}</div>
              : r?.writing ? <div className="reply muted">↩ writing auto-reply…</div> : null)}
          </li>
        );
      })}
    </ol>
  );
}
