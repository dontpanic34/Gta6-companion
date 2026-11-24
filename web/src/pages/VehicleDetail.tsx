import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, DRIVETRAIN_FR, FIELD_LABELS, KIND_LABELS, STAT_LABELS, Stats, VehicleDetail } from "../api";
import { StatBars } from "./Vehicles";

const ORDER = ["manufacturer", "class", "based_on", "price", "seats", "drivetrain", "gears", "weight_kg",
  "model_year", "style", "era", "how_to_unlock", "location_text", "game_edition", "security", "access",
  "tracker", "can_register", "sell_price_stolen", "standout_set"];
const GARAGE = [["owned", "Possédé"], ["wanted", "Recherché"], ["favorite", "Favori"], ["lost", "Perdu"]];

function fmt(k: string, v: unknown) {
  if (k === "drivetrain" && typeof v === "string") return DRIVETRAIN_FR[v] ?? v;
  if ((k === "price" || k === "sell_price_stolen") && typeof v === "number") return `${v.toLocaleString("fr-FR")} $`;
  return String(v);
}

export default function VehicleDetailPage() {
  const { id = "" } = useParams();
  const [d, setD] = useState<VehicleDetail | null>(null);
  const [err, setErr] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => { setD(null); api.vehicle(id).then(setD).catch((e) => setErr(e.message)); }, [id]);
  if (err) return <div className="page"><p className="notice">{err}</p></div>;
  if (!d) return <div className="page muted">Chargement…</div>;

  const stats = Object.fromEntries(Object.keys(STAT_LABELS).map((k) => [k, (d.fields[k]?.value as number) ?? null])) as Stats;
  const keys = [...ORDER.filter((k) => d.fields[k]), ...Object.keys(d.fields).filter((k) => !ORDER.includes(k) && !(k in STAT_LABELS))];

  return (
    <div className="page">
      <Link to="/vehicules" className="muted small">← Véhicules</Link>
      <h1>{d.name}</h1>
      {d.media[0] ? <img className="thumb" src={d.media[0]} alt="" referrerPolicy="no-referrer" /> : <div className="thumb" />}
      {d.missable_warning && <p className="notice">⚠ Ce véhicule peut devenir définitivement inaccessible.</p>}

      <div className="row" style={{ margin: "14px 0" }}>
        {GARAGE.map(([k, l]) => (
          <button key={k} className={`chip ${status === k ? "on" : ""}`}
            onClick={() => api.setStatus(d.id, k).then(() => setStatus(k))}>{l}</button>
        ))}
      </div>

      <div className="card">
        <div className="row"><h2 style={{ margin: 0 }}>Statistiques</h2><span className="spacer" />
          {d.fields.speed && <span className={`badge kind-${d.fields.speed.kind}`}>{KIND_LABELS[d.fields.speed.kind]}</span>}</div>
        <div style={{ marginTop: 10 }}><StatBars stats={stats} /></div>
      </div>

      <h2>Fiche</h2>
      <div className="card">
        <table className="kv"><tbody>
          {keys.map((k) => {
            const f = d.fields[k];
            return (
              <tr key={k}>
                <td>{FIELD_LABELS[k] ?? k}</td>
                <td>
                  {fmt(k, f.value)}
                  {f.contradiction && <span className="badge warn" style={{ marginLeft: 6 }}>sources divergentes</span>}
                  <div className="small muted">
                    {f.sources.map((s, i) => (
                      <span key={i}>{i > 0 && " · "}{s.url ? <a href={s.url} target="_blank" rel="noreferrer">{s.source}</a> : s.source}
                        {f.contradiction && ` : ${fmt(k, s.value)}`}</span>
                    ))}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody></table>
        {d.hidden_fields > 0 && (
          <p className="small muted" style={{ marginTop: 10 }}>
            🔒 {d.hidden_fields} information(s) masquée(s) par la protection anti-spoiler (progression insuffisante ou non vérifiée).
          </p>
        )}
      </div>

      {!!d.siblings?.length && (<>
        <h2>Autres variantes</h2>
        <div className="row">{d.siblings.map((s) => <Link key={s.id} className="chip" to={`/vehicules/${encodeURIComponent(s.id)}`}>{s.name}</Link>)}</div>
      </>)}
      <h2>Kits et personnalisations</h2>
      {d.kits?.length || d.mods?.length ? (
        <div className="row">{[...(d.kits ?? []).map((k) => ({ ...k, category: "Kit" })), ...(d.mods ?? [])].map((m) =>
          <span key={m.id} className="chip">{m.category} · {m.name}</span>)}</div>
      ) : <p className="muted small">Aucune donnée de personnalisation pour l'instant.</p>}
    </div>
  );
}
