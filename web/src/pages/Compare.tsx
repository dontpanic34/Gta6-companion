import { ChevronLeft, Circle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, STAT_LABELS, VehicleDetail, WEAPON_STAT_LABELS } from "../api";
type Stats = Record<string, number | null>;
// Module-level mutable: set per comparison (vehicles vs weapons)
let LABELS: Record<string, string> = STAT_LABELS;

let KEYS: string[] = Object.keys(STAT_LABELS);
const COLORS = ["#ff4f8b", "#38d6c4", "#ffa24c", "#a78bfa"];

function Radar({ series }: { series: { name: string; stats: Stats }[] }) {
  const size = 300, c = size / 2, r = 110;
  const pt = (i: number, v: number) => {
    const a = (Math.PI * 2 * i) / KEYS.length - Math.PI / 2;
    return [c + Math.cos(a) * r * (v / 10), c + Math.sin(a) * r * (v / 10)];
  };
  return (
    <svg viewBox={`0 0 ${size} ${size}`} style={{ width: "100%", maxWidth: 360, display: "block", margin: "0 auto" }}>
      {[2.5, 5, 7.5, 10].map((lv) => (
        <polygon key={lv} points={KEYS.map((_, i) => pt(i, lv).join(",")).join(" ")} fill="none" stroke="var(--line)" />
      ))}
      {KEYS.map((k, i) => {
        const [x, y] = pt(i, 11.8);
        return <text key={k} x={x} y={y} fill="var(--muted)" fontSize="10" textAnchor="middle" dominantBaseline="middle">{LABELS[k]}</text>;
      })}
      {series.map((s, si) => (
        <polygon key={s.name} points={KEYS.map((k, i) => pt(i, s.stats[k] ?? 0).join(",")).join(" ")}
          fill={COLORS[si]} fillOpacity={0.15} stroke={COLORS[si]} strokeWidth={2} />
      ))}
    </svg>
  );
}

export default function Compare() {
  const [sp] = useSearchParams();
  const ids = (sp.get("ids") ?? "").split(",").filter(Boolean);
  const weaponMode = ids[0]?.startsWith("weapon:");
  LABELS = weaponMode ? WEAPON_STAT_LABELS : STAT_LABELS;
  KEYS = Object.keys(LABELS);
  const [items, setItems] = useState<VehicleDetail[]>([]);
  const [weights, setWeights] = useState<Record<string, number>>({});

  useEffect(() => {
    Promise.all(ids.map((i) => api.vehicle(i))).then(setItems).catch(() => setItems([]));
    api.pref<Record<string, number> | null>(weaponMode ? "weapon_weights" : "vehicle_weights")
      .then((w) => setWeights(w ?? (weaponMode ? { damage: 0.4, accuracy: 0.25, range: 0.2, weapon_handling: 0.15 } : {}))).catch(() => {});
  }, [sp]);

  const series = items.map((d) => ({
    name: d.name, id: d.id,
    stats: Object.fromEntries(KEYS.map((k) => [k, (d.fields[k]?.value as number) ?? null])) as Stats,
  }));
  const score = (s: Stats) => {
    const known = KEYS.filter((k) => s[k] != null && (weights[k] ?? 0) > 0);
    const tw = known.reduce((a, k) => a + weights[k], 0);
    return tw ? +(known.reduce((a, k) => a + (s[k] as number) * weights[k], 0) / tw).toFixed(2) : null;
  };
  const ranked = [...series].sort((a, b) => (score(b.stats) ?? -1) - (score(a.stats) ?? -1));

  return (
    <div className="page">
      <Link to={weaponMode ? "/armes" : "/vehicules"} className="muted small"><ChevronLeft size={16} style={{ verticalAlign: "-3px" }} />Véhicules</Link>
      <h1>Comparateur</h1>
      <div className="card">
        <Radar series={series} />
        <div className="row" style={{ justifyContent: "center", marginTop: 8 }}>
          {series.map((s, i) => <span key={s.id} className="small"><b style={{ color: COLORS[i] }}><Circle size={10} fill="currentColor" /></b> {s.name}</span>)}
        </div>
      </div>

      <h2>Pondération</h2>
      <div className="card filters">
        {KEYS.map((k) => (
          <label className="slider" key={k}><span>{LABELS[k]}</span>
            <input type="range" min={0} max={1} step={0.05} value={weights[k] ?? 0}
              onChange={(e) => setWeights({ ...weights, [k]: +e.target.value })} />
            <span>{Math.round((weights[k] ?? 0) * 100)}</span></label>
        ))}
        <button className="btn ghost" onClick={() => api.setPref(weaponMode ? "weapon_weights" : "vehicle_weights", weights)}>Enregistrer comme mon profil</button>
      </div>

      <h2>Classement</h2>
      <div className="card"><table className="kv"><tbody>
        <tr><td></td>{ranked.map((s) => <td key={s.id}><b>{s.name}</b></td>)}</tr>
        <tr><td>Score pondéré</td>{ranked.map((s) => <td key={s.id}><span className="badge score">{score(s.stats) ?? "—"}</span></td>)}</tr>
        {KEYS.map((k) => {
          const best = Math.max(...ranked.map((s) => s.stats[k] ?? -1));
          return <tr key={k}><td>{LABELS[k]}</td>{ranked.map((s) =>
            <td key={s.id} style={{ color: s.stats[k] === best && best >= 0 ? "var(--accent)" : undefined }}>{s.stats[k] ?? "—"}</td>)}</tr>;
        })}
      </tbody></table>
      <p className="small muted">« — » = statistique inconnue (jamais estimée). Valeurs : mesures communautaires GTABase sur 10.</p></div>
    </div>
  );
}
