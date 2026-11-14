const pct = (x) => (x === null || x === undefined ? "–" : `${Math.round(x * 100)}%`);
const ms = (x) => (x == null ? "–" : x >= 1000 ? `${(x / 1000).toFixed(1)}s` : `${x}ms`);
const usd = (x) => (x == null ? "–" : x < 0.1 ? `$${x.toFixed(3)}` : `$${x.toFixed(2)}`);

function Cell({ k, j, l }) {
  return <div className="metric"><div className="k">{k}</div><div className="v"><span className="j">{j}</span>{l !== undefined && <span className="l"> / {l}</span>}</div></div>;
}

export default function Metrics({ m }) {
  if (!m) return null;
  return (
    <footer className="panel metrics">
      <div className="legend"><b className="ok">Jev + rules</b> / LLM-only<br />{m.n} labelled events · full day</div>
      <Cell k="accuracy" j={pct(m.jev.accuracy)} l={pct(m.llm.accuracy)} />
      <Cell k="holdout" j={pct(m.jev.holdout_accuracy)} l={pct(m.llm.holdout_accuracy)} />
      <Cell k="critical misses" j={m.jev.critical_misses} l={m.llm.critical_misses} />
      <Cell k="asks" j={m.jev.asks} />
      <Cell k="p50 latency" j={ms(m.jev.p50)} l={ms(m.llm.p50)} />
      <Cell k="cost / 1k events" j={usd(m.jev.cost_per_1k)} l={usd(m.llm.cost_per_1k)} />
      {m.settings_changed && <div className="note">settings changed: labels assume defaults</div>}
    </footer>
  );
}
