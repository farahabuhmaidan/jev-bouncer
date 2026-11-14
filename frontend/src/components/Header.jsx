import { Icon } from "./ui.jsx";

const TABS = [
  { key: "today", label: "Today", icon: "inbox" },
  { key: "calendar", label: "Calendar", icon: "calendar" },
  { key: "rules", label: "Rules", icon: "sliders" },
];

export default function Header({ day, tab, onTab, playing, speed, onPlay, onPause, onJump, onSpeed, onReset, onDigest }) {
  const { clock, budget, evening } = day;
  const used = budget.total - budget.left;
  return (
    <header className="topbar">
      <div className="brand">
        <span className="logo"><Icon name="door" size={18} /></span>
        <span className="wordmark">Doorman</span>
      </div>
      <nav className="tabs" aria-label="Main">
        {TABS.map((t) => (
          <button key={t.key} className={`tab ${tab === t.key ? "active" : ""}`} aria-current={tab === t.key ? "page" : undefined}
            onClick={() => onTab(t.key)}>
            <Icon name={t.icon} size={16} />{t.label}
          </button>
        ))}
        <button className="tab" onClick={onDigest}><Icon name="file" size={16} />Daily summary</button>
      </nav>

      <div className="budget-meter" title="Doorman interrupts you at most this many times a day. Deadlines, release blockers and family don't count.">
        <div className="bm-label"><span>Interruptions today</span><b>{used} of {budget.total}</b></div>
        <div className="bm-track">{Array.from({ length: budget.total }, (_, i) => <span key={i} className={i < used ? "on" : ""} />)}</div>
      </div>

      <div className="demo" role="group" aria-label="Demo day controls">
        <span className="demo-label">Demo day</span>
        <span className={`clock ${evening ? "evening" : ""}`}>{evening && <Icon name="moon" size={14} />}{clock}</span>
        {playing
          ? <button className="icon-btn" onClick={onPause} aria-label="Pause" title="Pause (space)"><Icon name="pause" /></button>
          : <button className="icon-btn" onClick={onPlay} aria-label="Play the day" title="Play (space)"><Icon name="play" /></button>}
        <button className="icon-btn" onClick={onJump} aria-label="Next moment" title="Jump to the next demo moment (n)"><Icon name="next" /></button>
        <button className="icon-btn text" onClick={onSpeed} aria-label="Playback speed" title="Playback speed">{speed}×</button>
        <button className="icon-btn" onClick={onReset} aria-label="Restart the day" title="Back to 08:00, remove test messages"><Icon name="reset" /></button>
      </div>
    </header>
  );
}
