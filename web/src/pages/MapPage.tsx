import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, entityLink, Place } from "../api";

const PALETTE = ["#ff4f8b", "#38d6c4", "#ffa24c", "#a78bfa", "#4ade80", "#60a5fa", "#f472b6", "#facc15"];

/** Vue provisoire : nuage de points en coordonnées du jeu, en attendant le fond
 *  de carte GTA VI Landmarks (CC BY 4.0). */
function PointCloud({ places, onPick, me }: { places: Place[]; onPick: (p: Place) => void; me: [number, number] | null }) {
  const pts = places.filter((p) => p.x != null && p.y != null);
  if (!pts.length) return <div className="card empty">Aucun point positionné pour ce filtre.</div>;
  const xs = pts.map((p) => p.x!), ys = pts.map((p) => p.y!);
  const [minX, maxX, minY, maxY] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const pad = 200, w = Math.max(maxX - minX, 1) + pad * 2, h = Math.max(maxY - minY, 1) + pad * 2;
  const cats = [...new Set(pts.map((p) => p.category))];
  return (
    <div className="card" style={{ padding: 6 }}>
      <svg viewBox={`${minX - pad} ${-(maxY + pad)} ${w} ${h}`} style={{ width: "100%", maxHeight: "60dvh", display: "block" }}>
        {pts.map((p) => (
          <circle key={p.id} cx={p.x!} cy={-p.y!} r={Math.max(w, h) / 220}
            fill={PALETTE[cats.indexOf(p.category) % PALETTE.length]} opacity={p.status === "done" ? 0.3 : 0.9}
            onClick={() => onPick(p)} style={{ cursor: "pointer" }}><title>{p.name}</title></circle>
        ))}
        {me && <circle cx={me[0]} cy={-me[1]} r={Math.max(w, h) / 90} fill="none" stroke="#fff" strokeWidth={Math.max(w, h) / 400} />}
      </svg>
      <p className="small muted" style={{ margin: 6 }}>Aperçu en coordonnées du jeu (sans fond de carte). Touchez un point pour l'ouvrir.</p>
    </div>
  );
}

export default function MapPage() {
  const [sp, setSp] = useSearchParams();
  const [facets, setFacets] = useState<Awaited<ReturnType<typeof api.facets>> | null>(null);
  const [places, setPlaces] = useState<Place[]>([]);
  const [picked, setPicked] = useState<Place | null>(null);
  const [err, setErr] = useState("");
  const region = sp.get("region"), category = sp.get("category"), hideDone = sp.get("hide_done") === "true";

  useEffect(() => { api.facets().then(setFacets).catch((e) => setErr(e.message)); }, []);
  useEffect(() => {
    const p = new URLSearchParams(); region && p.set("region", region); category && p.set("category", category);
    hideDone && p.set("hide_done", "true");
    api.places(p).then(setPlaces).catch((e) => setErr(e.message));
  }, [region, category, hideDone]);

  const set = (k: string, v: string | null) => { const n = new URLSearchParams(sp); v ? n.set(k, v) : n.delete(k); setSp(n, { replace: true }); };
  const byCat = useMemo(() => {
    const m = new Map<string, Place[]>();
    places.forEach((p) => m.set(p.category ?? "Autre", [...(m.get(p.category ?? "Autre") ?? []), p]));
    return [...m.entries()].sort((a, b) => b[1].length - a[1].length);
  }, [places]);

  return (
    <div className="page">
      <h1>Carte</h1>
      {err && <p className="notice">{err}</p>}
      <div className="row" style={{ overflowX: "auto", flexWrap: "nowrap", marginBottom: 8 }}>
        <button className={`chip ${!region ? "on" : ""}`} onClick={() => set("region", null)}>Toute Leonida</button>
        {facets?.regions.map((r) => <button key={r.name} className={`chip ${region === r.name ? "on" : ""}`} onClick={() => set("region", r.name)}>{r.name} · {r.n}</button>)}
      </div>
      <div className="row" style={{ overflowX: "auto", flexWrap: "nowrap", marginBottom: 12 }}>
        <button className={`chip ${hideDone ? "on" : ""}`} onClick={() => set("hide_done", hideDone ? null : "true")}>Masquer découverts</button>
        <button className={`chip ${!category ? "on" : ""}`} onClick={() => set("category", null)}>Toutes catégories</button>
        {facets?.categories.map((c) => <button key={c.name} className={`chip ${category === c.name ? "on" : ""}`} onClick={() => set("category", c.name)}>{c.secret ? "✦ " : ""}{c.name} · {c.n}</button>)}
      </div>

      <PointCloud places={places} onPick={setPicked} me={null} />
      {picked && (
        <div className="card row" style={{ marginTop: 10 }}>
          <div><b>{picked.name}</b><div className="small muted">{picked.category} · {picked.region}</div></div>
          <span className="spacer" /><Link className="btn" to={entityLink(picked.id)}>Ouvrir</Link>
        </div>
      )}

      <h2>{places.length} activités{region ? ` · ${region}` : ""}</h2>
      {byCat.map(([cat, list]) => (
        <details key={cat} className="card" style={{ marginBottom: 8 }}>
          <summary><b>{cat}</b> <span className="muted small">({list.length})</span></summary>
          <div style={{ display: "grid", gap: 6, marginTop: 8 }}>
            {list.map((p) => (
              <Link key={p.id} to={entityLink(p.id)} className="row small">
                <span>{p.status === "done" ? "✓ " : ""}{p.name}</span><span className="spacer" /><span className="muted">{p.region}</span>
              </Link>
            ))}
          </div>
        </details>
      ))}
    </div>
  );
}
