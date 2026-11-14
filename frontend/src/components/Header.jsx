export default function Header({ day, playing, speed, onPlay, onPause, onJump, onSpeed, onReset, onSettings, senderView, onSenderView, onDigest }) {
  const { clock, budget, evening } = day;
  return (
    <header className="bar">
      <div className="brand">Bouncer <span className="sub">Sanad's attention, guarded</span></div>
      <div className={`clock ${evening ? "evening" : ""}`}>{clock}{evening ? " 🌙" : ""}</div>
      <div className="controls">
        {playing ? <button onClick={onPause} title="Pause (space)">⏸</button> : <button onClick={onPlay} title="Play (space)">▶</button>}
        <button onClick={onJump} title="Jump to the next demo moment (n)">⏭ moment</button>
        <button onClick={onSpeed} title="Replay speed">{speed}x</button>
        <button onClick={onReset} title="Back to 08:00, remove live messages">↺</button>
      </div>
      <div className="budget" title={`${budget.left} of ${budget.total} interrupts left today`}>
        <span className="label">interrupts</span>
        {Array.from({ length: budget.total }, (_, i) => <span key={i} className={`dot ${i < budget.left ? "left" : ""}`} />)}
      </div>
      <div className="controls">
        <button onClick={onSettings}>⚙ settings</button>
        <button className={senderView ? "on" : ""} onClick={onSenderView}>👤 sender view</button>
        <button onClick={onDigest}>📋 digest</button>
        <a className="btnlink" href="/phone" target="_blank" rel="noreferrer">📱 phone</a>
      </div>
    </header>
  );
}
