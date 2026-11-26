import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CarFront, ChevronRight, LocateFixed, MessageCircle, Mountain, ScrollText, Star } from "lucide-react";
import ViceHero from "../components/ViceHero";
import { api, entityLink, News, Place, ProgressOptions } from "../api";
import { categoryStyle } from "../map/categories";
import { distance } from "../map/leonida";
import { FamIcon } from "./MapPage";

export default function Home() {
  const [o, setO] = useState<ProgressOptions | null>(null);
  const [garage, setGarage] = useState<{ id: string; name: string; status: string }[]>([]);
  const [places, setPlaces] = useState<Place[]>([]);
  const [newsDays, setNewsDays] = useState(1);
  const [news, setNews] = useState<News | null>(null);
  useEffect(() => { api.news(newsDays).then(setNews).catch(() => setNews(null)); }, [newsDays]);
  const me = useMemo<[number, number] | null>(() => { try { return JSON.parse(localStorage.getItem("map_state_v2") ?? "{}").me ?? null; } catch { return null; } }, []);

  useEffect(() => {
    api.progressOptions().then(setO).catch(() => {});
    api.garage().then(setGarage).catch(() => {});
    api.places(new URLSearchParams()).then(setPlaces).catch(() => {});
  }, []);

  const nearby = useMemo(() => !me ? [] : places.filter((p) => p.x != null && p.status !== "done")
    .map((p) => ({ p, d: distance(me, [p.x!, p.y!]) })).sort((a, b) => a.d - b.d).slice(0, 5), [places, me]);
  const secretsLeft = places.filter((p) => p.id.startsWith("secret:") && p.status !== "done").length;
  const story = o?.missions.filter((m) => m.kind === "mission") ?? [];
  const done = story.filter((m) => m.done).length;
  const chapTitle = o?.chapters.find((c) => c.num === o.chapter)?.title;

  return (
    <div className="page home">
      <ViceHero subtitle="LEONIDA · COMPAGNON" />

      <Link to="/reglages" className="card prog">
        <div style={{ flex: 1 }}>
          <div className="small muted">Ma progression</div>
          <div className="step-num" style={{ fontSize: 30 }}>{o ? (o.chapter === 0 ? "Prologue" : `Chapitre ${o.chapter}`) : "…"}</div>
          {chapTitle && o?.chapter ? <div className="small">{chapTitle}</div> : null}
          <div className="bar" style={{ marginTop: 8 }}><i style={{ width: `${story.length ? (done / story.length) * 100 : 0}%` }} /></div>
          <div className="small muted" style={{ marginTop: 4 }}>{done}/{story.length} missions visibles faites · anti-spoiler actif</div>
        </div>
        <ChevronRight size={20} className="muted" />
      </Link>

      <div className="row" style={{ marginTop: 22 }}><h2 style={{ margin: 0 }}>Nouveautés</h2><span className="spacer" />
        {[[1, "24 h"], [7, "7 j"], [30, "30 j"]].map(([d, l]) => (
          <button key={d} className={`chip ${newsDays === d ? "on" : ""}`} onClick={() => setNewsDays(d as number)}>{l}</button>))}
      </div>
      <div className="card" style={{ padding: 6, marginTop: 10 }}>
        {news?.items.length ? news.items.slice(0, 8).map((n) => { const st = categoryStyle(n.category, n.id.startsWith("secret:")); return (
          <Link key={n.id} to={entityLink(n.id)} className="listrow">
            <span className="famicon" style={{ background: st.color }}><FamIcon f={st} size={16} color="#140a24" /></span>
            <span className="grow ellipsis" style={{ textAlign: "left" }}>{n.name}<span className="small muted"> · {n.category ?? (n.kind.startsWith("vehicle") ? "Véhicule" : n.kind.startsWith("weapon") ? "Arme" : "")}</span></span>
            <span className="badge">nouveau</span>
          </Link>); })
          : <p className="small muted" style={{ margin: 10 }}>{news?.baseline ? "Rien de nouveau sur cette période." : "Les nouveautés apparaîtront après les prochaines mises à jour de nuit."}</p>}
        {!!news?.corrections && <p className="small muted" style={{ margin: "6px 10px" }}>+ {news.corrections} fiche(s) corrigée(s) ou complétée(s)</p>}
      </div>

      <h2>Autour de moi</h2>
      {nearby.length ? (
        <div className="card" style={{ padding: 6 }}>
          {nearby.map(({ p, d }) => { const st = categoryStyle(p.category, p.id.startsWith("secret:")); return (
            <Link key={p.id} to={`/carte?x=${p.x}&y=${p.y}&z=5`} className="listrow">
              <span className="famicon" style={{ background: st.color }}><FamIcon f={st} size={16} color="#140a24" /></span>
              <span className="grow ellipsis" style={{ textAlign: "left" }}>{p.name}<span className="small muted"> · {p.category}</span></span>
              <span className="small muted">{d < 1000 ? `${Math.round(d)} m` : `${(d / 1000).toFixed(1)} km`}</span>
            </Link>); })}
        </div>
      ) : (
        <Link to="/carte" className="card tile"><LocateFixed size={20} /> Indiquez où vous êtes sur la carte (appui long)</Link>
      )}

      <div className="grid2">
        <Link to="/encyclopedie" className="card statcard"><b>{secretsLeft}</b><span>secrets à découvrir</span></Link>
        <Link to="/vehicules" className="card statcard"><b>{garage.length}</b><span>véhicules au garage</span></Link>
      </div>

      {garage.length > 0 && (<>
        <h2>Mon garage</h2>
        <div className="row">{garage.map((g) => <Link key={g.id} className="chip" to={entityLink(g.id)}>{g.name}</Link>)}</div>
      </>)}

      <h2>Accès rapide</h2>
      <div className="grid">
        <Link className="card tile" to="/vehicules?sort=profile"><Star size={20} /> Voitures adaptées à mon style</Link>
        <Link className="card tile" to="/vehicules?min_handling_offroad=6"><Mountain size={20} /> Meilleures en tout-terrain</Link>
        <Link className="card tile" to="/encyclopedie"><ScrollText size={20} /> Missions et secrets</Link>
        <Link className="card tile" to="/armes"><CarFront size={20} /> Armes et variantes</Link>
        <Link className="card tile" to="/assistant"><MessageCircle size={20} /> Demander à l'assistant</Link>
      </div>
      <div style={{ height: 16 }} />
    </div>
  );
}
