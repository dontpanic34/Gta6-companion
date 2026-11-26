import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowDownUp, Check, GitCompare, Plus, Search, SlidersHorizontal, X } from "lucide-react";
import { api, imgSrc, DRIVETRAIN_FR, STAT_LABELS, VehicleSummary, WEAPON_STAT_LABELS, WeaponSummary } from "../api";
import { classStyle } from "../map/categories";
import { onBack } from "../back";
import { FamIcon } from "./MapPage";

type Kind = "vehicle" | "weapon";
type Item = (VehicleSummary | WeaponSummary) & { stats: Record<string, number | null> };

const CONF = {
  vehicle: {
    title: "Véhicules", route: "/vehicules", labels: STAT_LABELS as Record<string, string>, classParam: "vclass",
    sorts: [["balanced", "Équilibrée"], ["speed", "Plus rapide"], ["acceleration", "Accélération"], ["handling_road", "Plus maniable"], ["handling_offroad", "Tout-terrain"], ["strength", "Solidité"], ["profile", "Mon style"], ["price", "Prix"], ["name", "Nom"]],
    quick: [["exclude_class", "Muscle", "Sans muscle cars"], ["min_handling_offroad", "6", "Bon hors route"], ["drivetrain", "AWD", "Intégrale"]],
  },
  weapon: {
    title: "Armes", route: "/armes", labels: WEAPON_STAT_LABELS, classParam: "wclass",
    sorts: [["balanced", "Équilibrée"], ["damage", "Dégâts"], ["name", "Nom"], ["accuracy", "Précision"], ["range", "Portée"], ["weapon_handling", "Maniabilité"], ["price", "Prix"]],
    quick: [["free_only", "true", "Gratuites"]],
  },
} as const;

/** Grandes familles de véhicules -> classes (sous-familles). */
export const VEHICLE_TYPES: { id: string; label: string; match: RegExp }[] = [
  { id: "voitures", label: "Voitures", match: /.*/ },
  { id: "motos", label: "Motos", match: /^motorcycles?$/i },
  { id: "bateaux", label: "Bateaux", match: /^boats?$/i },
  { id: "aerien", label: "Avions & hélicos", match: /^(planes?|helicopters?)$/i },
  { id: "velos", label: "Vélos", match: /^cycles?$/i },
  { id: "autres", label: "Autres", match: /^trains?$/i },
];
export const typeOf = (cls: string | null) => (VEHICLE_TYPES.slice(1).find((t) => t.match.test(cls ?? "")) ?? VEHICLE_TYPES[0]).id;
const CLASS_FR: Record<string, string> = { Super: "Super", Sports: "Sportives", Muscle: "Muscle", Coupes: "Coupés", Sedans: "Berlines",
  SUVs: "SUV", Pickups: "Pick-up", "Off-Road": "Tout-terrain", Compacts: "Compactes", Vans: "Vans", Commercial: "Utilitaires",
  Emergency: "Urgence", Motorcycles: "Motos", Boats: "Bateaux", Planes: "Avions", Helicopters: "Hélicoptères", Cycles: "Vélos", Trains: "Trains" };
export const classFr = (c: string | null) => (c ? CLASS_FR[c] ?? c : "Autres");

const SHORT: Record<string, string> = { speed: "Vit", acceleration: "Acc", handling_road: "Man", handling_offroad: "TT", strength: "Sol", damage: "Dég", accuracy: "Préc", weapon_handling: "Man", range: "Port" };

export function StatMini({ stats, keys, highlight, onPick }: { stats: Record<string, number | null>; keys: string[]; highlight?: string; onPick?: (k: string) => void }) {
  return (
    <div className="statmini">
      {keys.slice(0, 4).map((k) => (
        <div key={k} className={k === highlight ? "hl" : ""}
          onClick={onPick ? (e) => { e.preventDefault(); e.stopPropagation(); onPick(k); } : undefined}><span>{SHORT[k] ?? k}</span><div className="bar"><i style={{ width: `${((stats[k] ?? 0) / 10) * 100}%` }} /></div><b>{stats[k] ?? "—"}</b></div>
      ))}
    </div>
  );
}

