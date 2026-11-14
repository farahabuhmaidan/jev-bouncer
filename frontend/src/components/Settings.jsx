import { putSettings } from "../api.js";

export default function Settings({ settings: s, people, onClose, onChange }) {
  const save = async (patch) => onChange(await putSettings({ ...s, ...patch }));
  const range = (k, label, min, max, step) => (
    <label>{label}
      <input type="range" min={min} max={max} step={step} value={s[k]} onChange={(e) => save({ [k]: Number(e.target.value) })} />
      <span className="val">{s[k]}</span>
    </label>
  );
  const check = (k, label) => <label>{label}<input type="checkbox" checked={s[k]} onChange={(e) => save({ [k]: e.target.checked })} /></label>;
  const toggle = (list, key, on) => save({ [list]: on ? [...new Set([...s[list], key])] : s[list].filter((x) => x !== key) });
  const humans = Object.values(people).filter((p) => !p.is_bot);
  return (
    <aside className="drawer">
      <div className="drawer-head"><h2>Settings</h2><button onClick={onClose}>✕</button></div>
      <div className="form">
        <fieldset><legend>How sure is “sure”</legend>{range("yesAt", "yes at ≥", 0.5, 0.95, 0.05)}{range("noAt", "no at ≤", 0.05, 0.5, 0.05)}</fieldset>
        <fieldset><legend>Interrupts</legend>
          {range("interruptBar", "interrupt bar", 0.5, 0.95, 0.05)}{check("risingBar", "bar rises as budget runs out")}
          {range("budget", "daily budget", 1, 10, 1)}
          <label>evening starts<input type="time" value={s.eveningStart} onChange={(e) => e.target.value && save({ eveningStart: e.target.value })} /></label>
        </fieldset>
        <fieldset><legend>Rules</legend>{check("familyAlways", "family can always reach me")}{check("silentRerun", "rerun flaky CI silently")}</fieldset>
        <fieldset><legend>People</legend>
          <div className="person muted"><span /><span>family</span><span>VIP</span></div>
          {humans.map((p) => (
            <div className="person" key={p.key}>
              <span>{p.name} <span className="muted">{p.role}</span></span>
              <input type="checkbox" checked={s.family.includes(p.key)} onChange={(e) => toggle("family", p.key, e.target.checked)} />
              <input type="checkbox" checked={s.vip.includes(p.key)} onChange={(e) => toggle("vip", p.key, e.target.checked)} />
            </div>
          ))}
        </fieldset>
        <button onClick={async () => onChange(await putSettings({ yesAt: 0.7, noAt: 0.3, interruptBar: 0.7, risingBar: true, budget: 5, eveningStart: "18:00", familyAlways: true, silentRerun: true, family: ["maha", "school"], vip: [] }))}>Reset to defaults</button>
      </div>
      <p className="muted small">Saved on the server. Every change re-routes the whole day with the same Jev answers.</p>
    </aside>
  );
}
