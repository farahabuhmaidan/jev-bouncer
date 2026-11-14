import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { getCalendar, getCalendarRange, reminderAction } from "../api.js";
import { Icon } from "./ui.jsx";

// A full calendar (design/16, 17): day / week / month views over the connected calendar,
// with the reminders Doorman added drawn on top and clashes laid out side by side.

const HOUR = 48; // px per hour in day and week views
const pad = (n) => String(n).padStart(2, "0");
const toMin = (t) => { const [h, m] = t.split(":").map(Number); return h * 60 + m; };
const hhmm = (m) => `${pad(Math.floor(m / 60))}:${pad(m % 60)}`;
const parse = (iso) => { const [y, m, d] = iso.split("-").map(Number); return new Date(y, m - 1, d); };
const iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const addDays = (isoDate, n) => { const d = parse(isoDate); d.setDate(d.getDate() + n); return iso(d); };
const mondayOf = (isoDate) => { const d = parse(isoDate); return addDays(isoDate, -((d.getDay() + 6) % 7)); };
const firstOfMonth = (isoDate) => isoDate.slice(0, 8) + "01";
const fmt = (isoDate, opts) => parse(isoDate).toLocaleDateString("en-GB", opts);
const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function rangeFor(view, anchor) {
  if (view === "day") return { start: anchor, days: 1 };
  if (view === "week") return { start: mondayOf(anchor), days: 7 };
  return { start: mondayOf(firstOfMonth(anchor)), days: 42 };
}

