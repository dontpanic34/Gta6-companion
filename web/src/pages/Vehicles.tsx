import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, DRIVETRAIN_FR, STAT_LABELS, Stats, VehicleSummary } from "../api";

const STAT_KEYS = Object.keys(STAT_LABELS) as (keyof Stats)[];
const DRIVES = ["RWD", "FWD", "AWD"];

export function StatBars({ stats, labels = STAT_LABELS }: { stats: Record<string, number | null>; labels?: Record<string, string> }) {
  return (
    <div style={{ display: "grid", gap: 4 }}>
      {Object.keys(labels).map((k) => (
        <div className="stat" key={k}>
          <span className="muted">{labels[k]}</span>
          <div className="bar"><i style={{ width: `${((stats[k] ?? 0) / 10) * 100}%` }} /></div>
          <span>{stats[k] ?? "—"}</span>
        </div>
      ))}
    </div>
  );
}

export default function Vehicles() {
  const [sp, setSp] = useSearchParams();
  const [items, setItems] = useState<VehicleSummary[] | null>(null);
  const [err, setErr] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const nav = useNavigate();

  useEffect(() => {
    setItems(null);
    api.vehicles(sp).then(setItems).catch((e) => setErr(e.message));
  }, [sp]);

  const classes = useMemo(() => [...new Set((items ?? []).map((v) => v.class).filter(Boolean))].sort() as string[], [items]);
  const set = (k: string, v: string | null) => { const n = new URLSearchParams(sp); v === null || v === "" ? n.delete(k) : n.set(k, v); setSp(n, { replace: true }); };
  const toggleMulti = (k: string, v: string) => {
    const n = new URLSearchParams(sp); const cur = n.getAll(k); n.delete(k);
    (cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v]).forEach((x) => n.append(k, x));
    setSp(n, { replace: true });
  };
  const toggleSel = (id: string) => setSelected((s) => s.includes(id) ? s.filter((x) => x !== id) : s.length < 4 ? [...s, id] : s);
  const profile = sp.get("use_profile") === "true";
  const activeCount = [...sp.keys()].filter((k) => k !== "q" && k !== "use_profile").length;

  return (
    <div className="page">
      <h1>Véhicules</h1>
      <input className="input" placeholder="Rechercher un véhicule…" value={sp.get("q") ?? ""} onChange={(e) => set("q", e.target.value)} />
      <div className="row" style={{ margin: "12px 0", overflowX: "auto", flexWrap: "nowrap" }}>
        <button className={`chip ${profile ? "on" : ""}`} onClick={() => set("use_profile", profile ? null : "true")}>★ Mon style</button>
        <button className={`chip ${activeCount ? "on" : ""}`} onClick={() => setShowFilters(true)}>Filtres{activeCount ? ` (${activeCount})` : ""}</button>
        <button className={`chip ${sp.getAll("exclude_class").includes("Muscle") ? "on" : ""}`} onClick={() => toggleMulti("exclude_class", "Muscle")}>Sans muscle cars</button>
        <button className={`chip ${sp.get("min_handling_offroad") ? "on" : ""}`} onClick={() => set("min_handling_offroad", sp.get("min_handling_offroad") ? null : "6")}>Bon hors route</button>
        <button className={`chip ${sp.getAll("drivetrain").includes("AWD") ? "on" : ""}`} onClick={() => toggleMulti("drivetrain", "AWD")}>Intégrale</button>
      </div>
      {profile && <p className="notice">Classement selon votre profil (Réglages). Le score ne compte que les stats connues ; la couverture est indiquée.</p>}
      {err && <p className="notice">{err}</p>}
      {!items && !err && <p className="muted">Chargement…</p>}
      {items && items.length === 0 && <div className="empty">Aucun véhicule ne correspond.</div>}
      <p className="muted small">{items?.length ?? 0} véhicules</p>
      <div className="grid">
        {items?.map((v) => (
          <div key={v.id} className="card vcard">
            <Link to={`/vehicules/${encodeURIComponent(v.id)}`}>
              {v.image ? <img src={v.image} alt="" loading="lazy" referrerPolicy="no-referrer" /> : <div className="thumb" />}
            </Link>
            <button className={`check ${selected.includes(v.id) ? "on" : ""}`} onClick={() => toggleSel(v.id)} aria-label="Comparer">{selected.includes(v.id) ? "✓" : "+"}</button>
            <Link to={`/vehicules/${encodeURIComponent(v.id)}`}>
              <div className="row">
                <span className="title">{v.name}</span><span className="spacer" />
                {v.score && <span className="badge score" title={`Couverture ${Math.round(v.score.coverage * 100)} %`}>{v.score.value}</span>}
              </div>
              <div className="row small muted" style={{ margin: "4px 0 8px" }}>
                <span>{v.class ?? "?"}</span>
                {v.drivetrain && <span>· {DRIVETRAIN_FR[v.drivetrain] ?? v.drivetrain}</span>}
                {v.seats && <span>· {v.seats} pl.</span>}
                {v.price != null && <span>· {v.price.toLocaleString("fr-FR")} $</span>}
                {v.variant_type !== "standard" && <span className="badge">variante</span>}
              </div>
              <StatBars stats={v.stats} />
            </Link>
          </div>
        ))}
      </div>

      {selected.length > 0 && (
        <div className="compare-tray">
          <button className="btn" style={{ flex: 1 }} disabled={selected.length < 2}
            onClick={() => nav(`/vehicules/comparer?ids=${selected.map(encodeURIComponent).join(",")}`)}>
            Comparer ({selected.length}/4)
          </button>
          <button className="btn ghost" onClick={() => setSelected([])}>✕</button>
        </div>
      )}

      {showFilters && (
        <div className="sheet">
          <div className="row"><h2 style={{ margin: 0 }}>Filtres</h2><span className="spacer" />
            <button className="btn ghost" onClick={() => setSp(new URLSearchParams(sp.get("q") ? { q: sp.get("q")! } : {}))}>Réinitialiser</button>
            <button className="btn" onClick={() => setShowFilters(false)}>OK</button></div>
          <div className="filters" style={{ marginTop: 14 }}>
            {STAT_KEYS.map((k) => (
              <label className="slider" key={k}>
                <span>{STAT_LABELS[k]} min.</span>
                <input type="range" min={0} max={10} step={0.5} value={sp.get(`min_${k}`) ?? 0}
                  onChange={(e) => set(`min_${k}`, e.target.value === "0" ? null : e.target.value)} />
                <span>{sp.get(`min_${k}`) ?? "—"}</span>
              </label>
            ))}
            <label className="slider"><span>Prix max.</span>
              <input type="number" className="input" placeholder="Illimité" value={sp.get("max_price") ?? ""} onChange={(e) => set("max_price", e.target.value)} /><span>$</span></label>
            <label className="slider"><span>Places min.</span>
              <input type="number" className="input" min={1} max={16} value={sp.get("seats_min") ?? ""} onChange={(e) => set("seats_min", e.target.value)} /><span /></label>
            <div><div className="muted small">Transmission</div><div className="row" style={{ marginTop: 6 }}>
              {DRIVES.map((d) => <button key={d} className={`chip ${sp.getAll("drivetrain").includes(d) ? "on" : ""}`} onClick={() => toggleMulti("drivetrain", d)}>{DRIVETRAIN_FR[d]}</button>)}</div></div>
            <div><div className="muted small">Catégories</div><div className="row" style={{ marginTop: 6 }}>
              {classes.map((c) => <button key={c} className={`chip ${sp.getAll("vclass").includes(c) ? "on" : ""}`} onClick={() => toggleMulti("vclass", c)}>{c}</button>)}</div></div>
            <div><div className="muted small">Variantes</div><div className="row" style={{ marginTop: 6 }}>
              {[["named", "Nommées"], ["unique", "Uniques"], ["secret", "Secrètes"], ["standard", "Standard"]].map(([k, l]) =>
                <button key={k} className={`chip ${sp.getAll("variant_type").includes(k) ? "on" : ""}`} onClick={() => toggleMulti("variant_type", k)}>{l}</button>)}</div></div>
          </div>
        </div>
      )}
    </div>
  );
}
