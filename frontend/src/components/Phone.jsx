import { Icon, eventText, senderName } from "./ui.jsx";

export default function Phone({ day, people, onSelect }) {
  const byId = Object.fromEntries(day.events.map((e) => [e.id, e]));
  const items = day.phone.map((id) => byId[id]).filter(Boolean);
  return (
    <div className={`phone ${day.evening ? "evening" : ""}`}>
      <div className="phone-notch" />
      <div className="phone-status">
        <span>{day.clock}</span>
        <span>{day.evening ? <><Icon name="moon" size={12} /> Quiet hours</> : "Doorman on"}</span>
      </div>
      <ol className="notifs">
        {items.length === 0 && <li className="phone-empty"><Icon name="shield" size={22} /><span>No interruptions yet.<br />Doorman is holding the door.</span></li>}
        {items.map((e) => {
          const rerouted = e.decision.action !== "interrupt";
          return (
            <li key={e.id}>
              <button className={`notif ${rerouted ? "rerouted" : ""}`} onClick={() => onSelect?.(e.id)}>
                <div className="n-head"><span className="n-app"><Icon name="door" size={11} />Doorman</span><span>{e.time}</span></div>
                <div className="n-title">{senderName(e, people)}</div>
                <div className="n-body">{eventText(e)}</div>
                {e.result?.ci_explanation && <div className="n-extra">Likely cause: {e.result.ci_explanation.likely_cause}</div>}
                {rerouted && <div className="n-extra warn">The sender marked this as urgent</div>}
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