export default function Catalog({ kind }: { kind: Kind }) {
  const conf = CONF[kind];
  const nav = useNavigate();
  const [sp, setSp] = useSearchParams();
  const [all, setAll] = useState<Item[] | null>(null);
  const [err, setErr] = useState("");
  const [sheet, setSheet] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  useEffect(() => onBack(() => { if (sheet) { setSheet(false); return true; } return false; }), [sheet]);
  const [sort, setSort] = useState<string>(() => sp.get("sort") ?? "balanced");
  const vtype = kind === "vehicle" ? (sp.get("type") ?? "voitures") : null;
  const [weights, setWeights] = useState<Record<string, number>>({});
  useEffect(() => {
    if (kind === "vehicle") api.pref<Record<string, number>>("vehicle_weights").then((w) => setWeights(w ?? {})).catch(() => {});
  }, [kind]);

  // le serveur (ou l'instantané) filtre ; le tri se fait ici
  const serverParams = useMemo(() => { const n = new URLSearchParams(sp); n.delete("sort"); n.delete("q"); return n.toString(); }, [sp]);
  useEffect(() => {
    setAll(null);
    (kind === "vehicle" ? api.vehicles(new URLSearchParams(serverParams)) : api.weapons(new URLSearchParams(serverParams)))
      .then((x) => setAll(x as Item[])).catch((e) => setErr(e.message));
  }, [serverParams, kind]);

  const q = (sp.get("q") ?? "").toLowerCase();
  const cls = sp.get(conf.classParam);
  const items = useMemo(() => {
    let l = (all ?? []).filter((v) => !q || v.name.toLowerCase().includes(q) || (v.class ?? "").toLowerCase().includes(q))
      .filter((v) => !vtype || typeOf(v.class) === vtype);
    const keys = Object.keys(conf.labels);
    const avg = (v: Item) => { const xs = keys.map((k) => v.stats[k]).filter((x): x is number => typeof x === "number"); return xs.length >= 3 ? xs.reduce((a, b) => a + b, 0) / xs.length : -1; };
    // stat principale, puis moyenne des autres pour départager
    const by = (k: string) => (a: Item, b: Item) => (((b.stats[k] ?? -1) as number) - ((a.stats[k] ?? -1) as number)) || (avg(b) - avg(a));
    if (!["name", "profile", "price", "balanced"].includes(sort)) l = l.filter((v) => v.stats[sort] != null).concat(l.filter((v) => v.stats[sort] == null));
    if (sort === "balanced") l = [...l].map((v) => ({ v, s: avg(v) })).sort((a, b) => b.s - a.s)
      .map(({ v, s }) => (s >= 0 ? { ...v, score: { value: +s.toFixed(1), coverage: 1 } } : { ...v, score: null }));
    else if (sort === "name") l = [...l].sort((a, b) => a.name.localeCompare(b.name));
    else if (sort === "profile") {
      // score « mon style » calculé localement (stats inconnues ignorées, jamais estimées)
      const sc = (v: Item) => {
        const known = Object.entries(weights).filter(([k, w]) => w > 0 && typeof v.stats[k] === "number");
        const tw = known.reduce((a, [, w]) => a + w, 0);
        return tw ? known.reduce((a, [k, w]) => a + (v.stats[k] as number) * w, 0) / tw * Math.min(1, tw / 0.6) : -1;
      };
      l = [...l].map((v) => ({ v, s: sc(v) })).sort((a, b) => b.s - a.s).map(({ v, s }) => (s >= 0 && !v.score ? { ...v, score: { value: +s.toFixed(1), coverage: 1 } } : v));
    }
    else if (sort === "price") l = [...l].sort((a, b) => (a.price ?? 1e12) - (b.price ?? 1e12));
    else l = [...l].sort(by(sort));
    return l;
  }, [all, q, sort, weights, vtype]);
  const classes = useMemo(() => {
    const n: Record<string, number> = {};
    (all ?? []).filter((v) => !vtype || typeOf(v.class) === vtype).forEach((v) => { if (v.class) n[v.class] = (n[v.class] ?? 0) + 1; });
    return Object.entries(n).sort((a, b) => b[1] - a[1]);
  }, [all, vtype]);
  const typeCount = useMemo(() => {
    const n: Record<string, number> = {};
    (all ?? []).forEach((v) => { const t = typeOf(v.class); n[t] = (n[t] ?? 0) + 1; });
    return n;
  }, [all]);

  const set = (k: string, v: string | null) => { const n = new URLSearchParams(sp); v === null || v === "" ? n.delete(k) : n.set(k, v); setSp(n, { replace: true }); };
  const toggleQuick = (k: string, v: string) => {
    const n = new URLSearchParams(sp); const cur = n.getAll(k); n.delete(k);
    (cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v]).forEach((x) => n.append(k, x));

    setSp(n, { replace: true });
  };
  const toggleSel = (id: string) => setSelected((s) => s.includes(id) ? s.filter((x) => x !== id) : s.length < 4 ? [...s, id] : s);
  const statKeys = Object.keys(conf.labels);
  const activeCount = [...sp.keys()].filter((k) => !["q", "sort", conf.classParam].includes(k)).length;

  return (
    <div className="catalog">
      <div className="cat-head">
        <h1>{conf.title}</h1>
        <span className="muted small">{all ? `${items.length} / ${all.length}` : "…"}</span>
      </div>
      {kind === "vehicle" && (
        <div className="typebar">
          {VEHICLE_TYPES.filter((t) => typeCount[t.id]).map((t) => (
            <button key={t.id} className={vtype === t.id ? "on" : ""} onClick={() => { const n = new URLSearchParams(sp); n.set("type", t.id); n.delete("vclass"); setSp(n, { replace: true }); }}>
              {t.label}<i>{typeCount[t.id]}</i></button>))}
        </div>
      )}
      <div className="rankbar">
        <span className="small muted"><ArrowDownUp size={14} style={{ verticalAlign: "-2px" }} /> Classer par</span>
        <div className="chiprow">
          {conf.sorts.map(([k, l]) => (
            <button key={k} className={`chip ${sort === k ? "on" : ""}`} onClick={() => setSort(k)}>{l}</button>))}
        </div>
      </div>
      <div className="cat-list">
        {err && <p className="notice">{err}</p>}
        {all && items.length === 0 && (
          <div className="empty">Aucun résultat avec ces filtres.<br />
            <button className="btn" style={{ marginTop: 12 }} onClick={() => { setSp(new URLSearchParams(), { replace: true }); setSort("balanced"); }}>Tout effacer</button></div>
        )}
        {items.map((v, idx) => {
          const st = classStyle(v.class);
          const ranked = sort !== "name";
          const on = selected.includes(v.id);
          return (
            <div key={v.id} className="vrow">
              <Link to={`${conf.route}/${encodeURIComponent(v.id)}`} className="vrow-main">
                <div className="vthumb" style={{ background: `linear-gradient(135deg, ${st.color}33, transparent)` }}>
                  {v.image ? <img src={imgSrc(v.image)} alt="" loading="lazy" referrerPolicy="no-referrer" onError={(e) => (e.currentTarget.style.display = "none")} />
                    : null}
                  <span className="vclass" style={{ background: st.color }}><FamIcon f={st} size={13} color="#0d0b14" /></span>
                  {ranked && <span className="rank">#{idx + 1}</span>}
                </div>
                <div className="vinfo">
                  <div className="row" style={{ flexWrap: "nowrap", gap: 6 }}>
                    <span className="title ellipsis">{v.name}</span>
                    {v.score && <span className="badge score">{v.score.value}</span>}
                  </div>
                  <div className="small muted ellipsis">
                    {kind === "vehicle" ? classFr(v.class) : v.class}{"drivetrain" in v && v.drivetrain ? ` · ${DRIVETRAIN_FR[v.drivetrain] ?? v.drivetrain}` : ""}
                    {v.price != null ? ` · ${v.price.toLocaleString("fr-FR")} $` : ""}
                    {"free_hint" in v && v.free_hint ? " · gratuite ?" : ""}
                  </div>
                  <StatMini stats={v.stats} keys={statKeys} highlight={sort} onPick={setSort} />
                </div>
              </Link>
              <button className={`selbtn ${on ? "on" : ""}`} onClick={() => toggleSel(v.id)} aria-label="Comparer">{on ? <Check size={18} /> : <Plus size={18} />}</button>
            </div>
          );
        })}
      </div>

      <div className="cat-bottom">
        {selected.length > 0 && (
          <div className="row" style={{ flexWrap: "nowrap" }}>
            <button className="btn grow" disabled={selected.length < 2}
              onClick={() => nav(`/vehicules/comparer?ids=${selected.map(encodeURIComponent).join(",")}`)}>
              <GitCompare size={18} /> Comparer {selected.length}/4</button>
            <button className="btn ghost" onClick={() => setSelected([])} aria-label="Vider"><X size={18} /></button>
          </div>
        )}
        <div className="chiprow">
          {conf.quick.map(([k, v, l]) => (
            <button key={k + v} className={`chip ${sp.getAll(k).includes(v) ? "on" : ""}`} onClick={() => toggleQuick(k, v)}>
              {l}</button>
          ))}
          {classes.map(([c, n]) => { const s = classStyle(c); return (
            <button key={c} className={`chip ${cls === c ? "on" : ""}`} onClick={() => set(conf.classParam, cls === c ? null : c)}>
              <FamIcon f={s} size={14} /> {kind === "vehicle" ? classFr(c) : c} <span className="muted small">{n}</span></button>); })}
        </div>
        <div className="row" style={{ flexWrap: "nowrap", gap: 8 }}>
          <div className="searchbar grow">
            <Search size={18} className="muted" />
            <input placeholder={`Chercher ${kind === "vehicle" ? "un véhicule" : "une arme"}`} value={sp.get("q") ?? ""} onChange={(e) => set("q", e.target.value)} />
            {sp.get("q") && <button className="iconbtn" onClick={() => set("q", null)} aria-label="Effacer"><X size={18} /></button>}
          </div>
          <button className={`sqbtn ${activeCount ? "on" : ""}`} onClick={() => setSheet(true)} aria-label="Filtres et tri">
            <SlidersHorizontal size={22} />{activeCount ? <i>{activeCount}</i> : null}</button>
        </div>
      </div>

      {sheet && (<>
        <div className="scrim" onClick={() => setSheet(false)} />
        <div className="sheet">
          <div className="grabber" />
          <div className="row"><h2 style={{ margin: 0 }}>Filtrer</h2><span className="spacer" />
            <button className="btn ghost small" onClick={() => { setSp(new URLSearchParams(), { replace: true }); setSort("name"); }}>Réinitialiser</button></div>
          <h4 className="sheet-h">Prix maximum</h4>
          <div className="filters">
            <label className="slider"><span>Jusqu'à</span>
              <input type="number" className="input" inputMode="numeric" placeholder="Illimité" value={sp.get("max_price") ?? ""} onChange={(e) => set("max_price", e.target.value)} /><span>$</span></label>
          </div>
          {kind === "vehicle" && (<>
            <h4 className="sheet-h">Transmission</h4>
            <div className="row">{["RWD", "FWD", "AWD"].map((d) => <button key={d} className={`chip ${sp.getAll("drivetrain").includes(d) ? "on" : ""}`} onClick={() => toggleQuick("drivetrain", d)}>{DRIVETRAIN_FR[d]}</button>)}</div>
            <h4 className="sheet-h">Places minimum</h4>
            <div className="row">{["2", "4", "6"].map((n) => <button key={n} className={`chip ${sp.get("seats_min") === n ? "on" : ""}`} onClick={() => set("seats_min", sp.get("seats_min") === n ? null : n)}>{n}+</button>)}</div>
            <h4 className="sheet-h">Variantes</h4>
            <div className="row">{[["named", "Variantes"], ["standard", "Modèles de base"]].map(([k, l]) =>
              <button key={k} className={`chip ${sp.getAll("variant_type").includes(k) ? "on" : ""}`} onClick={() => toggleQuick("variant_type", k)}>{l}</button>)}</div>
          </>)}
          <div className="sheet-footer"><button className="btn wide" onClick={() => setSheet(false)}>Voir {items.length} résultats</button></div>
        </div>
      </>)}
    </div>
  );
}
