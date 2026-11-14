import { useState } from "react";
import { addPerson, deletePerson, gmailSync, googleDisconnect, putSettings } from "../api.js";
import { Icon } from "./ui.jsx";

const DEFAULTS = { yesAt: 0.7, noAt: 0.3, interruptBar: 0.7, risingBar: true, budget: 5, eveningStart: "18:00",
  familyAlways: true, silentRerun: true, family: ["maha", "school"], vip: [], deadlineMinutes: 120 };

function Row({ title, help, children }) {
  return (
    <div className="setting">
      <div className="setting-text"><b>{title}</b><p>{help}</p></div>
      <div className="setting-control">{children}</div>
    </div>
  );
}

function Toggle({ checked, onChange, label }) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label} className={`switch ${checked ? "on" : ""}`} onClick={() => onChange(!checked)}>
      <span />
    </button>
  );
}

function PeopleList({ title, icon, help, members, people, onAdd, onRemove, onCreate }) {
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [err, setErr] = useState(null);
  const humans = Object.values(people).filter((p) => !p.is_bot && p.key !== "sanad");
  const match = humans.find((p) => p.name.toLowerCase() === name.trim().toLowerCase());
  const close = () => { setAdding(false); setName(""); setRole(""); setErr(null); };
  const submit = async (ev) => {
    ev.preventDefault();
    if (!name.trim()) return;
    try {
      if (match) { if (!members.includes(match.key)) await onAdd(match.key); }
      else await onCreate(name.trim(), role.trim());
      close();
    } catch (e) { setErr(e.message); }
  };
  return (
    <div className="plist">
      <div className="plist-head">
        <div><b><Icon name={icon} size={14} />{title}</b><p>{help}</p></div>
        {!adding && <button type="button" className="btn small" onClick={() => setAdding(true)}><Icon name="plus" size={14} />Add</button>}
      </div>
      <ul className="chips">
        {members.length === 0 && <li className="hint">Nobody yet.</li>}
        {members.map((k) => (
          <li key={k} className="person-chip">
            <span className="avatar xs">{(people[k]?.name ?? k).split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase()}</span>
            <span><b>{people[k]?.name ?? k}</b>{people[k]?.role && <small> · {people[k].role}</small>}</span>
            <button type="button" aria-label={`Remove ${people[k]?.name ?? k} from ${title}`} title={`Remove from ${title}`} onClick={() => onRemove(k)}><Icon name="x" size={12} /></button>
          </li>
        ))}
      </ul>
      {adding && (
        <form className="padd" onSubmit={submit}>
          <label><span>Name</span>
            <input className="input" autoFocus autoComplete="off" value={name} placeholder="Any name, e.g. Rana Haddad" onChange={(e) => setName(e.target.value)} /></label>
          {match
            ? <p className="hint padd-match"><Icon name="check" size={12} />Already a contact: {match.name}, {match.role}. Messages from them will follow this rule.</p>
            : <label><span>Who are they? <small>optional</small></span>
                <input className="input" autoComplete="off" value={role} placeholder="e.g. Sister, Head of Sales" onChange={(e) => setRole(e.target.value)} /></label>}
          <div className="padd-actions">
            <button className="btn small primary" type="submit" disabled={!name.trim()}>{match ? `Add ${match.name}` : "Add new person"}</button>
            <button className="btn small" type="button" onClick={close}>Cancel</button>
          </div>
          {err && <p className="error-line"><Icon name="alert" size={14} />{err}</p>}
        </form>
      )}
    </div>
  );
}

function Connections({ conn, onConn, onRouted }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  if (!conn) return <p className="hint">Checking connections…</p>;
  const g = conn.google;
  const run = async (fn) => { setBusy(true); setMsg(null); try { await fn(); } catch (e) { setMsg({ ok: false, text: e.message }); } finally { setBusy(false); } };
  const fetchMail = () => run(async () => {
    const out = await gmailSync(10);
    await onRouted();
    setMsg({ ok: true, text: out.added.length ? `Routed ${out.added.length} new email${out.added.length > 1 ? "s" : ""} into Today.` : "No new mail since the last fetch." });
  });
  const live = (on, text) => <span className="conn">{on ? <span className="dot" /> : <span className="dot off" />}{text}</span>;
  return (
    <>
      <Row title="Google account" help={g.connected
        ? "Doorman reads your inbox when you fetch mail, and checks your real calendar for clashes. It only writes to your calendar when you press “Add to Google Calendar”."
        : g.configured
          ? "Connect to use your real Gmail and Google Calendar instead of the demo data. You can disconnect any time."
          : "Not set up on this server. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env and restart (see design/17). Until then Doorman uses demo data."}>
        {g.connected
          ? <div className="conn-actions">{live(true, g.account)}<button className="btn small" disabled={busy} onClick={() => run(async () => { await googleDisconnect(); await onConn(); })}>Disconnect</button></div>
          : <a className={`btn small primary ${g.configured ? "" : "disabled"}`} href={g.configured ? "/api/connections/google/start" : undefined} aria-disabled={!g.configured}><Icon name="link" size={14} />Connect Google account</a>}
      </Row>
      <Row title="Google Calendar" help="Reminders for tasks with a later date, checked for clashes.">
        {conn.calendar.source === "google" ? live(true, `Your calendar · ${conn.calendar.account}`) : live(false, <>Demo calendar · sanad@example.com <span className="pill">Demo data</span></>)}
      </Row>
      <Row title="Gmail" help={conn.gmail.source === "google" ? "Fetch your newest inbox mail (last day, up to 10). Each new email is routed like any message: one Jev call each." : "The demo day's email comes from sample Gmail messages."}>
        {conn.gmail.source === "google"
          ? <button className="btn small" disabled={busy} onClick={fetchMail}><Icon name="inbox" size={14} />{busy ? "Fetching…" : "Fetch new mail"}</button>
          : live(false, <>Demo inbox <span className="pill">Demo data</span></>)}
      </Row>
      {msg && <p className={msg.ok ? "hint ok-line" : "error-line"} role="status"><Icon name={msg.ok ? "check" : "alert"} size={14} />{msg.text}</p>}
    </>
  );
}

