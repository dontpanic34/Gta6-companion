import { useEffect, useState } from "react";
import { api, getBaseUrl, getToken, Progress, setBaseUrl, setToken } from "../api";

export default function Settings() {
  const [p, setP] = useState<Progress | null>(null);
  const [token, setTok] = useState(getToken());
  const [base, setBase] = useState(getBaseUrl());
  const [saved, setSaved] = useState("");
  const [theme, setTheme] = useState(() => { try { return localStorage.getItem("theme") ?? "dark"; } catch { return "dark"; } });

  useEffect(() => { api.progress().then(setP).catch(() => {}); }, []);
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
