import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, ChevronLeft, Gamepad2, Minus, Plus, RefreshCw, ShieldCheck } from "lucide-react";
import { api, getBaseUrl, getToken, ProgressOptions, setBaseUrl, setToken, XboxSummary } from "../api";

export default function Settings() {
  const nav = useNavigate();
  const [o, setO] = useState<ProgressOptions | null>(null);
  const [token, setTok] = useState(getToken());
  const [base, setBase] = useState(getBaseUrl());
  const [msg, setMsg] = useState("");
  const [xb, setXb] = useState<XboxSummary | null>(null);
  const [xbMsg, setXbMsg] = useState("");
  const [theme, setTheme] = useState(() => { try { return localStorage.getItem("theme") ?? "dark"; } catch { return "dark"; } });

  const load = () => api.progressOptions().then(setO).catch((e) => setMsg(e.message));
  useEffect(() => { load(); api.xbox().then(setXb).catch(() => {}); }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("theme", theme); } catch { /* ignore */ }
  }, [theme]);

  const setChapter = async (n: number) => {
    if (!o) return;
    const cur = await api.progress();
    await api.setProgress({ ...cur, chapter: Math.max(0, Math.min(o.max_chapter, n)) });
    load();
  };
  const syncXbox = () => {
    setXbMsg("Synchronisation…");
    api.xboxSync().then((r) => {
      if (r.ok === false) { setXbMsg(r.error ?? "Échec"); return; }
      setXb(r); setXbMsg(`${r.new_unlocked ?? 0} nouveau(x) succès`); load();
    }).catch((e) => setXbMsg(e.message));
  };

  const chapterTitle = o?.chapters.find((c) => c.num === o.chapter)?.title;
  const byChapter = new Map<string, ProgressOptions["missions"]>();
  o?.missions.forEach((m) => {
    const k = m.kind === "side_mission" ? "Missions secondaires" : m.chapter === 0 ? "Prologue" : `Chapitre ${m.chapter}`;
    byChapter.set(k, [...(byChapter.get(k) ?? []), m]);
  });

  return (
    <div className="page">
      <button className="iconback" onClick={() => nav(-1)} aria-label="Retour"><ChevronLeft size={24} /></button>
      <h1 style={{ paddingLeft: 52 }}>Réglages</h1>

      <h2>Ma progression</h2>
      <div className="card">
        <div className="stepper">
          <button onClick={() => o && setChapter(o.chapter - 1)} aria-label="Chapitre précédent"><Minus size={22} /></button>
          <div>
            <div className="step-num">{o ? (o.chapter === 0 ? "Prologue" : `Chapitre ${o.chapter}`) : "…"}</div>
            <div className="small muted">{o && o.chapter > 0 ? (chapterTitle ?? "") : "Début de partie"}</div>
          </div>
          <button onClick={() => o && setChapter(o.chapter + 1)} aria-label="Chapitre suivant"><Plus size={22} /></button>
        </div>
        <p className="small muted" style={{ margin: "10px 0 0" }}><ShieldCheck size={14} style={{ verticalAlign: "-2px" }} /> Le titre d'un chapitre n'apparaît qu'une fois atteint. Tout ce qui est plus loin reste masqué partout.</p>
      </div>

      {[...byChapter.entries()].map(([k, list]) => (
        <div key={k}>
          <h4 className="sheet-h">{k} · {list.filter((m) => m.done).length}/{list.length} faites</h4>
          <div className="checklist">
            {list.map((m) => (
              <button key={m.id} className={`checkrow ${m.done ? "on" : ""}`} onClick={() => api.setMission(m.id, !m.done).then(setO)}>
                <span className="box">{m.done && <Check size={16} />}</span><span className="grow" style={{ textAlign: "left" }}>{m.name}{!!m.closes_count && <span className="badge warn" style={{ marginLeft: 8 }}>⚠</span>}</span>
              </button>
            ))}
          </div>
        </div>
      ))}

      {!!o?.characters.length && (<>
        <h4 className="sheet-h">Personnages rencontrés</h4>
        <div className="row">
          {o.characters.map((c) => <button key={c.id} className={`chip ${c.met ? "on" : ""}`} onClick={() => api.setCharacter(c.id, !c.met).then(setO)}>{c.met && <Check size={14} />}{c.name}</button>)}
        </div>
      </>)}

      <h2>Xbox</h2>
      <div className="card filters">
        <div className="row"><Gamepad2 size={20} color="var(--accent)" />
          <span>{xb ? `${xb.unlocked_count} / ${xb.total} succès débloqués` : "Non synchronisé"}</span><span className="spacer" />
          <button className="btn ghost small" onClick={syncXbox}><RefreshCw size={15} /> Synchroniser</button></div>
        {xbMsg && <p className="small muted" style={{ margin: 0 }}>{xbMsg}</p>}
        <p className="small muted" style={{ margin: 0 }}>Les succès non débloqués ne sont jamais nommés. Nécessite la clé OpenXBL sur le PC.</p>
      </div>

      <h2>Connexion au PC</h2>
      <div className="card filters">
        <input className="input" placeholder="Adresse du PC (ex. http://100.64.0.5:8765)" value={base} onChange={(e) => setBase(e.target.value)} />
        <input className="input" placeholder="Jeton d'accès" value={token} onChange={(e) => setTok(e.target.value)} />
        <button className="btn" onClick={() => { setBaseUrl(base); setToken(token); setMsg("Connexion enregistrée"); load(); }}>Enregistrer</button>
        <p className="small muted" style={{ margin: 0 }}>Sans PC, l'appli fonctionne hors ligne avec les données embarquées (sans assistant).</p>
      </div>

      <h2>Apparence</h2>
      <div className="row">
        <button className={`chip ${theme === "dark" ? "on" : ""}`} onClick={() => setTheme("dark")}>Nuit</button>
        <button className={`chip ${theme === "light" ? "on" : ""}`} onClick={() => setTheme("light")}>Jour</button>
      </div>
      {msg && <p className="notice">{msg}</p>}
      <div style={{ height: 24 }} />
    </div>
  );
}
