import { useState } from "react";
import { postEvent } from "../api.js";

const EXAMPLES = [
  { sender: "omar", text: "can you jump on a call about the pricing bug before the investor demo? it's broken for discounted plans" },
  { sender: "layla", text: "URGENT!!! pick a nicer font for slide 3 please!!!" },
  { sender: "noor", text: "a customer asks whether we have a dark mode, any idea?" },
];

export default function Compose({ people, onSent }) {
  const humans = Object.values(people).filter((p) => !p.is_bot);
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
      if (out.decision?.action === "error") setError(out.result?.jev?.error ?? "Jev call failed");
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
      <div className="compose-row">
        <select value={sender} onChange={(e) => setSender(e.target.value)} aria-label="Sender">
          {humans.map((p) => <option key={p.key} value={p.key}>{p.name}{p.role ? ` · ${p.role}` : ""}</option>)}
        </select>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Send Sanad a message, live…" aria-label="Message" />
        <button type="submit" disabled={busy || !text.trim()}>{busy ? "Jev is reading…" : "Send"}</button>
      </div>
      <div className="examples">
        {EXAMPLES.map((x, i) => (
          <button type="button" key={i} className="ex" onClick={() => { setSender(x.sender); setText(x.text); }}>
            {people[x.sender]?.name}: “{x.text.slice(0, 38)}…”
          </button>
        ))}
      </div>
      {error && <div className="error-line">⚠ {error}</div>}
    </form>
  );
}
