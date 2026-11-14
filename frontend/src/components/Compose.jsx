import { useState } from "react";
import { postEvent } from "../api.js";
import { Icon } from "./ui.jsx";

const EXAMPLES = [
  { sender: "omar", label: "Real blocker", text: "can you jump on a call about the pricing bug before the investor demo? it's broken for discounted plans" },
  { sender: "layla", label: "Loud, not urgent", text: "URGENT!!! pick a nicer font for slide 3 please!!!" },
  { sender: "noor", label: "Someone else can answer", text: "a customer asks whether we have a dark mode, any idea?" },
];

export default function Compose({ people, onSent, onClose }) {
  const humans = Object.values(people).filter((p) => !p.is_bot && p.key !== "sanad");
  const [sender, setSender] = useState("omar");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function send(e) {
    e?.preventDefault();
    if (!text.trim() || busy) return;
    setBusy(true); setError(null);
    try {
      const out = await postEvent({ sender, text });
      if (out.decision?.action === "error") setError(out.result?.jev?.error ?? "The model call failed");
      setText("");
      onSent(out);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="compose" onSubmit={send}>
      <div className="compose-head">
        <h3>Send a test message</h3>
        <button type="button" className="icon-btn" onClick={onClose} aria-label="Close"><Icon name="x" /></button>
      </div>
      <label className="field">
        <span>From</span>
        <select value={sender} onChange={(e) => setSender(e.target.value)}>
          {humans.map((p) => <option key={p.key} value={p.key}>{p.name}{p.role ? ` · ${p.role}` : ""}</option>)}
        </select>
      </label>
      <label className="field">
        <span>Message</span>
        <textarea rows={3} value={text} onChange={(e) => setText(e.target.value)} placeholder="Type what they'd send you…"
          onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) send(e); }} />
      </label>
      <div className="examples">
        <span>Try:</span>
        {EXAMPLES.map((x) => (
          <button type="button" key={x.label} className="pill-btn" onClick={() => { setSender(x.sender); setText(x.text); }}>{x.label}</button>
        ))}
      </div>
      {error && <p className="error-line" role="alert"><Icon name="alert" size={14} />{error}</p>}
      <button type="submit" className="btn primary block" disabled={busy || !text.trim()}>
        {busy ? <><span className="spinner" />Doorman is reading…</> : <><Icon name="send" />Send</>}
      </button>
    </form>
  );
}
