import { putSettings } from "../api.js";
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

export default function Settings({ settings: s, people, onChange }) {
  const save = async (patch) => onChange(await putSettings({ ...s, ...patch }));
  const toggle = (list, key, on) => save({ [list]: on ? [...new Set([...s[list], key])] : s[list].filter((x) => x !== key) });
  const humans = Object.values(people).filter((p) => !p.is_bot && p.key !== "sanad");
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
        <div className="people">
          <div className="people-head"><span>Person</span><span>Family</span><span>VIP <small>skips the budget</small></span></div>
          {humans.map((p) => (
            <div className="person" key={p.key}>
              <span><b>{p.name}</b> <small>{p.role}</small></span>
              <Toggle checked={s.family.includes(p.key)} label={`${p.name} is family`} onChange={(v) => toggle("family", p.key, v)} />
              <Toggle checked={s.vip.includes(p.key)} label={`${p.name} is VIP`} onChange={(v) => toggle("vip", p.key, v)} />
            </div>
          ))}
        </div>
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
