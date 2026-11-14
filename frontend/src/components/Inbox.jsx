import { Avatar, Icon, Status, askChoice, eventText, isUrgent, senderName, sourceName } from "./ui.jsx";

export const FILTERS = [
  { key: "all", label: "All", match: () => true },
  { key: "now", label: "Got through", match: (a) => a === "interrupt" },
  { key: "ask", label: "Your call", match: (a) => a === "ask" },
  { key: "later", label: "Held", match: (a) => a === "batch" },
  { key: "handled", label: "Handled", match: (a) => a === "delegate" || a === "drop" },
];

export default function Inbox({ events, people, selected, onSelect, filter, onFilter }) {
  const action = (e) => askChoice(e) ? "ask" : e.decision.action;
  const count = (f) => events.filter((e) => f.match(action(e))).length;
  const shown = events.filter((e) => FILTERS.find((f) => f.key === filter).match(action(e)));
  return (
    <>
      <div className="segmented" role="tablist" aria-label="Filter messages">
        {FILTERS.map((f) => (
          <button key={f.key} role="tab" aria-selected={filter === f.key} className={filter === f.key ? "active" : ""} onClick={() => onFilter(f.key)}>
            {f.label}<span className="count">{count(f)}</span>
          </button>
        ))}
      </div>
      {!events.length && (
        <div className="empty">
          <Icon name="inbox" size={28} />
          <p><b>Your morning is quiet.</b><br />Press play or "next moment" to start the demo day, or send a test message.</p>
        </div>
      )}
      {events.length > 0 && !shown.length && <div className="empty small"><p>Nothing here yet.</p></div>}
      <ol className="msg-list">
        {shown.map((e) => {
          const d = e.decision, r = e.result;
          const isPerson = e.type === "message" && people[e.sender] && !people[e.sender].is_bot;
          return (
            <li key={e.id}>
              <button className={`msg ${selected === e.id ? "selected" : ""} ${e.origin === "live" ? "live" : ""} a-${d.action}`}
                onClick={() => onSelect(e.id)} aria-pressed={selected === e.id}>
                <Avatar e={e} people={people} />
                <div className="msg-body">
                  <div className="msg-top">
                    <span className="who">{senderName(e, people)}</span>
                    <span className="src">{sourceName(e.source)}</span>
                    {e.origin === "live" && <span className="pill live">Test</span>}
                    <span className="time">{e.time}</span>
                  </div>
                  <div className="msg-text">{eventText(e)}</div>
                  <div className="msg-meta">
                    <Status decision={d} chosen={askChoice(e)} />
                    {isUrgent(e) && <span className="pill warn">Sender marked urgent</span>}
                    {d.action === "batch" && isPerson && r?.auto_reply && <span className="pill quiet"><Icon name="reply" size={12} />Auto-replied</span>}
                    {d.action === "batch" && isPerson && !r?.auto_reply && r?.writing && <span className="pill quiet">Writing auto-reply…</span>}
                  </div>
                </div>
              </button>
            </li>
          );
        })}
      </ol>
    </>
  );
}
