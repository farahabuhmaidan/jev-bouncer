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
import CalendarPage from "./components/CalendarPage.jsx";
import { AskModal, DigestModal } from "./components/Modals.jsx";
import { Icon, askChoice } from "./components/ui.jsx";

const DAY_END = 20 * 60;

export default function App() {
  const [day, setDay] = useState(null);
  const [people, setPeople] = useState({});
  const [moments, setMoments] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [selected, setSelected] = useState(null);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [tab, setTab] = useState("today");
  const [filter, setFilter] = useState("all");
  const [composing, setComposing] = useState(false);
  const [senderView, setSenderView] = useState(false);
  const [digest, setDigest] = useState(null);
  const [error, setError] = useState(null);
  const [showPhone, setShowPhone] = useState(() => { try { return localStorage.getItem("doorman.phone") !== "hidden"; } catch { return true; } });
  const togglePhone = () => setShowPhone((v) => { try { localStorage.setItem("doorman.phone", v ? "hidden" : "shown"); } catch { /* private mode */ } return !v; });
  const loadPeople = useCallback(() => api.getPeople().then((ps) => setPeople(Object.fromEntries(ps.map((p) => [p.key, p])))), []);
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
    loadPeople();
    api.getMoments().then(setMoments);
    refresh(); refreshMetrics();
    const t = setInterval(refresh, 1000); // live events and LLM text arrive by polling
    return () => clearInterval(t);
  }, [refresh, refreshMetrics, loadPeople]);

  useEffect(() => { if (tab === "insights") refreshMetrics(); }, [tab, refreshMetrics]);

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
    const next = moments.find((m) => api.toMin(m.time) > now);
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
      if (ev.key === "p" && tab === "today") togglePhone();
      if (ev.key === "Escape") { setDigest(null); setComposing(false); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (!day) return <p className="boot">{error ? `Can't reach the Doorman server: ${error}. Is \`make app\` running?` : "Loading…"}</p>;
  const byId = Object.fromEntries(day.events.map((e) => [e.id, e]));

  const onChanged = async () => { await refresh(); refreshMetrics(); };
  return (
    <div className="app">
      <Header day={day} tab={tab} onTab={setTab} playing={playing} speed={speed}
        onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onJump={jump}
        onSpeed={() => setSpeed((s) => (s === 1 ? 10 : 1))} onReset={resetDay}
        onDigest={async () => setDigest(await api.getDigest())} />
      {error && <div className="banner" role="alert"><Icon name="alert" size={14} />{error}</div>}

      {tab === "today" && (
        <main className={`today ${showPhone ? "" : "no-phone"}`}>
          <section className="col list-col" aria-label="Messages">
            <div className="col-head">
              <div>
                <h1>{senderView ? "What senders see" : "Today"}</h1>
                <p>{senderView ? "Colleagues you held get an auto-reply, and can still reach you." : `${day.events.length} messages so far`}</p>
              </div>
              <div className="head-actions">
                <button className={`btn small ${senderView ? "active" : ""}`} onClick={() => setSenderView((v) => !v)} aria-pressed={senderView}>
                  <Icon name="user" size={14} />Sender view</button>
                {!senderView && <button className="btn small primary" onClick={() => setComposing((c) => !c)}><Icon name="send" size={14} />Test message</button>}
              </div>
            </div>
            {composing && !senderView && <Compose people={people} onClose={() => setComposing(false)}
              onSent={async (out) => { setSelected(out.event.id); setFilter("all"); await refresh(); }} />}
            <div className="scroll">
              {senderView
                ? <SenderView events={day.events} people={people} onChange={refresh} />
                : <Inbox events={day.events} people={people} selected={selected} onSelect={setSelected} filter={filter} onFilter={setFilter} />}
            </div>
          </section>
          <section className="col detail-col" aria-label="Details">
            <div className="scroll"><Why event={byId[selected]} people={people} settings={day.settings} onChoose={choose} onChange={refresh} /></div>
          </section>
          {showPhone ? (
            <aside className="col phone-col" aria-label="Phone preview">
              <div className="col-head"><div><h1 className="small-h">On your phone</h1><p>Only what got through</p></div>
                <div className="head-actions">
                  <a className="icon-btn" href="/phone" target="_blank" rel="noreferrer" aria-label="Open the phone view in a new tab" title="Open on a phone"><Icon name="phone" /></a>
                  <button className="icon-btn" onClick={togglePhone} aria-label="Hide the phone" title="Hide the phone (p)"><Icon name="eyeOff" /></button>
                </div></div>
              <Phone day={day} people={people} onSelect={(id) => { setSelected(id); setFilter("all"); }} />
            </aside>
          ) : (
            <button className="phone-rail" onClick={togglePhone} aria-label="Show the phone" title="Show the phone (p)">
              <Icon name="phone" size={18} /><span>Show phone</span>
              {day.phone.length > 0 && <b className="rail-count">{day.phone.length}</b>}
            </button>
          )}
        </main>
      )}
      {tab === "calendar" && <CalendarPage version={day.events.length} />}
      {tab === "insights" && <Metrics m={metrics} />}
      {tab === "rules" && <Settings settings={day.settings} people={people} onChange={onChanged} onPeople={loadPeople} />}

      <footer className="foot">
        <span>Doorman · decisions by fixed rules on judgments from TypeSafe Jev</span>
        <a href="/test">Test bench</a><a href="/slides/">Slides</a>
      </footer>
      {pendingAsk && <AskModal event={pendingAsk} people={people} settings={day.settings} onChoose={choose}
        onLater={() => setDismissed((s) => new Set([...s, pendingAsk.id]))} />}
      {digest && <DigestModal digest={digest} byId={byId} onClose={() => setDigest(null)} />}
    </div>
  );
}
