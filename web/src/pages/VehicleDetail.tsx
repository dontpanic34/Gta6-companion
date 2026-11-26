import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Ban, ChevronLeft, CircleCheck, Heart, Lock, MapPinned, Search as SearchIcon, TriangleAlert } from "lucide-react";
import { api, imgSrc, DRIVETRAIN_FR, FIELD_LABELS, KIND_LABELS, STAT_LABELS, VehicleDetail, WEAPON_STAT_LABELS } from "../api";
import { classStyle } from "../map/categories";
import { FamIcon } from "./MapPage";

type Detail = Omit<VehicleDetail, "siblings"> & {
  status?: string | null;
  map_points?: { id: string; name: string; x: number; y: number; precision: string }[];
  siblings?: { id: string; name: string; variant_type: string; image?: string | null }[];
};

// champs déjà affichés ailleurs (en-tête, stats) ou purement techniques
const HIDE = new Set(["class", "manufacturer", "price", "drivetrain", "seats", "base_model", "variants_list"]);
const TEXTS: [string, string][] = [["description", "Présentation"], ["design", "Design"], ["performance", "Conduite"],
  ["modifications", "Personnalisations"], ["location_text", "Où le trouver"], ["how_to_unlock", "Obtention"]];
const isText = (k: string) => TEXTS.some(([t]) => k === t || k === `${t}_en`);
const ORDER = ["based_on", "how_to_unlock", "location_text", "game_edition", "purchase_from", "capacity", "gears", "weight_kg",
  "model_year", "style", "era", "security", "access", "tracker", "can_register", "sell_price_stolen", "standout_set", "moddable"];
const GARAGE = [["owned", "Possédé", CircleCheck], ["wanted", "Recherché", SearchIcon], ["favorite", "Favori", Heart], ["lost", "Perdu", Ban]] as const;

const BODY_FR: [RegExp, string][] = [[/(\d)-door/gi, "$1 portes"], [/coup[eé]/gi, "coupé"], [/sedan|saloon/gi, "berline"],
  [/convertible|cabriolet/gi, "cabriolet"], [/roadster/gi, "roadster"], [/hatchback/gi, "compacte"], [/station wagon|estate/gi, "break"],
  [/pickup truck|pick-up/gi, "pick-up"], [/motorcycle/gi, "moto"], [/van/gi, "fourgon"], [/truck/gi, "camion"], [/targa/gi, "targa"]];

function fmt(k: string, v: unknown) {
  if (k === "body_style" && typeof v === "string") return BODY_FR.reduce((t, [rx, fr]) => t.replace(rx, fr), v).replace(/\s+/g, " ");
  if (k === "drivetrain" && typeof v === "string") return DRIVETRAIN_FR[v] ?? v;
  if ((k === "price" || k === "sell_price_stolen") && typeof v === "number") return `${v.toLocaleString("fr-FR")} $`;
  if (v === "Yes") return "Oui"; if (v === "No") return "Non";
  if (v === "Can be modified") return "Oui"; if (v === "Cannot be modified") return "Non";
  return String(v);
}

