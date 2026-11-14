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
      <div className="legend"><b className="ok">Jev</b> / LLM baseline<br />same policy · {m.n} labelled events</div>
      <Cell k="critical misses" j={m.jev.critical_misses} l={m.llm.critical_misses} />
      <Cell k="interrupt precision" j={pct(m.jev.precision)} l={pct(m.llm.precision)} />
      <Cell k="cost / 1k events" j={usd(m.jev.cost_per_1k)} l={usd(m.llm.cost_per_1k)} />
      <Cell k="p50 latency" j={ms(m.jev.p50)} l={ms(m.llm.p50)} />
      <Cell k="accuracy" j={pct(m.jev.accuracy)} l={pct(m.llm.accuracy)} />
      <Cell k="excl. asks" j={pct(m.jev.accuracy_excl_asks)} l={pct(m.llm.accuracy_excl_asks)} />
      <Cell k="asks" j={m.jev.asks} l={m.llm.asks} />
      {m.settings_changed && <div className="note">settings changed: labels assume defaults</div>}
    </footer>
  );
}
