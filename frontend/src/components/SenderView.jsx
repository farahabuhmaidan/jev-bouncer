import { feedback } from "../api.js";
import { isUrgent, senderName } from "./ui.jsx";

export default function SenderView({ events, people, onChange }) {
  const held = events.filter((e) => e.type === "message" && people[e.sender] && !people[e.sender].is_bot && e.decision.action === "batch");
  if (!held.length) return <p className="muted">No one is waiting on Sanad yet.</p>;
  return (
    <ol className="list">
      {held.map((e) => (
        <li key={e.id} className="item">
          <div className="top"><span className="time">{e.time}</span><span className="who">{senderName(e, people)} sent:</span></div>
          <div className="text">{e.text}</div>
          <div className="reply">Auto-reply: {e.result?.auto_reply ?? (e.result?.writing ? "writing…" : "(none)")}</div>
          {isUrgent(e)
            ? <span className="tag urgent-tag">→ on Sanad's phone</span>
            : <button className="urgent-btn" onClick={async () => { await feedback(e.id, { kind: "urgent" }); onChange(); }}>truly urgent</button>}
        </li>
      ))}
    </ol>
  );
}
