import { useEffect, useState } from "react";
import { getDay, getPeople } from "../api.js";
import Phone from "./Phone.jsx";

// /phone: open on a real phone on the same wifi (http://<laptop-ip>:8000/phone).
export default function PhoneOnly() {
  const [day, setDay] = useState(null);
  const [people, setPeople] = useState({});
  useEffect(() => {
    getPeople().then((ps) => setPeople(Object.fromEntries(ps.map((p) => [p.key, p]))));
    const tick = () => getDay().then(setDay).catch(() => {});
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, []);
  if (!day) return <p className="boot">Connecting…</p>;
  return <div className="phone-only"><Phone day={day} people={people} /></div>;
}
