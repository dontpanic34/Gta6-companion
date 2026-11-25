import { useEffect, useState } from "react";
import { Gamepad2, RefreshCw } from "lucide-react";
import { api, getBaseUrl, getToken, Progress, setBaseUrl, setToken, XboxSummary } from "../api";

export default function Settings() {
  const [p, setP] = useState<Progress | null>(null);
  const [token, setTok] = useState(getToken());
  const [base, setBase] = useState(getBaseUrl());
  const [saved, setSaved] = useState("");
  const [theme, setTheme] = useState(() => { try { return localStorage.getItem("theme") ?? "dark"; } catch { return "dark"; } });

  const [xb, setXb] = useState<XboxSummary | null>(null);
  const [xbMsg, setXbMsg] = useState("");
  useEffect(() => { api.progress().then(setP).catch(() => {}); api.xbox().then(setXb).catch(() => {}); }, []);
  const syncXbox = () => { setXbMsg("Synchronisation…"); api.xboxSync().then((r) => {
    if (r.ok === false) { setXbMsg(r.error ?? "Échec"); return; }
    setXb(r); setXbMsg(`${r.new_unlocked ?? 0} nouveau(x) succès`); api.progress().then(setP).catch(() => {});
  }).catch((e) => setXbMsg(e.message)); };
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem("theme", theme); } catch { /* ignore */ }
  }, [theme]);

  return (
    <div className="page">
      <h1>Réglages</h1>
      <h2>Progression</h2>
      <div className="card filters">
        <label className="slider"><span>Chapitre actuel</span>
          <input type="number" className="input" min={0} value={p?.chapter ?? 0}
            onChange={(e) => p && setP({ ...p, chapter: +e.target.value })} /><span /></label>
        <p className="small muted">Missions terminées, personnages rencontrés et régions découvertes seront sélectionnables dès que l'encyclopédie des missions sera importée.</p>
        <button className="btn" onClick={() => p && api.setProgress(p).then(() => setSaved("Progression enregistrée"))}>Enregistrer</button>
      </div>
      <h2>Xbox</h2>
      <div className="card filters">
        <div className="row"><Gamepad2 size={20} color="var(--accent)" />
          <span>{xb ? `${xb.unlocked_count} / ${xb.total} succès débloqués` : "Non synchronisé"}</span><span className="spacer" />
          <button className="btn ghost small" onClick={syncXbox}><RefreshCw size={15} /> Synchroniser</button></div>
        {xbMsg && <p className="small muted" style={{ margin: 0 }}>{xbMsg}</p>}
        {xb?.unlocked.slice(0, 5).map((a) => <div key={a.name} className="small">• {a.name}</div>)}
        <p className="small muted" style={{ margin: 0 }}>Les succès non débloqués ne sont jamais nommés (anti-spoiler). Clé OpenXBL à placer sur le PC (XBL_API_KEY).</p>
      </div>
      <h2>Apparence</h2>
      <div className="row">
        <button className={`chip ${theme === "dark" ? "on" : ""}`} onClick={() => setTheme("dark")}>Sombre</button>
        <button className={`chip ${theme === "light" ? "on" : ""}`} onClick={() => setTheme("light")}>Clair</button>
      </div>
      <h2>Connexion au PC</h2>
      <div className="card filters">
        <input className="input" placeholder="Adresse du PC (ex. http://100.64.0.5:8765)" value={base} onChange={(e) => setBase(e.target.value)} />
        <input className="input" placeholder="Jeton d'accès (COMPANION_TOKEN)" value={token} onChange={(e) => setTok(e.target.value)} />
        <button className="btn ghost" onClick={() => { setBaseUrl(base); setToken(token); setSaved("Connexion enregistrée"); }}>Enregistrer</button>
      </div>
      {saved && <p className="notice">{saved}</p>}
    </div>
  );
}
