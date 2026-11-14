import { feedback } from "../api.js";
import { Avatar, Icon, isUrgent, senderName } from "./ui.jsx";

// What colleagues see when Doorman holds their message.
export default function SenderView({ events, people, onChange }) {
  const held = events.filter((e) => e.type === "message" && people[e.sender] && !people[e.sender].is_bot && e.decision.action === "batch");
  if (!held.length) return <div className="empty"><p>No one is waiting on you right now.</p></div>;
  return (
    <ol className="msg-list">
      {held.map((e) => (
        <li key={e.id} className="sender-card">
          <div className="msg-top"><Avatar e={e} people={people} /><span className="who">{senderName(e, people)}</span><span className="time">{e.time}</span></div>
          <p className="bubble out">{e.text}</p>
          <p className="bubble in"><Icon name="door" size={12} /> {e.result?.auto_reply ?? (e.result?.writing ? "Writing…" : "No auto-reply")}</p>
          {isUrgent(e)
            ? <span className="pill warn"><Icon name="check" size={12} />Sent to their phone</span>
            : <button className="btn small danger" onClick={async () => { await feedback(e.id, { kind: "urgent" }); onChange(); }}>It's truly urgent</button>}
        </li>
      ))}
    </ol>
  );
}
