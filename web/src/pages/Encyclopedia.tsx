import { CarFront, Crosshair, ScrollText, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, entityLink } from "../api";

export default function Encyclopedia() {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<Awaited<ReturnType<typeof api.search>>>([]);
  useEffect(() => {
    if (q.trim().length < 2) { setRes([]); return; }
    const t = setTimeout(() => api.search(q).then(setRes).catch(() => setRes([])), 200);
    return () => clearTimeout(t);
  }, [q]);

  const link = entityLink;
  const [facets, setFacets] = useState<Awaited<ReturnType<typeof api.facets>> | null>(null);
  useEffect(() => { api.facets().then(setFacets).catch(() => {}); }, []);
  return (
    <div className="page">
      <h1>Encyclopédie</h1>
      <input className="input" placeholder="Rechercher (véhicules, armes, lieux…)" value={q} onChange={(e) => setQ(e.target.value)} />
      <p className="small muted">La recherche ne porte que sur les contenus autorisés par votre progression.</p>
      <div style={{ display: "grid", gap: 8 }}>
        {res.map((r, i) => (
          <Link key={i} to={link(r.entity_id)} className="card">
            <b>{r.display_name}</b>
            <div className="small muted">{r.snip}</div>
          </Link>
        ))}
      </div>
      <h2>Rubriques</h2>
      <div className="grid">
        <Link to="/vehicules" className="card tile"><CarFront size={20} /> Véhicules et variantes</Link>
        <Link to="/armes" className="card tile"><Crosshair size={20} /> Armes et variantes</Link>
        <div className="card tile muted"><ScrollText size={20} /> Missions et quêtes — phase 5</div>
        {facets?.categories.filter((c) => c.secret).map((c) => (
          <Link key={c.name} className="card tile" to={`/carte?category=${encodeURIComponent(c.name)}`}><Sparkles size={20} /> {c.name} <span className="muted small">({c.n})</span></Link>
        ))}
      </div>
    </div>
  );
}
