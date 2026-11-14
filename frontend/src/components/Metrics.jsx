const pct = (x) => (x == null ? "–" : `${Math.round(x * 100)}%`);
const ms = (x) => (x == null ? "–" : x >= 1000 ? `${(x / 1000).toFixed(1)} s` : `${x} ms`);
const usd = (x) => (x == null ? "–" : x < 0.1 ? `$${x.toFixed(3)}` : `$${x.toFixed(2)}`);

// lower: true when a smaller number is better. Ties are not highlighted.
function Stat({ title, help, j, l, fmt, lower }) {
  const win = j == null || l == null || j === l ? null : (lower ? j < l : j > l) ? "j" : "l";
  return (
    <div className="stat">
      <div className="stat-title">{title}</div>
      <div className="stat-row">
        <div className={`stat-val ${win === "j" ? "win" : ""}`}><span className="who">Doorman</span>{fmt(j)}</div>
        <div className={`stat-val base ${win === "l" ? "win" : ""}`}><span className="who">LLM only</span>{fmt(l)}</div>
      </div>
      <p className="stat-help">{help}</p>
    </div>
  );
}

export default function Metrics({ m }) {
  if (!m) return <div className="page"><p className="muted">Loading…</p></div>;
  const j = m.jev, l = m.llm;
  const ratio = (a, b) => (a && b ? Math.round(b / a) : null);
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Insights</h1>
          <p>How Doorman's model compares with a large general-purpose model on the same {m.n} hand-labelled messages. Both answer the same questions, and the same rules decide.</p>
        </div>
      </div>
      {m.settings_changed && <div className="notice">Your rules differ from the defaults. The labels assume the defaults, so these numbers are indicative.</div>}

      <div className="highlights">
        <div className="highlight"><b>{ratio(j.cost_per_1k, l.cost_per_1k)}×</b><span>cheaper per decision</span></div>
        <div className="highlight"><b>{ratio(j.p50, l.p50)}×</b><span>faster per decision</span></div>
        <div className="highlight"><b>{j.critical_misses}</b><span>urgent message{j.critical_misses === 1 ? "" : "s"} missed · LLM only: {l.critical_misses}</span></div>
      </div>

      <div className="stats">
        <Stat title="Urgent messages missed" help="Messages that should have interrupted you but were held, forwarded or filtered." j={j.critical_misses} l={l.critical_misses} fmt={String} lower />
        <Stat title="Interruptions worth it" help="Of the times it interrupted you, how often it really should have." j={j.precision} l={l.precision} fmt={pct} />
        <Stat title="Cost per 1,000 messages" help="Measured from each model call's billed cost." j={j.cost_per_1k} l={l.cost_per_1k} fmt={usd} lower />
        <Stat title="Time to decide" help="Median time per message, measured from the laptop." j={j.p50} l={l.p50} fmt={ms} lower />
        <Stat title="Agrees with the labels" help="Asking you counts as a miss here." j={j.accuracy} l={l.accuracy} fmt={pct} />
        <Stat title="Agrees, when it didn't ask" help="The same, leaving out the messages where it asked you." j={j.accuracy_excl_asks} l={l.accuracy_excl_asks} fmt={pct} />
        <Stat title="Asked you instead of guessing" help="Times it wasn't sure whether a message needed you." j={j.asks} l={l.asks} fmt={String} lower />
        <Stat title="Held-out messages" help="Agreement on messages never looked at while writing the questions." j={j.holdout_accuracy} l={l.holdout_accuracy} fmt={pct} />
      </div>
      <p className="footnote">Doorman uses TypeSafe Jev 1.14; the comparison is Claude Sonnet 5.5. Fictional data, one day, {m.n} messages: read it as a demo, not a benchmark.</p>
    </div>
  );
}
