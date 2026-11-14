import { useEffect, useState } from "react";
import { getDay, getPeople, postEvent } from "../api.js";
import Why from "./Why.jsx";
import { Icon, Status } from "./ui.jsx";

// /test: send any notification and see exactly what Doorman does with it.
const PRESETS = [
  { name: "Loud but cosmetic", type: "message", source: "slack", sender: "layla", text: "URGENT!!! change the deck font to something bolder!!!" },
  { name: "Quiet but broken", type: "message", source: "slack", sender: "rami", text: "hm, discounted plans show a negative total at checkout?" },
  { name: "Customer deadline", type: "message", source: "gmail", sender: "hadi", text: "We need the export fixed before 16:00 today, our finance team closes the month then." },
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
  const asEvent = run && { ...run.event, result: run.result, decision: run.decision, baseline_decision: null, feedback: [] };
  const humans = Object.values(people).filter((p) => !p.is_bot);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand"><span className="logo"><Icon name="door" size={18} /></span><span className="wordmark">Doorman</span></div>
        <span className="pill"><Icon name="flask" size={12} />Test bench</span>
        <a className="btn small" href="/" style={{ marginLeft: "auto", textDecoration: "none", color: "inherit" }}>Back to the app</a>
      </header>
      <main className="bench">
        <section className="col">
          <h2>Notification</h2>
          <div className="presets">{PRESETS.map((p) => <button key={p.name} className="pill-btn" onClick={() => setF({ ...blank, time: f.time, ...p })}>{p.name}</button>)}</div>
          <form className="test-form" onSubmit={send}>
            <label>Type<select value={f.type} onChange={set("type")}><option value="message">Message</option><option value="ci_failure">CI failure</option></select></label>
            <label>Source<select value={f.source} onChange={set("source")}>
              {["slack", "email", "gmail", "teams", "whatsapp", "compose", "github_actions"].map((s) => <option key={s}>{s}</option>)}</select></label>
            <label>Time<input type="time" value={f.time} onChange={set("time")} /></label>
            {f.type === "message" ? <>
              <label>Sender<select value={f.sender} onChange={set("sender")}>
                {humans.map((p) => <option key={p.key} value={p.key}>{p.name}{p.role ? ` · ${p.role}` : ""}</option>)}
                {Object.values(people).filter((p) => p.is_bot).map((p) => <option key={p.key} value={p.key}>{p.name} (bot)</option>)}
                <option value="__other">Someone else…</option></select></label>
              {f.sender === "__other" && <label>Name<input value={f.senderName} onChange={set("senderName")} placeholder="e.g. Acme Corp sales" /></label>}
              <label>Channel<input value={f.channel} onChange={set("channel")} placeholder="Slack DM, #checkout, Email…" /></label>
              <label className="wide">Text<textarea rows={5} value={f.text} onChange={set("text")} placeholder="What does the notification say?" /></label>
            </> : <>
              <label>Branch<input value={f.branch} onChange={set("branch")} placeholder="main" /></label>
              <label>Test<input value={f.testName} onChange={set("testName")} placeholder="test_checkout_total" /></label>
              <label className="wide">Commit message<input value={f.commitMessage} onChange={set("commitMessage")} /></label>
              <label className="wide">Log tail<textarea rows={7} value={f.logTail} onChange={set("logTail")} placeholder="Paste the failing output" /></label>
            </>}
            <label className="wide check"><input type="checkbox" checked={f.dryRun} onChange={set("dryRun")} /> Dry run (don't add it to today's messages)</label>
            <button type="submit" className="btn primary wide" disabled={busy}>{busy ? <><span className="spinner" />Doorman is reading…</> : <><Icon name="send" />Send to Doorman</>}</button>
            {error && <p className="error-line wide"><Icon name="alert" size={14} />{error}</p>}
          </form>
          {runs.length > 0 && (
            <ol className="runs">{runs.map((r, i) => (
              <li key={i}><button className={i === shown ? "selected" : ""} onClick={() => setShown(i)}>
                <span className="time" style={{ margin: 0 }}>{r.at}</span>
                <b>{r.out.event.type === "ci_failure" ? r.out.event.test_name : r.out.result.state.sender.split(",")[0]}</b>
                <Status decision={r.out.decision} />
                <span className="pill">{r.out.dry_run ? "Dry run" : "Added"}</span>
              </button></li>))}</ol>
          )}
        </section>
        <section className="col">
          {!run
            ? <div className="empty tall"><Icon name="flask" size={30} /><p><b>Send a notification</b><br />to see the decision, the signals, what the model saw and what the LLM wrote.</p></div>
            : <>
              {settings && <Why event={asEvent} people={people} settings={settings} onChoose={() => {}} />}
              <details className="raw"><summary>Raw API response</summary><pre>{JSON.stringify(run, null, 2)}</pre></details>
            </>}
        </section>
      </main>
    </div>
  );
}