function title(view, anchor, start) {
  if (view === "month") return fmt(anchor, { month: "long", year: "numeric" });
  if (view === "day") return fmt(anchor, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  const end = addDays(start, 6);
  const sameMonth = start.slice(0, 7) === end.slice(0, 7);
  return sameMonth
    ? `${fmt(start, { day: "numeric" })} – ${fmt(end, { day: "numeric", month: "long", year: "numeric" })}`
    : `${fmt(start, { day: "numeric", month: "short" })} – ${fmt(end, { day: "numeric", month: "short", year: "numeric" })}`;
}

// Side-by-side columns for overlapping items, like any calendar app.
function layout(items) {
  const sorted = [...items].sort((a, b) => a.s - b.s || b.e - a.e);
  const out = [];
  let cluster = [], cols = [], clusterEnd = -1;
  const flush = () => { cluster.forEach((it) => out.push({ ...it, ncols: cols.length })); cluster = []; cols = []; };
  for (const it of sorted) {
    if (it.s >= clusterEnd) { flush(); clusterEnd = -1; }
    let col = cols.findIndex((end) => end <= it.s);
    if (col === -1) { col = cols.length; cols.push(it.e); } else cols[col] = it.e;
    cluster.push({ ...it, col });
    clusterEnd = Math.max(clusterEnd, it.e);
  }
  flush();
  return out;
}

function MiniMonth({ month, selected, today, marks, onPick, onMonth }) {
  const start = mondayOf(firstOfMonth(month));
  const days = Array.from({ length: 42 }, (_, i) => addDays(start, i));
  return (
    <div className="mini">
      <div className="mini-head">
        <b>{fmt(month, { month: "long", year: "numeric" })}</b>
        <span>
          <button className="icon-btn sm" aria-label="Previous month" onClick={() => onMonth(-1)}><Icon name="chevronLeft" size={16} /></button>
          <button className="icon-btn sm" aria-label="Next month" onClick={() => onMonth(1)}><Icon name="chevronRight" size={16} /></button>
        </span>
      </div>
      <div className="mini-grid" role="grid">
        {WEEKDAYS.map((w) => <span key={w} className="mini-wd">{w[0]}</span>)}
        {days.map((d) => (
          <button key={d} onClick={() => onPick(d)} aria-label={fmt(d, { weekday: "long", day: "numeric", month: "long" })}
            className={`mini-day ${d.slice(0, 7) !== month.slice(0, 7) ? "out" : ""} ${d === today ? "is-today" : ""} ${d === selected ? "sel" : ""}`}>
            {Number(d.slice(8))}{marks.has(d) && <i />}
          </button>
        ))}
      </div>
    </div>
  );
}

function Popover({ pop, google, onClose, onAction, onOpenMessage }) {
  const ref = useRef(null);
  const [pos, setPos] = useState({ left: pop.x, top: pop.y });
  useLayoutEffect(() => {
    const r = ref.current.getBoundingClientRect();
    const left = Math.min(Math.max(12, pop.x), window.innerWidth - r.width - 12);
    const top = Math.min(Math.max(12, pop.y), window.innerHeight - r.height - 12);
    setPos({ left, top });
    ref.current.focus();
  }, [pop]);
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const it = pop.item, r = it.reminder;
  return (
    <>
      <div className="pop-scrim" onClick={onClose} />
      <div ref={ref} tabIndex={-1} role="dialog" aria-label={it.title} className="pop" style={pos}>
        <div className="pop-top">
          <span className={`pop-swatch ${r ? "rem" : "ev"}`} />
          <button className="icon-btn sm" onClick={onClose} aria-label="Close"><Icon name="x" size={16} /></button>
        </div>
        <h3>{it.title}</h3>
        <p className="pop-when">{fmt(it.date, { weekday: "long", day: "numeric", month: "long" })} · {hhmm(it.s)} – {hhmm(it.e)}</p>
        {r ? (
          <>
            <p className="pop-line"><Icon name="door" size={14} />Doorman reminder, from {r.sender?.split(/ [(,]|,/)[0]}</p>
            <blockquote>“{r.message}”</blockquote>
            <p className="pop-line muted"><Icon name="clock" size={14} />Read as “{r.phrase}”</p>
            {r.clashes.length > 0 && (
              <p className="pop-clash"><Icon name="alert" size={14} />Clashes with {r.clashes.map((c) => `${c.title} (${c.start}–${c.end})`).join(", ")}</p>
            )}
            {r.google?.link && <p className="pop-line"><Icon name="check" size={14} /><a href={r.google.link} target="_blank" rel="noreferrer">In Google Calendar</a></p>}
            <div className="pop-actions">
              {r.suggested && <button className="btn small primary" onClick={() => onAction(r.event_id, "move")}><Icon name="clock" size={14} />Move to {r.suggested}</button>}
              {google && !r.google && <button className="btn small" onClick={() => onAction(r.event_id, "push")}><Icon name="calendar" size={14} />Add to Google Calendar</button>}
              <button className="btn small" onClick={() => onOpenMessage(r.event_id)}><Icon name="inbox" size={14} />Open message</button>
              <button className="btn small ghost" onClick={() => onAction(r.event_id, "remove")}><Icon name="trash" size={14} />Remove</button>
            </div>
          </>
        ) : (
          <p className="pop-line muted"><Icon name="calendar" size={14} />{google ? "Your Google Calendar" : "Demo calendar"}</p>
        )}
      </div>
    </>
  );
}

function TimeGrid({ dates, byDate, today, clock, onOpen }) {
  const scroller = useRef(null);
  useEffect(() => { if (scroller.current) scroller.current.scrollTop = 7.5 * HOUR; }, []);
  const nowMin = toMin(clock);
  return (
    <div className="tg">
      <div className="tg-head" style={{ gridTemplateColumns: `56px repeat(${dates.length}, 1fr)` }}>
        <span />
        {dates.map((d) => (
          <div key={d} className={`tg-day ${d === today ? "is-today" : ""}`}>
            <span className="tg-wd">{fmt(d, { weekday: "short" }).toUpperCase()}</span>
            <span className="tg-num">{Number(d.slice(8))}</span>
          </div>
        ))}
      </div>
      <div className="tg-body" ref={scroller}>
        <div className="tg-inner" style={{ gridTemplateColumns: `56px repeat(${dates.length}, 1fr)`, height: 24 * HOUR }}>
          <div className="tg-hours">
            {Array.from({ length: 24 }, (_, h) => <span key={h} style={{ top: h * HOUR }}>{h ? `${pad(h)}:00` : ""}</span>)}
          </div>
          {dates.map((d) => (
            <div key={d} className="tg-col">
              {layout(byDate[d] || []).map((it) => {
                const top = (it.s / 60) * HOUR, height = Math.max(20, ((it.e - it.s) / 60) * HOUR - 2);
                // Overlaps cascade like a desk calendar: each later column starts further right and sits on top.
                const step = 90 / it.ncols, left = it.col * step;
                const width = it.ncols === 1 ? 100 : it.col === it.ncols - 1 ? 100 - left : step + 10;
                return (
                  <button key={it.key} className={`blk ${it.reminder ? "rem" : "ev"} ${it.clash ? "clash" : ""} ${height < 36 ? "short" : ""}`}
                    style={{ top, height, left: `calc(${left}% + 2px)`, width: `calc(${width}% - 6px)`, zIndex: 1 + it.col }}
                    onClick={(e) => onOpen(it, e)} aria-label={`${it.title}, ${hhmm(it.s)} to ${hhmm(it.e)}${it.clash ? ", clashes" : ""}`}>
                    <span className="blk-title">{it.reminder && <Icon name="door" size={11} />}{it.clash && <Icon name="alert" size={11} />}{it.title}</span>
                    <span className="blk-time">{hhmm(it.s)} – {hhmm(it.e)}</span>
                  </button>
                );
              })}
              {d === today && <div className="now" style={{ top: (nowMin / 60) * HOUR }}><i /></div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MonthGrid({ dates, month, byDate, today, onOpen, onDay }) {
  return (
    <div className="mg">
      <div className="mg-head">{WEEKDAYS.map((w) => <span key={w}>{w.toUpperCase()}</span>)}</div>
      <div className="mg-grid">
        {dates.map((d) => {
          const items = [...(byDate[d] || [])].sort((a, b) => a.s - b.s);
          return (
            <div key={d} className={`mg-cell ${d.slice(0, 7) !== month.slice(0, 7) ? "out" : ""}`}>
              <button className={`mg-num ${d === today ? "is-today" : ""}`} onClick={() => onDay(d)} aria-label={`Open ${fmt(d, { day: "numeric", month: "long" })}`}>{Number(d.slice(8))}</button>
              {items.slice(0, 3).map((it) => (
                <button key={it.key} className={`chip-ev ${it.reminder ? "rem" : "ev"} ${it.clash ? "clash" : ""}`} onClick={(e) => onOpen(it, e)}>
                  <i />{hhmm(it.s)} {it.title}
                </button>
              ))}
              {items.length > 3 && <button className="mg-more" onClick={() => onDay(d)}>{items.length - 3} more</button>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function CalendarPage({ version, clock, onOpenMessage }) {
  const [view, setView] = useState(() => (window.innerWidth < 760 ? "day" : "week"));
  const [anchor, setAnchor] = useState("2026-11-14");
  const [mini, setMini] = useState("2026-11-01");
  const [range, setRange] = useState(null);
  const [cal, setCal] = useState(null);
  const [show, setShow] = useState({ events: true, reminders: true });
  const [pop, setPop] = useState(null);
  const [err, setErr] = useState(null);
  const { start, days } = rangeFor(view, anchor);

  const load = () => {
    setErr(null);
    getCalendar().then(setCal).catch((e) => setErr(e.message));
    return getCalendarRange(start, days).then(setRange).catch((e) => setErr(e.message));
  };
  useEffect(() => { load(); }, [start, days, version]); // eslint-disable-line react-hooks/exhaustive-deps

  const today = cal?.today ?? "2026-11-14";
  const google = cal ? !cal.connection.demo : false;
  const reminders = cal?.reminders ?? [];
  const dates = Array.from({ length: days }, (_, i) => addDays(start, i));

  const byDate = useMemo(() => {
    const out = {};
    const push = (d, it) => { (out[d] ||= []).push(it); };
    if (range && show.events) {
      range.days.forEach((day) => day.events.forEach((e, i) => {
        const s = toMin(e.start), en = Math.max(s + 15, toMin(e.end));
        const clash = reminders.some((r) => r.date === day.date && r.clashes.some((c) => c.title === e.title && c.start === e.start));
        push(day.date, { key: `e-${day.date}-${i}`, date: day.date, title: e.title, s, e: en, clash });
      }));
    }
    if (show.reminders) {
      reminders.forEach((r) => {
        const s = toMin(r.time);
        push(r.date, { key: `r-${r.event_id}`, date: r.date, title: r.title, s, e: s + r.minutes, reminder: r, clash: r.clashes.length > 0 });
      });
    }
    return out;
  }, [range, reminders, show]);

  const move = (n) => {
    const next = view === "day" ? addDays(anchor, n) : view === "week" ? addDays(anchor, 7 * n)
      : iso(new Date(parse(anchor).getFullYear(), parse(anchor).getMonth() + n, 1));
    setAnchor(next); setMini(firstOfMonth(next));
  };
  const goTo = (d, v) => { setAnchor(d); setMini(firstOfMonth(d)); if (v) setView(v); };
  const open = (it, ev) => { const r = ev.currentTarget.getBoundingClientRect(); setPop({ item: it, x: r.right + 8, y: r.top }); };
  const act = async (id, action) => {
    try { await reminderAction(id, action); setPop(null); await load(); } catch (e) { setErr(e.message); }
  };
  const marks = new Set(reminders.map((r) => r.date));
  const upcoming = [...reminders].sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time));

  return (
    <div className="calapp">
      <aside className="cal-side" aria-label="Calendar navigation">
        <MiniMonth month={mini} selected={anchor} today={today} marks={marks} onPick={(d) => goTo(d)}
          onMonth={(n) => setMini(iso(new Date(parse(mini).getFullYear(), parse(mini).getMonth() + n, 1)))} />

        <div className="side-sec">
          <h4>Calendars</h4>
          <label className="cal-check ev"><input type="checkbox" checked={show.events} onChange={(e) => setShow({ ...show, events: e.target.checked })} />
            <span className="box" />{google ? cal.connection.account : "Sanad (demo calendar)"}</label>
          <label className="cal-check rem"><input type="checkbox" checked={show.reminders} onChange={(e) => setShow({ ...show, reminders: e.target.checked })} />
            <span className="box" />Doorman reminders</label>
        </div>

        <div className="side-sec">
          <h4>Reminders from messages</h4>
          {upcoming.length === 0 && <p className="hint">None yet. Try a test message like “you need to pay school fees next month”.</p>}
          <ul className="up-list">
            {upcoming.map((r) => (
              <li key={r.event_id}>
                <button onClick={(e) => { goTo(r.date, view === "month" ? "week" : view); const rect = e.currentTarget.getBoundingClientRect(); setPop({ item: { key: `r-${r.event_id}`, date: r.date, title: r.title, s: toMin(r.time), e: toMin(r.time) + r.minutes, reminder: r }, x: rect.right + 8, y: rect.top }); }}>
                  <span className="up-date"><b>{Number(r.date.slice(8))}</b>{fmt(r.date, { month: "short" })}</span>
                  <span className="up-body"><b>{r.title}</b><small>{fmt(r.date, { weekday: "short" })} · {r.time}{r.clashes.length > 0 && <em> · clash</em>}</small></span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        {cal && (
          <p className="side-conn"><span className={`dot ${google ? "" : "off"}`} />{google ? `Google Calendar · ${cal.connection.account}` : "Demo calendar · connect a real one in Rules"}</p>
        )}
      </aside>

      <section className="cal-main" aria-label="Calendar">
        <div className="cal-toolbar">
          <button className="btn small" onClick={() => goTo(today)}>Today</button>
          <button className="icon-btn" aria-label="Previous" onClick={() => move(-1)}><Icon name="chevronLeft" /></button>
          <button className="icon-btn" aria-label="Next" onClick={() => move(1)}><Icon name="chevronRight" /></button>
          <h1>{title(view, anchor, start)}</h1>
          <div className="seg" role="tablist" aria-label="View">
            {["day", "week", "month"].map((v) => (
              <button key={v} role="tab" aria-selected={view === v} className={view === v ? "active" : ""} onClick={() => setView(v)}>{v[0].toUpperCase() + v.slice(1)}</button>
            ))}
          </div>
        </div>
        {err && <p className="error-line cal-err"><Icon name="alert" size={14} />{err}</p>}
        {view === "month"
          ? <MonthGrid dates={dates} month={anchor} byDate={byDate} today={today} onOpen={open} onDay={(d) => goTo(d, "day")} />
          : <TimeGrid key={view + start} dates={dates} byDate={byDate} today={today} clock={clock} onOpen={open} />}
      </section>

      {pop && <Popover pop={pop} google={google} onClose={() => setPop(null)} onAction={act} onOpenMessage={(id) => { setPop(null); onOpenMessage(id); }} />}
    </div>
  );
}
