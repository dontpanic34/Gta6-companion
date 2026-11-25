import { Star } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, WEAPON_STAT_LABELS, WeaponSummary } from "../api";
import { StatBars } from "./Vehicles";

export default function Weapons() {
  const [sp, setSp] = useSearchParams();
  const [items, setItems] = useState<WeaponSummary[] | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => { setItems(null); api.weapons(sp).then(setItems).catch((e) => setErr(e.message)); }, [sp]);
  const classes = useMemo(() => [...new Set((items ?? []).map((w) => w.class).filter(Boolean))].sort() as string[], [items]);
  const set = (k: string, v: string | null) => { const n = new URLSearchParams(sp); v ? n.set(k, v) : n.delete(k); setSp(n, { replace: true }); };
  const cls = sp.get("wclass");

  return (
    <div className="page">
      <h1>Armes</h1>
      <input className="input" placeholder="Rechercher une arme…" value={sp.get("q") ?? ""} onChange={(e) => set("q", e.target.value)} />
      <div className="row" style={{ margin: "12px 0", overflowX: "auto", flexWrap: "nowrap" }}>
        <button className={`chip ${sp.get("ranked") ? "on" : ""}`} onClick={() => set("ranked", sp.get("ranked") ? null : "true")}><Star size={15} /> Classement</button>
        <button className={`chip ${sp.get("free_only") ? "on" : ""}`} onClick={() => set("free_only", sp.get("free_only") ? null : "true")}>Gratuites</button>
        <button className={`chip ${!cls ? "on" : ""}`} onClick={() => set("wclass", null)}>Toutes</button>
        {classes.map((c) => <button key={c} className={`chip ${cls === c ? "on" : ""}`} onClick={() => set("wclass", c)}>{c}</button>)}
      </div>
      {err && <p className="notice">{err}</p>}
      {!items && !err && <p className="muted">Chargement…</p>}
      <p className="muted small">{items?.length ?? 0} armes</p>
      <div className="grid">
        {items?.map((w) => (
          <Link key={w.id} to={`/armes/${encodeURIComponent(w.id)}`} className="card vcard">
            {w.image ? <img src={w.image} alt="" loading="lazy" referrerPolicy="no-referrer" style={{ objectFit: "contain" }} /> : <div className="thumb" />}
            <div className="row"><span className="title">{w.name}</span><span className="spacer" />
              {w.score && <span className="badge score">{w.score.value}</span>}</div>
            <div className="row small muted">
              <span>{w.class}</span>
              {w.price != null && <span>· {w.price.toLocaleString("fr-FR")} $</span>}
              {w.free_hint && <span className="badge">gratuite ?</span>}
              {w.variant_type !== "standard" && <span className="badge">variante</span>}
            </div>
            {Object.values(w.stats).some((v) => v != null) && <StatBars stats={w.stats} labels={WEAPON_STAT_LABELS} />}
          </Link>
        ))}
      </div>
    </div>
  );
}