export default function Settings({ settings: s, people, onChange, onPeople, conn, onConn }) {
  const save = async (patch) => onChange(await putSettings({ ...s, ...patch }));
  const create = async (name, role, relationship, list) => {
    const p = await addPerson({ name, role, relationship });
    await onPeople();
    await save({ [list]: [...new Set([...s[list], p.key])] });
  };
  const remove = async (key) => { await deletePerson(key); await onPeople(); await onChange(); };
  const custom = Object.values(people).filter((p) => p.custom);
  const toggle = (list, key, on) => save({ [list]: on ? [...new Set([...s[list], key])] : s[list].filter((x) => x !== key) });
  const stepper = (k, min, max, step, unit) => (
    <div className="stepper">
      <button type="button" aria-label={`Less ${k}`} disabled={s[k] <= min} onClick={() => save({ [k]: Math.max(min, s[k] - step) })}>−</button>
      <output>{s[k]}{unit}</output>
      <button type="button" aria-label={`More ${k}`} disabled={s[k] >= max} onClick={() => save({ [k]: Math.min(max, s[k] + step) })}>+</button>
    </div>
  );
  const range = (k, min, max, step) => (
    <div className="range"><input type="range" min={min} max={max} step={step} value={s[k]} aria-label={k}
      onChange={(e) => save({ [k]: Number(e.target.value) })} /><output>{Math.round(s[k] * 100)}%</output></div>
  );

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Rules</h1>
          <p>Decide when Doorman lets things through. Changes apply to the whole day instantly.</p>
        </div>
        <button className="btn" onClick={async () => onChange(await putSettings(DEFAULTS))}><Icon name="reset" />Restore defaults</button>
      </div>

      <section className="panel-card">
        <h2>Interruptions</h2>
        <Row title="Daily interruption budget" help="How many times a day Doorman may interrupt you for something time-sensitive.">{stepper("budget", 1, 10, 1, "")}</Row>
        <Row title="Raise the bar as the day fills up" help="Each interruption used makes the next one a little harder to earn.">
          <Toggle checked={s.risingBar} label="Raise the bar" onChange={(v) => save({ risingBar: v })} />
        </Row>
        <Row title="Deadlines always get through" help="A message with a deadline sooner than this interrupts you, without using the budget.">{stepper("deadlineMinutes", 15, 480, 15, " min")}</Row>
        <Row title="Quiet hours start" help="After this time, only family and release blockers reach you. Everything else waits for the morning.">
          <input type="time" className="input" value={s.eveningStart} onChange={(e) => e.target.value && save({ eveningStart: e.target.value })} />
        </Row>
      </section>

      <section className="panel-card">
        <h2>People</h2>
        <Row title="Family can always reach me" help="Family messages get through any time, unless they can clearly wait.">
          <Toggle checked={s.familyAlways} label="Family can always reach me" onChange={(v) => save({ familyAlways: v })} />
        </Row>
        <PeopleList title="Family" icon="user" members={s.family} people={people}
          help="Always get through, unless the message can clearly wait. New messages tell Jev they're family."
          onAdd={(k) => toggle("family", k, true)} onRemove={(k) => toggle("family", k, false)}
          onCreate={(name, role) => create(name, role, "family", "family")} />
        <PeopleList title="VIPs" icon="shield" members={s.vip} people={people}
          help="Time-sensitive messages from them get through without using your daily budget."
          onAdd={(k) => toggle("vip", k, true)} onRemove={(k) => toggle("vip", k, false)}
          onCreate={(name, role) => create(name, role, "contact", "vip")} />
        {custom.length > 0 && (
          <div className="people-added">
            <span className="hint">People you added:</span>
            {custom.map((p) => (
              <span key={p.key} className="person-chip">{p.name}
                <button type="button" aria-label={`Delete ${p.name}`} title="Delete this person" onClick={() => remove(p.key)}><Icon name="trash" size={12} /></button>
              </span>
            ))}
          </div>
        )}
      </section>

      <section className="panel-card">
        <h2>Connections</h2>
        <Connections conn={conn} onConn={onConn} onRouted={onChange} />
      </section>

      <section className="panel-card">
        <h2>Engineering</h2>
        <Row title="Rerun flaky tests silently" help="When CI fails on a known-flaky test, Doorman reruns it instead of telling you.">
          <Toggle checked={s.silentRerun} label="Rerun flaky tests silently" onChange={(v) => save({ silentRerun: v })} />
        </Row>
      </section>

      <details className="panel-card advanced">
        <summary><h2>Advanced: how sure is sure</h2></summary>
        <Row title="Counts as yes from" help="Doorman treats an answer as yes at or above this confidence.">{range("yesAt", 0.5, 0.95, 0.05)}</Row>
        <Row title="Counts as no up to" help="Between no and yes, Doorman asks you instead of guessing.">{range("noAt", 0.05, 0.5, 0.05)}</Row>
        <Row title="Interruption bar" help="How sure Doorman must be that something can't wait before it spends your budget.">{range("interruptBar", 0.5, 0.95, 0.05)}</Row>
      </details>
    </div>
  );
}
