import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Check, ChevronRight, Lock, Search, X } from "lucide-react";
import { api, entityLink, Place, ProgressOptions } from "../api";
import { ALL_FAMILIES, categoryStyle, familyOf } from "../map/categories";
import { FamIcon } from "./MapPage";

type Tab = "missions" | "secrets";

export default function Encyclopedia() {
  const nav = useNavigate();
  const [tab, setTab] = useState<Tab>(() => { try { return (localStorage.getItem("enc_tab") as Tab) ?? "missions"; } catch { return "missions"; } });
  const [o, setO] = useState<ProgressOptions | null>(null);
  const [places, setPlaces] = useState<Place[]>([]);
  const [q, setQ] = useState("");
  const [fam, setFam] = useState<string | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => { try { localStorage.setItem("enc_tab", tab); } catch { /* ignore */ } }, [tab]);
  useEffect(() => {
    api.progressOptions().then(setO).catch((e) => setErr(e.message));
    api.places(new URLSearchParams()).then(setPlaces).catch(() => {});
  }, []);

  const needle = q.trim().toLowerCase();
  const secrets = useMemo(() => places.filter((p) => p.id.startsWith("secret:"))
    .filter((p) => !fam || familyOf(p.category, true).id === fam)
    .filter((p) => !needle || `${p.name} ${p.category} ${p.region}`.toLowerCase().includes(needle)), [places, fam, needle]);
  const famCount = useMemo(() => {
    const n: Record<string, number> = {};
    places.filter((p) => p.id.startsWith("secret:")).forEach((p) => { const k = familyOf(p.category, true).id; n[k] = (n[k] ?? 0) + 1; });
    return n;
  }, [places]);
  const groups = useMemo(() => {
    const g = new Map<string, ProgressOptions["missions"]>();
    (o?.missions ?? []).filter((m) => !needle || m.name.toLowerCase().includes(needle)).forEach((m) => {
      const k = m.kind === "side_mission" ? "Missions secondaires" : m.chapter === 0 ? "Prologue" : `Chapitre ${m.chapter}`;
      g.set(k, [...(g.get(k) ?? []), m]);
    });
    return [...g.entries()];
  }, [o, needle]);
  const hiddenChapters = o ? o.chapters.filter((c) => c.num > o.chapter).length : 0;

  return (
    <div className="catalog">
      <div className="cat-head"><h1>Encyclopédie</h1></div>
      <div className="seg">
        <button className={tab === "missions" ? "on" : ""} onClick={() => setTab("missions")}>Missions</button>
        <button className={tab === "secrets" ? "on" : ""} onClick={() => setTab("secrets")}>Secrets</button>
        <button onClick={() => nav("/vehicules")}>Véhicules</button>
        <button onClick={() => nav("/armes")}>Armes</button>
      </div>

      <div className="cat-list">
        {err && <p className="notice">{err}</p>}
        {tab === "missions" && (<>
          {groups.map(([k, list]) => (
            <div key={k}>
              <h4 className="sheet-h">{k} · {list.filter((m) => m.done).length}/{list.length} faites</h4>
              {list.map((m) => (
                <div key={m.id} className="vrow" style={{ alignItems: "center" }}>
                  <Link to={entityLink(m.id)} className="vrow-main" style={{ alignItems: "center" }}>
                    <span className="famicon" style={{ background: m.done ? "var(--teal)" : "var(--surface-2)" }}>{m.done ? <Check size={16} color="#140a24" /> : <ChevronRight size={16} />}</span>
                    <span className="title grow" style={{ textAlign: "left" }}>{m.name}{!!m.closes_count && <span className="badge warn" style={{ marginLeft: 8 }}>⚠ manquable avant</span>}</span>
                  </Link>
                  <button className={`selbtn ${m.done ? "on" : ""}`} onClick={() => api.setMission(m.id, !m.done).then(setO)} aria-label="Faite"><Check size={18} opacity={m.done ? 1 : 0.25} /></button>
                </div>
              ))}
            </div>
          ))}
          {hiddenChapters > 0 && <p className="small muted" style={{ textAlign: "center", padding: 16 }}><Lock size={13} style={{ verticalAlign: "-2px" }} /> {hiddenChapters} chapitre(s) suivant(s) masqué(s). Avancez votre progression dans Réglages.</p>}
          {o && groups.length === 0 && <div className="empty">Aucune mission pour l'instant.</div>}
        </>)}

        {tab === "secrets" && secrets.map((p) => {
          const st = categoryStyle(p.category, true);
          return (
            <Link key={p.id} to={entityLink(p.id)} className="vrow" style={{ alignItems: "center" }}>
              <span className="famicon big" style={{ background: st.color }}><FamIcon f={st} size={20} color="#140a24" /></span>
              <div className="vinfo">
                <span className="title ellipsis">{p.status === "done" ? "✓ " : ""}{p.name}</span>
                <span className="small muted ellipsis">{p.category} · {p.region ?? "Leonida"}</span>
              </div>
              <ChevronRight size={18} className="muted" />
            </Link>
          );
        })}
      </div>

      <div className="cat-bottom">
        {tab === "secrets" && (
          <div className="chiprow">
            {ALL_FAMILIES.filter((f) => famCount[f.id]).map((f) => (
              <button key={f.id} className={`chip ${fam === f.id ? "on" : ""}`} onClick={() => setFam(fam === f.id ? null : f.id)}>
                <FamIcon f={f} size={14} /> {f.label} <span className="muted small">{famCount[f.id]}</span></button>
            ))}
          </div>
        )}
        <div className="searchbar">
          <Search size={18} className="muted" />
          <input placeholder={tab === "missions" ? "Chercher une mission" : "Chercher un secret"} value={q} onChange={(e) => setQ(e.target.value)} />
          {q && <button className="iconbtn" onClick={() => setQ("")} aria-label="Effacer"><X size={18} /></button>}
        </div>
      </div>
    </div>
  );
}
