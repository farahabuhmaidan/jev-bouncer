// Thin client for the Doorman API (design/14-app.md § API).
async function call(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok && res.status !== 502) throw new Error(data.detail ?? `HTTP ${res.status}`);
  return data;
}

export const getDay = () => call("GET", "/api/day");
export const getEvent = (id) => call("GET", `/api/events/${encodeURIComponent(id)}`);
export const postEvent = (body) => call("POST", "/api/events", body);
export const putSettings = (s) => call("PUT", "/api/settings", s);
export const setClock = (time) => call("POST", "/api/clock", { time });
export const feedback = (id, body) => call("POST", `/api/events/${encodeURIComponent(id)}/feedback`, body);
export const getMetrics = () => call("GET", "/api/metrics");
export const getDigest = () => call("GET", "/api/digest");
export const getPeople = () => call("GET", "/api/people");
export const getMoments = () => call("GET", "/api/moments");
export const reset = () => call("POST", "/api/reset");
export const getCalendar = () => call("GET", "/api/calendar");
export const reminderAction = (id, action) => call("POST", `/api/events/${encodeURIComponent(id)}/reminder`, { action });

export const toMin = (hhmm) => { const [h, m] = hhmm.split(":").map(Number); return h * 60 + m; };
export const toHHMM = (min) => `${String(Math.floor(min / 60)).padStart(2, "0")}:${String(min % 60).padStart(2, "0")}`;
