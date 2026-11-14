import { useEffect, useState } from "react";
import { getDay, getPeople, postEvent } from "../api.js";
import Why from "./Why.jsx";
import { Chip } from "./ui.jsx";

// /test: send any notification and see exactly what Bouncer does with it.
const PRESETS = [
  { name: "Loud but cosmetic", type: "message", source: "slack", sender: "layla", text: "URGENT!!! change the deck font to something bolder!!!" },
  { name: "Quiet but broken", type: "message", source: "slack", sender: "rami", text: "hm, discounted plans show a negative total at checkout?" },
  { name: "Outside sales email", type: "message", source: "email", sender: "__other", senderName: "Acme Corp sales", text: "Last chance: 40% off our analytics suite, offer ends today!" },
  { name: "Family, can wait", type: "message", source: "slack", sender: "maha", text: "can you grab milk on the way home? no rush" },
  { name: "Flaky CI", type: "ci_failure", source: "github_actions", branch: "main", testName: "test_checkout_badge", commitMessage: "Bump eslint", logTail: "FAILED tests/test_badge.py::test_checkout_badge - TimeoutError: element not visible after 5000ms\nRetry 1/1 passed locally" },
];

const blank = { type: "message", source: "slack", sender: "rami", senderName: "", channel: "", time: "", text: "",
  branch: "", testName: "", commitMessage: "", logTail: "", dryRun: true };

export default function TestPage() {
  const [people, setPeople] = useState({});
  const [settings, setSettings] = useState(null);
  const [f, setF] = useState(blank);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [runs, setRuns] = useState([]);
  const [shown, setShown] = useState(0);

  useEffect(() => {
    getPeople().then((ps) => setPeople(Object.fromEntries(ps.map((p) => [p.key, p]))));
    getDay().then((d) => { setSettings(d.settings); setF((x) => ({ ...x, time: x.time || d.clock })); });
  }, []);

  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  async function send(e) {
    e.preventDefault();
    setBusy(true); setError(null);
    const body = f.type === "ci_failure"
      ? { type: "ci_failure", source: f.source, branch: f.branch, test_name: f.testName, commit_message: f.commitMessage, log_tail: f.logTail }
      : { type: "message", source: f.source, text: f.text, channel: f.channel || undefined,
          ...(f.sender === "__other" ? { sender_name: f.senderName } : { sender: f.sender }) };
    try {
      const out = await postEvent({ ...body, time: f.time || undefined, dry_run: f.dryRun });
      setRuns((r) => [{ out, at: new Date().toLocaleTimeString() }, ...r]);
      setShown(0);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  const run = runs[shown]?.out;
  const asEvent = run && { ...run.event, result: run.result, decision: run.decision, feedback: [] };
  const humans = Object.values(people).filter((p) => !p.is_bot);

  return (
    <div className="app">
      <header className="bar">
        <div className="brand">Bouncer <span className="sub">test bench</span></div>
        <div className="controls"><a className="btnlink" href="/">← back to the app</a></div>
      </header>
      <main className="test-grid">
        <section className="panel">
          <h2>Notification</h2>
          <div className="presets">{PRESETS.map((p) => <button key={p.name} className="ex" onClick={() => setF({ ...blank, time: f.time, ...p })}>{p.name}</button>)}</div>
          <form className="test-form" onSubmit={send}>
            <label>Type<select value={f.type} onChange={set("type")}><option value="message">message</option><option value="ci_failure">CI failure</option></select></label>
            <label>Source<select value={f.source} onChange={set("source")}>
              {["slack", "email", "gmail", "teams", "whatsapp", "compose", "github_actions"].map((s) => <option key={s}>{s}</option>)}</select></label>
            <label>Time<input type="time" value={f.time} onChange={set("time")} /></label>
            {f.type === "message" ? <>
              <label>Sender<select value={f.sender} onChange={set("sender")}>
                {humans.map((p) => <option key={p.key} value={p.key}>{p.name}{p.role ? ` · ${p.role}` : ""}</option>)}
                {Object.values(people).filter((p) => p.is_bot).map((p) => <option key={p.key} value={p.key}>{p.name} (bot)</option>)}
                <option value="__other">someone else…</option></select></label>
              {f.sender === "__other" && <label>Name<input value={f.senderName} onChange={set("senderName")} placeholder="e.g. Acme Corp sales" /></label>}
              <label>Channel<input value={f.channel} onChange={set("channel")} placeholder="Slack DM, #checkout, Email…" /></label>
              <label className="wide">Text<textarea rows={5} value={f.text} onChange={set("text")} placeholder="What does the notification say?" /></label>
            </> : <>
              <label>Branch<input value={f.branch} onChange={set("branch")} placeholder="main" /></label>
              <label>Test<input value={f.testName} onChange={set("testName")} placeholder="test_checkout_total" /></label>
              <label className="wide">Commit message<input value={f.commitMessage} onChange={set("commitMessage")} /></label>
              <label className="wide">Log tail<textarea rows={7} value={f.logTail} onChange={set("logTail")} placeholder="paste the failing output" /></label>
            </>}
            <label className="wide check"><input type="checkbox" checked={f.dryRun} onChange={set("dryRun")} /> dry run (don't add it to the inbox)</label>
            <button type="submit" className="primary wide" disabled={busy}>{busy ? "Jev is reading… (LLM text may take a few seconds)" : "Send to Bouncer"}</button>
            {error && <div className="error-line wide">⚠ {error}</div>}
          </form>
          {runs.length > 0 && <>
            <h2 style={{ marginTop: 18 }}>This session</h2>
            <ol className="list">{runs.map((r, i) => (
              <li key={i} className={`item ${i === shown ? "selected" : ""}`} onClick={() => setShown(i)}>
                <div className="top"><span className="time">{r.at}</span><span className="who">{r.out.event.type === "ci_failure" ? r.out.event.test_name : r.out.result.state.sender}</span></div>
                <div className="meta"><Chip action={r.out.decision.action} label={r.out.decision.label} /><span className="tag">{r.out.decision.label}</span>{r.out.dry_run ? <span className="tag">dry run</span> : <span className="tag live-tag">in inbox</span>}</div>
              </li>))}</ol>
          </>}
        </section>
        <section className="panel">
          <h2>Response</h2>
          {!run ? <p className="muted">Send a notification to see the decision, Jev's answers, the state it saw and what the LLM wrote.</p> : <>
            <div className="verdict-card">
              <Chip action={run.decision.action} label={run.decision.label} />
              <span className="big">{run.decision.action === "error" ? "not routed" : run.decision.label || run.decision.action}</span>
            </div>
            {run.result.auto_reply && <div className="reply">↩ auto-reply: {run.result.auto_reply}</div>}
            <div className="why">
              {settings && <Why event={asEvent} people={people} settings={settings} onChoose={() => {}} />}
              <details><summary>Raw API response</summary><pre>{JSON.stringify(run, null, 2)}</pre></details>
            </div>
          </>}
        </section>
      </main>
    </div>
  );
}