export default function VehicleDetailPage() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const [d, setD] = useState<Detail | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => { setD(null); window.scrollTo(0, 0); api.vehicle(id).then((x) => setD(x as Detail)).catch((e) => setErr(e.message)); }, [id]);
  if (err) return <div className="page"><p className="notice">{err}</p></div>;
  if (!d) return <div className="page muted">Chargement…</div>;

  const isWeapon = d.id.startsWith("weapon:");
  const route = isWeapon ? "/armes" : "/vehicules";
  const labels: Record<string, string> = isWeapon ? WEAPON_STAT_LABELS : STAT_LABELS;
  const f = (k: string) => d.fields[k]?.value as never;
  const st = classStyle(f("class"));
  const keys = [...ORDER.filter((k) => d.fields[k] && !isText(k)), ...Object.keys(d.fields).filter((k) => !ORDER.includes(k) && !HIDE.has(k) && !(k in labels) && !isText(k))];
  const texts = TEXTS.map(([k, l]) => {
    const fr = d.fields[k]?.value, en = d.fields[`${k}_en`]?.value;
    return fr ? { k, l, t: String(fr), en: false } : en ? { k, l, t: String(en), en: true } : null;
  }).filter(Boolean) as { k: string; l: string; t: string; en: boolean }[];
  const statKind = d.fields[Object.keys(labels)[0]]?.kind;
  const setStatus = (s: string) => {
    const next = d.status === s ? "to_discover" : s;
    api.setStatus(d.id, next).then(() => setD({ ...d, status: next }));
  };

  return (
    <div className="detail">
      <button className="iconback" onClick={() => nav(-1)} aria-label="Retour"><ChevronLeft size={24} /></button>
      <div className="d-hero" style={{ background: `linear-gradient(160deg, ${st.color}40, var(--bg) 70%)` }}>
        {d.media[0] && <img src={imgSrc(d.media[0])} alt="" referrerPolicy="no-referrer" onError={(e) => (e.currentTarget.style.display = "none")} />}
      </div>
      <div className="d-body">
        <div className="row" style={{ flexWrap: "nowrap", gap: 10 }}>
          <span className="famicon big" style={{ background: st.color }}><FamIcon f={st} size={20} color="#0d0b14" /></span>
          <div style={{ minWidth: 0 }}>
            <h1 className="d-title">{d.name}</h1>
            <div className="small muted">{f("manufacturer") ?? ""}{d.variant_type && d.variant_type !== "standard" ? " · variante" : ""}</div>
          </div>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          {f("class") && <span className="tag">{f("class")}</span>}
          {f("drivetrain") && <span className="tag">{fmt("drivetrain", f("drivetrain"))}</span>}
          {f("seats") && <span className="tag">{f("seats")} places</span>}
          {f("price") != null && <span className="tag">{fmt("price", f("price"))}</span>}
        </div>
        {d.missable_warning && <p className="notice"><TriangleAlert size={15} style={{ verticalAlign: "-3px" }} /> Peut devenir définitivement inaccessible.</p>}

        {!isWeapon && (
          <div className="garage">
            {GARAGE.map(([k, l, Icon]) => (
              <button key={k} className={d.status === k ? "on" : ""} onClick={() => setStatus(k)}><Icon size={18} />{l}</button>
            ))}
          </div>
        )}

        {(d.map_points?.length ?? 0) > 0 && (
          <button className="btn wide" style={{ marginTop: 12 }}
            onClick={() => nav(`/carte?x=${d.map_points![0].x}&y=${d.map_points![0].y}&z=5&focus=${encodeURIComponent(d.map_points![0].id)}`)}>
            <MapPinned size={18} /> Voir sur la carte{d.map_points!.length > 1 ? ` (${d.map_points!.length} emplacements)` : ""}</button>
        )}

        <section className="d-sec">
          <h4>Statistiques {statKind && <span className={`badge kind-${statKind}`}>{KIND_LABELS[statKind]}</span>}</h4>
          {Object.keys(labels).map((k) => {
            const v = d.fields[k]?.value as number | undefined;
            return (
              <div className="stat" key={k}>
                <span className="muted">{labels[k]}</span>
                <div className="bar big"><i style={{ width: `${((v ?? 0) / 10) * 100}%`, background: `linear-gradient(90deg, ${st.color}, var(--accent))` }} /></div>
                <span>{v ?? "—"}</span>
              </div>
            );
          })}
        </section>

        {!!d.siblings?.length && (
          <section className="d-sec">
            <h4>Variantes ({d.siblings.length + 1})</h4>
            <div className="cardrow">
              {d.siblings.map((s) => (
                <Link key={s.id} to={`${route}/${encodeURIComponent(s.id)}`} className="minicard">
                  {s.image ? <img src={imgSrc(s.image)} alt="" loading="lazy" referrerPolicy="no-referrer" onError={(e) => (e.currentTarget.style.visibility = "hidden")} /> : <div className="mc-ph" />}
                  <div className="title" style={{ fontSize: 13 }}>{s.name}</div>
                  <div className="small muted">{s.variant_type === "standard" ? "Modèle de base" : "Variante"}</div>
                </Link>
              ))}
            </div>
          </section>
        )}

        {texts.map((x) => (
          <section className="d-sec" key={x.k}>
            <h4>{x.l} {x.en && <span className="badge">EN</span>}</h4>
            <p className="d-text">{x.t}</p>
          </section>
        ))}

        <section className="d-sec">
          <h4>Infos</h4>
          {keys.map((k) => {
            const fv = d.fields[k];
            return (
              <div className="kvrow" key={k}>
                <span className="muted">{FIELD_LABELS[k] ?? k}</span>
                <span>{fmt(k, fv.value)}{fv.contradiction && <span className="badge warn" style={{ marginLeft: 6 }}>sources divergentes</span>}</span>
              </div>
            );
          })}
          {d.hidden_fields > 0 && <p className="small muted" style={{ marginTop: 10 }}><Lock size={13} style={{ verticalAlign: "-2px" }} /> {d.hidden_fields} info(s) masquée(s) par l'anti-spoiler.</p>}
        </section>

        {(d.kits?.length || d.mods?.length) ? (
          <section className="d-sec"><h4>Kits et personnalisations</h4>
            <div className="row">{[...(d.kits ?? []).map((k) => ({ ...k, category: "Kit" })), ...(d.mods ?? [])].map((m) => <span key={m.id} className="chip">{m.category} · {m.name}</span>)}</div>
          </section>
        ) : null}

        <p className="small muted" style={{ margin: "16px 0 8px" }}>
          Sources : {[...new Set(Object.values(d.fields).flatMap((x) => x.sources.map((s) => s.source)))].join(", ") || "—"}
        </p>
      </div>
    </div>
  );
}
