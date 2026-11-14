import { eventText, senderName } from "./ui.jsx";

export default function Phone({ day, people, onSelect }) {
  const byId = Object.fromEntries(day.events.map((e) => [e.id, e]));
  const items = day.phone.map((id) => byId[id]).filter(Boolean);
  return (
    <div className={`phone ${day.evening ? "evening" : ""}`}>
      <div className="phone-status"><span>{day.clock}</span><span>{day.evening ? "🌙 evening" : "● online"}</span></div>
      <ol className="list">
        {items.length === 0 && <li className="muted small">Quiet. Nothing has needed Sanad yet.</li>}
        {items.map((e) => {
          const urgent = e.decision.action !== "interrupt";
          return (
            <li key={e.id} className={`notif ${urgent ? "rerouted" : ""}`} onClick={() => onSelect?.(e.id)}>
              <div className="h"><span>{senderName(e, people)}</span><span>{e.time}</span></div>
              <div className="b">{eventText(e).slice(0, 160)}</div>
              {e.result?.ci_explanation && <div className="x">Likely cause: {e.result.ci_explanation.likely_cause}</div>}
              {urgent && <div className="x">Sender tapped “truly urgent”</div>}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
