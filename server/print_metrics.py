"""`make eval` prints the README's numbers: the seeded day at default settings, from data/results.json."""
import json
from pathlib import Path

from .metrics import compute_metrics
from .policy import DEFAULTS, replay_day

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    r = json.loads((ROOT / "data" / "results.json").read_text())
    events, snap = r["day"]["events"], r["day"]["snapshot"]
    m = compute_metrics(events, replay_day(events, r["events"], snap, DEFAULTS), r["events"],
                        baseline=replay_day(events, r["events"], snap, DEFAULTS, source="baseline"))
    pct = lambda x: "–" if x is None else f"{int(x * 100 + 0.5)}%"  # noqa: E731
    ms = lambda x: "–" if x is None else f"{x} ms"  # noqa: E731
    usd = lambda x: "–" if x is None else f"${x:.3f}"  # noqa: E731
    n = lambda f: sum(1 for e in events if f(e))  # noqa: E731
    j, l = m["jev"], m["llm"]
    print(f"{r['models']['jev']} vs {r['models']['llm']}, run {r['generated_at']}")
    print(f"n = {len(events)} events ({n(lambda e: e['type'] == 'message')} messages, "
          f"{n(lambda e: e['type'] == 'ci_failure')} CI), holdout {n(lambda e: e.get('holdout'))}\n")
    print("| Metric (same policy, default settings) | Jev | LLM baseline |\n|---|---|---|")
    rows = [
        ("Critical misses (should have interrupted)", j["critical_misses"], l["critical_misses"]),
        ("Interrupt precision", pct(j["precision"]), pct(l["precision"])),
        ("False-alarm rate", pct(j["false_alarm_rate"]), pct(l["false_alarm_rate"])),
        ("Routing cost per 1,000 events", usd(j["cost_per_1k"]), usd(l["cost_per_1k"])),
        ("Latency per call, p50 / p95", f"{ms(j['p50'])} / {ms(j['p95'])}", f"{ms(l['p50'])} / {ms(l['p95'])}"),
        ("Accuracy, all events (ask = wrong)", pct(j["accuracy"]), pct(l["accuracy"])),
        ("Accuracy, excluding asks", pct(j["accuracy_excl_asks"]), pct(l["accuracy_excl_asks"])),
        ("Accuracy, holdout", pct(j["holdout_accuracy"]), pct(l["holdout_accuracy"])),
        ("Accuracy, messages", pct(j["by_type"]["message"]), pct(l["by_type"]["message"])),
        ("Accuracy, CI failures", pct(j["by_type"]["ci"]), pct(l["by_type"]["ci"])),
        ("Asks", j["asks"], l["asks"]),
        ("Errors", j["errors"], l["errors"]),
    ]
    for row in rows:
        print("| " + " | ".join(map(str, row)) + " |")


if __name__ == "__main__":
    main()
