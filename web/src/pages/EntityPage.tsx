import { ChevronLeft, Lightbulb, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, EntityFull, RELIABILITY_FR } from "../api";

const STATUS = [["to_discover", "À découvrir"], ["discovered", "Découvert"], ["done", "Terminé"], ["favorite", "Favori"]];
const PRECISION_FR: Record<string, string> = { exact: "Emplacement exact", nearby: "À proximité", zone: "Zone à fouiller" };

export default function EntityPage() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [e, setE] = useState<EntityFull | null>(null);
  const [err, setErr] = useState("");
  const [confirm, setConfirm] = useState<"name" | "solution" | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => { setE(null); api.entity(id).then(setE).catch((x) => setErr(x.message)); }, [id]);
  if (err) return <div className="page"><p className="notice">{err}</p></div>;
  if (!e) return <div className="page muted">Chargement…</div>;

  const claim = (f: string) => { const c = e.claims.find((x) => x.field === f); return c ? JSON.parse(c.value_json) : null; };
  const start = e.content.filter((c) => c.level === 1);
  const hints = e.content.filter((c) => c.level === 2);
  const solution = e.content.filter((c) => c.level === 3);
  const sourceUrl = claim("source_page") ?? e.claims.find((c) => c.source_url)?.source_url;

  return (
    <div className="page">
      <button className="chip" onClick={() => nav(-1)}><ChevronLeft size={16} /> Retour</button>
      <h1 style={{ marginTop: 14 }}>{e.name}</h1>
      <div className="row small">
        {e.category && <span className="badge">{e.category}</span>}
        {e.region && <span className="badge">{e.region}</span>}
        <span className="badge">{RELIABILITY_FR[e.reliability] ?? e.reliability}</span>
        {claim("precision") && <span className="badge">{PRECISION_FR[claim("precision")] ?? claim("precision")}</span>}
        {claim("creators_count") && <span className="badge">vu par {claim("creators_count")} joueurs</span>}
      </div>
      {e.missable_warning && <p className="notice"><TriangleAlert size={15} style={{ verticalAlign: "-3px" }} /> Ce contenu peut devenir définitivement inaccessible.</p>}

      <div className="row" style={{ margin: "14px 0" }}>
        {STATUS.map(([k, l]) => <button key={k} className={`chip ${status === k ? "on" : ""}`}
          onClick={() => api.setStatus(e.id, k).then(() => setStatus(k))}>{l}</button>)}
      </div>

      <h2>Pour commencer</h2>
      <div className="card">
        {start.length ? start.map((c, i) => <p key={i} style={{ margin: "4px 0" }}>{c.body}</p>)
          : <p className="muted">Aucune information de départ vérifiée.</p>}
        {claim("subarea") && <p className="small muted">Secteur : {claim("subarea")}</p>}
        {claim("description") && <p className="small muted">{claim("description")}</p>}
      </div>

      {(hints.length > 0 || e.hints_remaining > 0) && (<>
        <h2>Indices</h2>
        <div className="card">
          {hints.map((c, i) => <p key={i} style={{ margin: "4px 0" }}><Lightbulb size={15} style={{ verticalAlign: "-3px", color: "var(--warn)" }} /> {c.body}</p>)}
          {e.hints_remaining > 0 && <button className="btn ghost" onClick={() => api.hint(e.id).then(setE)}>
            Afficher un indice ({e.hints_remaining} restant{e.hints_remaining > 1 ? "s" : ""})</button>}
        </div>
      </>)}

      {solution.length > 0 && (<><h2>Solution</h2><div className="card">{solution.map((c, i) => <p key={i}>{c.body}</p>)}</div></>)}

      <h2>Options de révélation</h2>
      <div className="row">
        {e.name_hidden && <button className="btn ghost" onClick={() => setConfirm("name")}>Révéler le vrai titre</button>}
        {solution.length === 0 && <button className="btn ghost" onClick={() => setConfirm("solution")}>Solution complète</button>}
      </div>
      <p className="small muted">Chaque révélation ne concerne que ce contenu. La protection reste active partout ailleurs.</p>
      {sourceUrl && <p className="small muted">Source : <a href={sourceUrl} target="_blank" rel="noreferrer" style={{ textDecoration: "underline" }}>{new URL(sourceUrl).hostname}</a></p>}

      {confirm && (
        <div className="sheet">
          <h2 style={{ marginTop: 0 }}>{confirm === "name" ? "Révéler le titre ?" : "Afficher la solution complète ?"}</h2>
          <p className="muted">{confirm === "name" ? "Le titre peut révéler la nature ou l'issue de ce contenu." : "Le déroulement et la conclusion de ce contenu seront affichés, s'ils existent dans la base."}</p>
          <div className="row">
            <button className="btn" onClick={() => (confirm === "name" ? api.revealName(e.id) : api.solution(e.id)).then(setE).finally(() => setConfirm(null))}>Oui, révéler</button>
            <button className="btn ghost" onClick={() => setConfirm(null)}>Annuler</button>
          </div>
        </div>
      )}
    </div>
  );
}
