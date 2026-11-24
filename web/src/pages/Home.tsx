import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Progress } from "../api";

export default function Home() {
  const [p, setP] = useState<Progress | null>(null);
  const [garage, setGarage] = useState<{ id: string; name: string; status: string }[]>([]);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.progress().then(setP).catch((e) => setErr(e.message));
    api.garage().then(setGarage).catch(() => {});
  }, []);

  return (
    <div className="page">
      <div className="row"><h1>Leonida <em>Companion</em></h1><span className="spacer" />
        <Link to="/reglages" className="chip">⚙ Réglages</Link></div>
      {err && <p className="notice">{err}</p>}
      <div className="card">
        <div className="muted small">Ma progression</div>
        <div style={{ fontSize: 22, fontWeight: 700, margin: "4px 0" }}>{p ? (p.chapter ? `Chapitre ${p.chapter}` : "Début de partie") : "…"}</div>
        <div className="small muted">{p ? `${p.completed_missions.length} missions · ${p.discovered_regions.length} régions · ${p.met_characters.length} personnages` : ""}</div>
        <p className="small" style={{ marginBottom: 0 }}>🛡 Protection anti-spoiler active : seul ce qui correspond à votre progression est affiché.</p>
      </div>

      <h2>Mon garage</h2>
      {garage.length ? (
        <div className="row">{garage.map((g) => <Link key={g.id} className="chip" to={`/vehicules/${encodeURIComponent(g.id)}`}>{g.name}</Link>)}</div>
      ) : <p className="muted small">Ajoutez des véhicules depuis leur fiche (possédé, recherché, favori, perdu).</p>}

      <h2>Accès rapide</h2>
      <div className="grid">
        <Link className="card" to="/vehicules?use_profile=true">★ Voitures adaptées à mon style</Link>
        <Link className="card" to="/vehicules?min_handling_offroad=6">⛰ Meilleures en tout-terrain</Link>
        <Link className="card" to="/carte">🗺 Activités autour de moi</Link>
        <Link className="card" to="/assistant">💬 Demander à l'assistant</Link>
      </div>
    </div>
  );
}
