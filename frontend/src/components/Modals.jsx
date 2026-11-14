import { senderName } from "./ui.jsx";

export function AskModal({ event: e, people, settings, onChoose, onLater }) {
  const unsure = (q) => e.decision.reasons.find((r) => r.q === q && r.p > settings.noAt && r.p < settings.yesAt);
  const r = unsure("needs_sanad") ?? unsure("time_sensitive") ?? e.decision.reasons[0];
  const other = r?.q === "needs_sanad" ? "delegate" : "batch";
  return (
    <div className="modal">
      <div className="modal-card">
        <h3>Jev isn't sure. Your call, Sanad.</h3>
        <p><b>{senderName(e, people)}</b> at {e.time}: “{e.text}”</p>
        {r && <p className="muted">{r.q} = {r.p.toFixed(2)}, between “no” ({settings.noAt.toFixed(2)}) and “yes” ({settings.yesAt.toFixed(2)})</p>}
        <div className="choices">
          <button onClick={() => onChoose(e.id, "interrupt")}>🔔 Show me now</button>
          <button onClick={() => onChoose(e.id, other)}>{other === "delegate" ? "Forward it" : "Later is fine"}</button>
        </div>
        <button className="linkish" onClick={onLater}>decide later</button>
        <p className="muted small">Your answer is saved as feedback. It never changes Jev's answers or the metrics.</p>
      </div>
    </div>
  );
}

export function DigestModal({ digest, byId, onClose }) {
  return (
    <div className="modal" onClick={(ev) => ev.target === ev.currentTarget && onClose()}>
      <div className="modal-card">
        <h3>End-of-day digest</h3>
        <p className="muted">Everything Bouncer held back today, written by the LLM after the rules decided.</p>
        {digest.groups.length === 0 && <p>Nothing was held back.</p>}
        {digest.groups.map((g, i) => (
          <div className="digest-group" key={i}>
            <h4>{g.title}</h4>
            {g.items.map((it) => (
              <div className="digest-item" key={it.event_id}>
                <span className="muted">{byId[it.event_id]?.time ?? ""}</span> {it.summary}
                {it.draft_reply && <div className="draft">Draft reply: {it.draft_reply}</div>}
              </div>
            ))}
          </div>
        ))}
        <div className="choices"><button onClick={onClose}>Close</button></div>
      </div>
    </div>
  );
}
