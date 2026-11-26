import { offlineChat } from "../offlineAssistant";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowUp, CarFront, Crosshair, GitCompare, MapPinned, Mic, Sparkles, Volume2, VolumeX } from "lucide-react";
import { canSpeak, listen, speak, voiceAvailable } from "../device";
import { api, ChatAction, ChatReply, entityLink } from "../api";

interface Msg { role: "user" | "assistant"; content: string; reply?: ChatReply }
const KEY = "assistant_history_v1";
const SUGGESTIONS = [
  "Je viens d'arriver à Port Gellhorn, qu'est-ce que je peux faire ?",
  "Je cherche une voiture polyvalente qui ne dérape pas",
  "Quelles voitures sont meilleures hors route ?",
  "J'ai besoin d'une arme avec un silencieux",
];

function actionLabel(a: ChatAction) {
  switch (a.type) {
    case "open_map": return { label: "Voir sur la carte", Icon: MapPinned };
    case "open_vehicles": return { label: "Ouvrir le catalogue filtré", Icon: CarFront };
    case "open_weapons": return { label: "Voir les armes", Icon: Crosshair };
    case "open_compare": return { label: "Ouvrir le comparateur", Icon: GitCompare };
    default: return null;
  }
}

export default function Assistant() {
  const nav = useNavigate();
  const [msgs, setMsgs] = useState<Msg[]>(() => { try { return JSON.parse(localStorage.getItem(KEY) ?? "[]"); } catch { return []; } });
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const [hasMic, setHasMic] = useState(false);
  const [listening, setListening] = useState(false);
  const [voiceOut, setVoiceOut] = useState(() => { try { return localStorage.getItem("assistant_voice") === "1"; } catch { return false; } });
  useEffect(() => { voiceAvailable().then(setHasMic); }, []);
  useEffect(() => { try { localStorage.setItem("assistant_voice", voiceOut ? "1" : "0"); } catch { /* ignore */ } }, [voiceOut]);
  const talk = async () => {
    if (listening) return;
    setListening(true);
    try { const t = await listen(); if (t) await send(t, true); }
    catch (e) { setMsgs((m) => [...m, { role: "assistant", content: (e as Error).message }]); }
    finally { setListening(false); }
  };

  useEffect(() => {
    try { localStorage.setItem(KEY, JSON.stringify(msgs.slice(-40))); } catch { /* ignore */ }
    end.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);

  const send = async (text: string, spoken = false) => {
    const t = text.trim(); if (!t || busy) return;
    setInput(""); setBusy(true);
    const history = msgs.map(({ role, content }) => ({ role, content }));
    setMsgs((m) => [...m, { role: "user", content: t }]);
    try {
      const reply = await api.chat(t, history);
      setMsgs((m) => [...m, { role: "assistant", content: reply.text, reply }]);
      if (voiceOut || spoken) speak(reply.text);   // question posée à la voix -> réponse lue à voix haute
    } catch (e) {
      // PC injoignable : recherche locale dans les données du téléphone
      const reply = await offlineChat(t);
      setMsgs((m) => [...m, { role: "assistant", content: reply.text, reply }]);
      if (voiceOut || spoken) speak(reply.text);
      (window as any).__autoConnect?.();   // relance la recherche du PC en arrière-plan
      void e;
    } finally { setBusy(false); }
  };

  const run = (a: ChatAction) => {
    if (a.type === "open_map") nav(`/carte?x=${a.x}&y=${a.y}&z=${a.zoom ?? 5}`);
    if (a.type === "open_vehicles") nav(`/vehicules?${new URLSearchParams(a.params ?? [])}`);
    if (a.type === "open_weapons") nav(`/armes?${new URLSearchParams(a.params ?? [])}`);
    if (a.type === "open_compare") nav(`/vehicules/comparer?ids=${(a.ids ?? []).map(encodeURIComponent).join(",")}`);
  };

  return (
    <div className="chat">
      <div className="chat-scroll">
        <div className="row" style={{ padding: "8px 2px 4px" }}>
          <h1 style={{ margin: 0 }}>Assistant</h1><span className="spacer" />
          {canSpeak() && <button className={`chip ${voiceOut ? "on" : ""}`} onClick={() => setVoiceOut(!voiceOut)} aria-label="Lecture vocale">{voiceOut ? <Volume2 size={15} /> : <VolumeX size={15} />}</button>}
          {msgs.length > 0 && <button className="chip" onClick={() => setMsgs([])}>Nouvelle</button>}
        </div>
        {msgs.length === 0 && (
          <div className="chat-empty">
            <Sparkles size={28} color="var(--accent)" />
            {hasMic && <button className="bigmic" onClick={talk}><Mic size={34} /><span>{listening ? "Je vous écoute…" : "Appuyez et parlez"}</span></button>}
            <p>Demandez-moi quoi faire dans une zone, quelle voiture choisir, où trouver une arme… Je ne révèle jamais la suite d'une quête.</p>
            <div style={{ display: "grid", gap: 8 }}>
              {SUGGESTIONS.map((s) => <button key={s} className="suggest" onClick={() => send(s)}>{s}</button>)}
            </div>
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            <div>{m.content}</div>
            {!!m.reply?.cards?.length && (
              <div className="cardrow">
                {m.reply.cards.map((c) => (
                  <Link key={c.id} to={entityLink(c.id)} className="minicard">
                    {c.image ? <img src={c.image} alt="" loading="lazy" referrerPolicy="no-referrer" onError={(e) => (e.currentTarget.style.visibility = "hidden")} /> : <div className="mc-ph" />}
                    <div className="ellipsis title">{c.name}</div>
                    {c.subtitle && <div className="ellipsis small muted">{c.subtitle}</div>}
                  </Link>
                ))}
              </div>
            )}
            {!!m.reply?.actions?.length && (
              <div className="row" style={{ marginTop: 8 }}>
                {m.reply.actions.map((a, j) => { const l = actionLabel(a); return l && (
                  <button key={j} className="btn ghost small" onClick={() => run(a)}><l.Icon size={16} />{l.label}</button>); })}
              </div>
            )}
            {m.reply?.engine && <div className="engine">{m.reply.engine === "règles" ? "mode sans IA" : m.reply.engine}</div>}
          </div>
        ))}
        {busy && <div className="bubble assistant"><span className="typing"><i /><i /><i /></span></div>}
        <div ref={end} />
      </div>
      <form className="composer" onSubmit={(e) => { e.preventDefault(); send(input); }}>
        {hasMic && <button type="button" className={`mic ${listening ? "on" : ""}`} onClick={talk} aria-label="Parler"><Mic size={22} /></button>}
        <input placeholder={listening ? "Je vous écoute…" : "Posez votre question…"} value={input} onChange={(e) => setInput(e.target.value)} />
        <button className="send" disabled={!input.trim() || busy} aria-label="Envoyer"><ArrowUp size={20} /></button>
      </form>
    </div>
  );
}
