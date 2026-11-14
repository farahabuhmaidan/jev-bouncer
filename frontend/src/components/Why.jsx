import Reminder from "./Reminder.jsx";
import { Avatar, Icon, SIGNALS, Status, askChoice, eventText, explain, senderName, senderRole, sourceName, statusText } from "./ui.jsx";

function Signal({ q, p, used, s }) {
  const level = p >= s.yesAt ? "yes" : p > s.noAt ? "unsure" : "no";
  const word = { yes: "Yes", unsure: "Unsure", no: "No" }[level];
  return (
    <div className={`signal ${used ? "used" : ""}`}>
      <div className="sig-name">{SIGNALS[q] ?? q}{used && <span className="sig-used">used</span>}</div>
      <div className="sig-track" aria-hidden="true"><div className={`sig-fill ${level}`} style={{ width: `${Math.round(p * 100)}%` }} /></div>
      <div className={`sig-val ${level}`}>{word} <span>{Math.round(p * 100)}%</span></div>
    </div>
  );
}

const ruleRef = (d) => (d.rule === "error" ? "not routed" : typeof d.rule === "number" ? `rule ${d.rule}` : d.rule);

export default function Why({ event: e, people, settings, onChoose, onChange, google }) {
  if (!e) {
    return (
      <div className="empty tall">
        <Icon name="shield" size={30} />
        <p><b>Select a message</b><br />to see what Doorman did with it, and why.</p>
      </div>
    );
  }
  const r = e.result ?? {}, d = e.decision, used = new Set(d.reasons.map((x) => x.q));
  const answers = r.jev?.answers ?? {};
  const chosen = askChoice(e);
  const signals = Object.entries(answers).filter(([, v]) => typeof v === "number");
  const failure = answers.failure_type;
  const deadline = r.facts?.deadline_in_minutes;
  const isPerson = e.type === "message" && people[e.sender] && !people[e.sender].is_bot;

  return (
    <article className="detail">
      <header className="detail-head">
        <Avatar e={e} people={people} />
        <div>
          <h2>{senderName(e, people)}</h2>
          <p className="sub">{senderRole(e, people)} · {sourceName(e.source)} · {e.time}</p>
        </div>
      </header>

      <blockquote className="original">{eventText(e)}</blockquote>

      <section className={`verdict v-${chosen ?? d.action}`}>
        <Status decision={d} chosen={chosen} />
        <p>{explain(e, d, people)}</p>
        {d.action === "ask" && !chosen && (
          <div className="actions">
            <button className="btn primary" onClick={() => onChoose(e.id, "interrupt")}><Icon name="bell" />Show me now</button>
            <button className="btn" onClick={() => onChoose(e.id, "batch")}><Icon name="clock" />Later is fine</button>
          </div>
        )}
        {deadline != null && e.type === "message" && (
          <p className="fact"><Icon name="timer" size={14} />Deadline in {deadline} minutes{d.rule === 5 ? " · that's why it got through" : ""}</p>
        )}
      </section>

      {d.action === "batch" && isPerson && (r.auto_reply || r.writing) && (
        <section className="card">
          <h3><Icon name="reply" size={14} />Auto-reply sent to {senderName(e, people)}</h3>
          <p className={r.auto_reply ? "" : "muted"}>{r.auto_reply ?? "Writing…"}</p>
        </section>
      )}

      <Reminder eventId={e.id} reminder={r.reminder} onChange={onChange} google={google} />

      {r.ci_explanation && (
        <section className="card">
          <h3><Icon name="code" size={14} />What probably broke</h3>
          <p>{r.ci_explanation.likely_cause}</p>
          {(r.ci_explanation.suspicious_lines ?? []).map((l, i) => <pre key={i} className="code-line">{l}</pre>)}
          <p><b>Suggested fix:</b> {r.ci_explanation.suggested_fix}</p>
        </section>
      )}
      {r.llm_error && <p className="error-line"><Icon name="alert" size={14} />The text writer failed: {r.llm_error}</p>}

      <section className="card">
        <h3>What Doorman read in it</h3>
        {r.jev?.error
          ? <p className="error-line"><Icon name="alert" size={14} />{r.jev.error}</p>
          : <>
            {failure && (
              <div className="signal used">
                <div className="sig-name">Most likely cause<span className="sig-used">used</span></div>
                <div className="sig-text">{Object.entries(failure).sort((a, b) => b[1] - a[1])[0][0].replace(/_/g, " ")}</div>
                <div className="sig-val">{Math.round(Math.max(...Object.values(failure)) * 100)}%</div>
              </div>
            )}
            {signals.map(([q, p]) => <Signal key={q} q={q} p={p} used={used.has(q)} s={settings} />)}
          </>}
        <p className="hint">The highlighted signals decided the outcome. Doorman's model only answers these questions; fixed rules make the decision.</p>
      </section>

      <details className="tech">
        <summary><Icon name="code" size={14} />Technical details</summary>
        <dl>
          <dt>Rule</dt><dd>{ruleRef(d)}{d.uses_budget ? ` · used 1 interruption (bar ${d.bar.toFixed(2)})` : ""}</dd>
          <dt>Model</dt><dd>Jev{r.jev?.latency_ms ? ` · ${r.jev.latency_ms} ms` : ""}</dd>
          {e.baseline_decision && <><dt>LLM baseline, same rules</dt><dd>{statusText(e.baseline_decision)} · {ruleRef(e.baseline_decision)}</dd></>}
          {e.label && <><dt>Hand label</dt><dd>{e.label.action}{e.holdout ? " · holdout" : ""}</dd></>}
          {e.source_time && <><dt>Sent at</dt><dd>{e.source_time}</dd></>}
        </dl>
        <h4>Exactly what the model saw</h4>
        <pre>{JSON.stringify(r.state, null, 2)}</pre>
      </details>
    </article>
  );
}
