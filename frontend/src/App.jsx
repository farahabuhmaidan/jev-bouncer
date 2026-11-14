import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "./api.js";
import Header from "./components/Header.jsx";
import Compose from "./components/Compose.jsx";
import Inbox from "./components/Inbox.jsx";
import SenderView from "./components/SenderView.jsx";
import Why from "./components/Why.jsx";
import Phone from "./components/Phone.jsx";
import Settings from "./components/Settings.jsx";
import Metrics from "./components/Metrics.jsx";
import { AskModal, DigestModal } from "./components/Modals.jsx";
import { askChoice } from "./components/ui.jsx";

const DAY_END = 20 * 60;

export default function App() {
  const [day, setDay] = useState(null);
  const [people, setPeople] = useState({});
  const [moments, setMoments] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [selected, setSelected] = useState(null);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [showSettings, setShowSettings] = useState(false);
  const [senderView, setSenderView] = useState(false);
  const [digest, setDigest] = useState(null);
  const [error, setError] = useState(null);
  const lastIds = useRef(new Set());
  const digestShown = useRef(false);

  const refresh = useCallback(async () => {
    try {
      const d = await api.getDay();
      const fresh = d.events.filter((e) => !lastIds.current.has(e.id));
      if (fresh.length && lastIds.current.size) setSelected(fresh[0].id); // follow the newest arrival
      lastIds.current = new Set(d.events.map((e) => e.id));
      setDay(d); setError(null);
      return d;
    } catch (err) { setError(err.message); }
  }, []);
  const refreshMetrics = useCallback(() => api.getMetrics().then(setMetrics).catch(() => {}), []);

  useEffect(() => {
    api.getPeople().then((ps) => setPeople(Object.fromEntries(ps.map((p) => [p.key, p]))));
    api.getMoments().then(setMoments);
    refresh(); refreshMetrics();
    const t = setInterval(refresh, 1000); // live events and LLM text arrive by polling
    return () => clearInterval(t);
  }, [refresh, refreshMetrics]);

  // Only an ask that arrives now pops up; older ones wait in the Why panel ("Answer" there).
  const [dismissed, setDismissed] = useState(() => new Set());
  const pendingAsk = day?.events.find((e) => e.decision.action === "ask" && !askChoice(e) && !dismissed.has(e.id)
    && api.toMin(day.clock) - api.toMin(e.time) <= speed);

  // Play: the client advances the server clock 1 or 10 replay minutes per real second.
  useEffect(() => {
    if (!playing || !day || pendingAsk) return;
    const t = setTimeout(async () => {
      const next = Math.min(DAY_END, api.toMin(day.clock) + speed);
      await api.setClock(api.toHHMM(next));
      const d = await refresh();
      if (next >= DAY_END) {
        setPlaying(false);
        if (!digestShown.current) { digestShown.current = true; setDigest(await api.getDigest()); }
      }
      return d;
    }, 1000);
    return () => clearTimeout(t);
  }, [playing, day, speed, pendingAsk, refresh]);

  async function jump() {
    setPlaying(false);
    const now = api.toMin(day.clock);
    const next = moments.find((m) => api.toMin(m.time) - 1 > now);
    await api.setClock(next ? api.toHHMM(api.toMin(next.time) - 1) : "20:00");
    await refresh();
    if (next) { // step onto the moment one minute later so it lands on screen
      setTimeout(async () => { await api.setClock(next.time); await refresh(); }, 600);
    }
  }

  async function resetDay() {
    setPlaying(false); setSelected(null); digestShown.current = false; lastIds.current = new Set(); setDismissed(new Set());
    await api.reset(); await refresh(); refreshMetrics();
  }

  async function choose(id, choice) {
    await api.feedback(id, { kind: "ask", choice });
    await refresh();
  }

  useEffect(() => {
    const onKey = (ev) => {
      if (["INPUT", "SELECT", "TEXTAREA"].includes(ev.target.tagName)) return;
      if (ev.key === " ") { ev.preventDefault(); setPlaying((p) => !p); }
      if (ev.key === "n") jump();
      if (ev.key === "Escape") { setShowSettings(false); setDigest(null); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (!day) return <p className="muted pad">{error ? `Can't reach the Bouncer API: ${error}. Is \`make app\` running?` : "Loading…"}</p>;
  const byId = Object.fromEntries(day.events.map((e) => [e.id, e]));

  return (
    <div className="app">
      <Header day={day} playing={playing} speed={speed}
        onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onJump={jump}
        onSpeed={() => setSpeed((s) => (s === 1 ? 10 : 1))} onReset={resetDay}
        onSettings={() => setShowSettings(true)} senderView={senderView} onSenderView={() => setSenderView((v) => !v)}
        onDigest={async () => setDigest(await api.getDigest())} />
      {error && <div className="banner">⚠ {error}</div>}
      <main className="grid">
        <section className="panel feed">
          <h2>{senderView ? "Sender view · what people see back" : "Inbox"}</h2>
          {!senderView && <Compose people={people} onSent={async (out) => { setSelected(out.event.id); await refresh(); }} />}
          {senderView
            ? <SenderView events={day.events} people={people} onChange={refresh} />
            : <Inbox events={day.events} people={people} selected={selected} onSelect={setSelected} />}
        </section>
        <section className="panel why">
          <h2>Why</h2>
          <Why event={byId[selected]} people={people} settings={day.settings} onChoose={choose} />
        </section>
        <section className="panel phone-col">
          <h2>Sanad's phone</h2>
          <Phone day={day} people={people} onSelect={setSelected} />
        </section>
      </main>
      <Metrics m={metrics} />
      {showSettings && <Settings settings={day.settings} people={people} onClose={() => setShowSettings(false)}
        onChange={async () => { await refresh(); refreshMetrics(); }} />}
      {pendingAsk && <AskModal event={pendingAsk} people={people} settings={day.settings} onChoose={choose}
        onLater={() => setDismissed((s) => new Set([...s, pendingAsk.id]))} />}
      {digest && <DigestModal digest={digest} byId={byId} onClose={() => setDigest(null)} />}
    </div>
  );
}
