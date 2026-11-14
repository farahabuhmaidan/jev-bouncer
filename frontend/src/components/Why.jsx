import { Chip, askChoice, senderName } from "./ui.jsx";

function Bar({ q, p, used, s }) {
  const cls = p >= s.yesAt ? "yes" : p > s.noAt ? "unsure" : "";
  return (
    <>
      <div className={`q ${used ? "used" : ""}`}>{q}</div>
      <div className="track"><div className={`fill ${cls}`} style={{ width: `${Math.round(p * 100)}%` }} /></div>
      <div className="val">{p.toFixed(2)}</div>
    </>
  );
}

const deadlineText = (m, d) =>
  m == null ? "none" : `in ${m} minutes${d.rule === 5 ? " · rule 5 fired" : ""}`;

const ruleText = (d) => (d.rule === "error" ? "not routed" : typeof d.rule === "number" ? `message row ${d.rule}` : d.rule);

export default function Why({ event: e, people, settings, onChoose }) {
  if (!e) return <p className="muted">Click an event to see what Jev was shown, what it answered and which rule fired.</p>;
  const r = e.result ?? {}, d = e.decision, used = new Set(d.reasons.map((x) => x.q));
  const answers = r.jev?.answers ?? {};
  const bars = [];
  for (const [q, v] of Object.entries(answers)) {
    if (typeof v === "number") bars.push(<Bar key={q} q={q} p={v} used={used.has(q)} s={settings} />);
    else if (q === "failure_type") for (const [opt, p] of Object.entries(v)) bars.push(<Bar key={opt} q={`failure: ${opt}`} p={p} used={used.has(q)} s={settings} />);
  }
  return (
    <div>
      <h3 className="why-title">{senderName(e, people)} <span className="muted">at {e.time}</span></h3>
      <dl className="facts">
        <dt>Bouncer did</dt><dd><Chip action={d.action} label={d.label} /> {d.label}</dd>
        {d.action === "ask" && <><dt>Your call</dt><dd>{askChoice(e) ? <Chip action={askChoice(e)} /> : <>
          <button className="mini" onClick={() => onChoose(e.id, "interrupt")}>🔔 show me now</button>{" "}
          <button className="mini" onClick={() => onChoose(e.id, "batch")}>later is fine</button></>}</dd></>}
        <dt>Rule fired</dt><dd>{ruleText(d)}{d.uses_budget ? " · used 1 interrupt" : ""}{d.rule === 9 || d.uses_budget ? ` · bar ${d.bar.toFixed(2)}` : ""}</dd>
        {e.type === "message" && <><dt>Deadline</dt><dd>{deadlineText(r.facts?.deadline_in_minutes, d)}</dd></>}
        {e.baseline_decision && <><dt>Baseline + same policy</dt><dd><Chip action={e.baseline_decision.action} /> {ruleText(e.baseline_decision)}</dd></>}
        {e.label && <><dt>Label</dt><dd><Chip action={e.label.action} />{e.holdout && <span className="tag"> holdout</span>}</dd></>}
        {e.origin === "live" && <><dt>Source</dt><dd>live · {e.source}{e.source_time ? ` (sent ${e.source_time})` : ""}</dd></>}
      </dl>
      <h4>Jev's answers {r.jev?.latency_ms ? <span className="muted">· {r.jev.latency_ms} ms</span> : null}</h4>
      {r.jev?.error ? <p><span className="chip error">error</span> {r.jev.error}</p> : <div className="bars">{bars}</div>}
      {r.ci_explanation && (
        <div className="explain">
          <b>LLM explanation</b><br />{r.ci_explanation.likely_cause}
          {(r.ci_explanation.suspicious_lines ?? []).map((l, i) => <div key={i}><code>{l}</code></div>)}
          <i>Fix:</i> {r.ci_explanation.suggested_fix}
        </div>
      )}
      {r.llm_error && <p className="error-line">LLM: {r.llm_error}</p>}
      <h4>State sent to Jev</h4>
      <pre>{JSON.stringify(r.state, null, 2)}</pre>
    </div>
  );
}
