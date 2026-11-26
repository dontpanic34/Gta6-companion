import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Check, ChevronLeft, ChevronRight, Eye, Lightbulb, MapPinned, TriangleAlert } from "lucide-react";
import { api, EntityFull, entityLink, RELIABILITY_FR } from "../api";

const PRECISION_FR: Record<string, string> = { exact: "Emplacement exact", nearby: "Secteur", zone: "Zone approximative" };
const STAT_FR: Record<string, string> = { speed: "Vitesse", acceleration: "Accélération", handling_road: "Maniabilité", handling_offroad: "Tout-terrain", damage: "Dégâts", accuracy: "Précision", range: "Portée" };

export default function EntityPage() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [e, setE] = useState<EntityFull | null>(null);
  const [err, setErr] = useState("");
  const [confirm, setConfirm] = useState<"name" | "solution" | null>(null);

  useEffect(() => { setE(null); api.entity(id).then(setE).catch((x) => setErr(x.message)); }, [id]);
  if (err) return <div className="page"><p className="notice">{err}</p></div>;
  if (!e) return <div className="page muted">Chargement…</div>;

  const claim = (f: string) => { const c = e.claims.find((x) => x.field === f); return c ? JSON.parse(c.value_json) : null; };
  const start = e.content.filter((c) => c.level === 1);
  const hints = e.content.filter((c) => c.level === 2);
  const solution = e.content.filter((c) => c.level === 3);
  const done = e.status === "done";
  const image = e.linked?.image ?? e.media[0];
  const sourceUrl = claim("source_page") ?? e.claims.find((c) => c.source_url)?.source_url;
  const toggleDone = () => {
    const isMission = e.kind === "mission" || e.kind === "side_mission";
    // une mission faite fait aussi avancer la progression anti-spoiler
    const p = isMission ? api.setMission(e.id, !done).then(() => api.setStatus(e.id, done ? "to_discover" : "done")) : api.setStatus(e.id, done ? "to_discover" : "done");
    p.then(() => setE({ ...e, status: done ? "to_discover" : "done" }));
  };

  return (
    <div className="page entity">
      <button className="iconback" onClick={() => nav(-1)} aria-label="Retour"><ChevronLeft size={24} /></button>
      {image && <img className="hero" src={image} alt="" referrerPolicy="no-referrer" onError={(e) => (e.currentTarget.style.display = "none")} />}
      <div className="row" style={{ flexWrap: "nowrap", alignItems: "flex-start", marginTop: 12 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1 style={{ margin: "0 0 6px" }}>{e.name}</h1>
          <div className="row small">
            {e.category && <span className="badge">{e.category}</span>}
            {e.region && <span className="badge">{e.region}</span>}
            <span className="badge">{RELIABILITY_FR[e.reliability] ?? e.reliability}</span>
          </div>
        </div>
        <button className={`donebtn big ${done ? "on" : ""}`} onClick={toggleDone} aria-label="Fait"><Check size={24} /><span>{done ? "Fait" : "À faire"}</span></button>
      </div>
      {!!e.closes_count && !done && (
        <div className="missable">
          <TriangleAlert size={22} />
          <div><b>Avant de lancer cette mission</b><br />
            {e.closes_count > 1 ? `${e.closes_count} choses peuvent` : "Quelque chose peut"} devenir définitivement inaccessible. Explorez et terminez ce qui vous tient à cœur avant de la commencer.</div>
        </div>
      )}
      {e.missable_warning && <p className="notice"><TriangleAlert size={15} style={{ verticalAlign: "-3px" }} /> Peut devenir définitivement inaccessible.</p>}

      <div className="card" style={{ marginTop: 14 }}>
        {start.map((c, i) => <p key={i} style={{ margin: "0 0 8px" }}>{c.body}</p>)}
        {claim("description") && <p style={{ margin: "0 0 8px" }}>{claim("description")}</p>}
        {!start.length && !claim("description") && <p className="muted" style={{ margin: "0 0 8px" }}>Pas encore de détail vérifié sur l'accès.</p>}
        <div className="row small muted">
          {claim("subarea") && <span>Secteur : {claim("subarea")}</span>}
          {e.location && <span>· {PRECISION_FR[e.location.precision] ?? e.location.precision}</span>}
        </div>
        {e.location && (
          <button className="btn ghost wide" style={{ marginTop: 10 }}
            onClick={() => nav(`/carte?x=${e.location!.x}&y=${e.location!.y}&z=5&focus=${encodeURIComponent(e.id)}`)}><MapPinned size={18} /> Voir sur la carte</button>
        )}
      </div>

      {e.linked && (
        <Link to={entityLink(e.linked.id)} className="card linkcard">
          <div style={{ flex: 1 }}>
            <div className="title">Fiche complète</div>
            <div className="ministats">{Object.keys(STAT_FR).filter((k) => e.linked!.stats[k] != null).slice(0, 4)
              .map((k) => <span key={k}><b>{e.linked!.stats[k]}</b> {STAT_FR[k]}</span>)}</div>
          </div>
          <ChevronRight size={20} className="muted" />
        </Link>
      )}

      {(hints.length > 0 || e.hints_remaining > 0) && (
        <div className="card" style={{ marginTop: 12 }}>
          {hints.map((c, i) => <p key={i} style={{ margin: "0 0 8px" }}><Lightbulb size={15} style={{ verticalAlign: "-3px", color: "var(--warn)" }} /> {c.body}</p>)}
          {e.hints_remaining > 0 && <button className="btn ghost wide" onClick={() => api.hint(e.id).then((x) => setE({ ...e, ...x }))}>
            <Lightbulb size={18} /> Un indice ({e.hints_remaining})</button>}
        </div>
      )}

      {solution.length > 0 && <div className="card" style={{ marginTop: 12 }}>{solution.map((c, i) => <p key={i}>{c.body}</p>)}</div>}

      {(e.name_hidden || (e.has_solution && !solution.length)) && (
        <div className="row" style={{ marginTop: 12 }}>
          {e.name_hidden && <button className="btn ghost" onClick={() => setConfirm("name")}><Eye size={16} /> Vrai titre</button>}
          {e.has_solution && !solution.length && <button className="btn ghost" onClick={() => setConfirm("solution")}><Eye size={16} /> Solution</button>}
        </div>
      )}
      {sourceUrl && <p className="small muted" style={{ marginTop: 16 }}>Source : <a href={sourceUrl} target="_blank" rel="noreferrer" style={{ textDecoration: "underline" }}>{new URL(sourceUrl).hostname}</a></p>}

      {confirm && (<>
        <div className="scrim" onClick={() => setConfirm(null)} />
        <div className="sheet">
          <div className="grabber" />
          <h2 style={{ marginTop: 0 }}>{confirm === "name" ? "Révéler le titre ?" : "Afficher la solution ?"}</h2>
          <p className="muted">{confirm === "name" ? "Le titre peut révéler la nature ou l'issue de ce contenu." : "Le déroulement et la fin de ce contenu seront affichés."} Rien d'autre n'est débloqué.</p>
          <div className="row" style={{ flexWrap: "nowrap" }}>
            <button className="btn grow" onClick={() => (confirm === "name" ? api.revealName(e.id) : api.solution(e.id)).then((x) => setE({ ...e, ...x })).finally(() => setConfirm(null))}>Révéler</button>
            <button className="btn ghost grow" onClick={() => setConfirm(null)}>Annuler</button>
          </div>
        </div>
      </>)}
    </div>
  );
}
