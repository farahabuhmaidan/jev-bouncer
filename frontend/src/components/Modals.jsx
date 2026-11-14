import { useEffect, useRef } from "react";
import { Avatar, Icon, eventText, senderName, senderRole } from "./ui.jsx";

function Dialog({ title, onClose, children, labelledBy }) {
  const ref = useRef(null);
  useEffect(() => { ref.current?.querySelector("button")?.focus(); }, []);
  return (
    <div className="overlay" onClick={(ev) => onClose && ev.target === ev.currentTarget && onClose()}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby={labelledBy} ref={ref}>
        {title}
        {children}
      </div>
    </div>
  );
}

export function AskModal({ event: e, people, settings, onChoose, onLater }) {
  // Unsure whether Sanad is needed → the other option is forwarding; unsure about timing → later.
  const forwardable = e.decision.reasons.some((r) => r.q === "needs_sanad" && r.p > settings.noAt && r.p < settings.yesAt);
  return (
    <Dialog labelledBy="ask-title" onClose={onLater} title={
      <div className="dialog-head"><span className="dialog-icon ask"><Icon name="help" size={18} /></span>
        <div><h2 id="ask-title">Quick question</h2><p>Doorman isn't sure this needs you. Your call.</p></div></div>}>
      <div className="ask-msg">
        <Avatar e={e} people={people} />
        <div><b>{senderName(e, people)}</b> <small>{senderRole(e, people)} · {e.time}</small><p>{eventText(e)}</p></div>
      </div>
      <div className="dialog-actions">
        <button className="btn primary" onClick={() => onChoose(e.id, "interrupt")}><Icon name="bell" />Show me now</button>
        <button className="btn" onClick={() => onChoose(e.id, forwardable ? "delegate" : "batch")}>
          {forwardable ? <><Icon name="forward" />Someone else can take it</> : <><Icon name="clock" />Later is fine</>}
        </button>
      </div>
      <button className="link" onClick={onLater}>Decide later</button>
    </Dialog>
  );
}

export function DigestModal({ digest, byId, onClose }) {
  return (
    <Dialog labelledBy="digest-title" onClose={onClose} title={
      <div className="dialog-head"><span className="dialog-icon"><Icon name="file" size={18} /></span>
        <div><h2 id="digest-title">Your daily summary</h2><p>Everything Doorman held for you today, with draft replies.</p></div>
        <button className="icon-btn push" onClick={onClose} aria-label="Close"><Icon name="x" /></button></div>}>
      {digest.groups.length === 0 && <p className="muted">Nothing was held back today.</p>}
      {digest.groups.map((g, i) => (
        <section className="digest-group" key={i}>
          <h3>{g.title}</h3>
          {g.items.map((it) => (
            <div className="digest-item" key={it.event_id}>
              <span className="time">{byId[it.event_id]?.time ?? ""}</span>
              <div>
                <p>{it.summary}</p>
                {it.draft_reply && <p className="draft"><Icon name="reply" size={12} />{it.draft_reply}</p>}
              </div>
            </div>
          ))}
        </section>
      ))}
    </Dialog>
  );
}
