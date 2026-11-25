import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { api, entityLink, getBaseUrl, Place } from "../api";
import { ALL_FAMILIES, familyOf } from "../map/categories";
import { createTileLayer, distance, gameToLatLng, latLngToGame, LEONIDA_BOUNDS, TILE_BOUNDS } from "../map/leonida";

const STORE = "map_state_v1";
interface MapState { families: string[]; hideDone: boolean; me: [number, number] | null }
const load = (): MapState => {
  try { return { families: [], hideDone: false, me: null, ...JSON.parse(localStorage.getItem(STORE) ?? "{}") }; }
  catch { return { families: [], hideDone: false, me: null }; }
};

export default function MapPage() {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const layer = useRef<L.LayerGroup | null>(null);
  const meLayer = useRef<L.LayerGroup | null>(null);
  const [places, setPlaces] = useState<Place[]>([]);
  const [st, setSt] = useState<MapState>(load);
  const [q, setQ] = useState("");
  const [picked, setPicked] = useState<Place | null>(null);
  const [sheet, setSheet] = useState<"filters" | "nearby" | null>(null);
  const [err, setErr] = useState("");
  const [hint, setHint] = useState("");
  const [zoom, setZoom] = useState(2);

  useEffect(() => { try { localStorage.setItem(STORE, JSON.stringify(st)); } catch { /* ignore */ } }, [st]);
  useEffect(() => { api.places(new URLSearchParams()).then(setPlaces).catch((e) => setErr(e.message)); }, []);

  // Carte (une seule fois)
  useEffect(() => {
    if (!el.current || map.current) return;
    const m = L.map(el.current, {
      crs: L.CRS.Simple, zoomControl: false, minZoom: 1, maxZoom: 7,
      maxBounds: TILE_BOUNDS.pad(0.1), maxBoundsViscosity: 0.8, preferCanvas: true, zoomSnap: 0.25,
    });
    createTileLayer(getBaseUrl()).addTo(m);
    m.fitBounds(LEONIDA_BOUNDS);
    layer.current = L.layerGroup().addTo(m);
    meLayer.current = L.layerGroup().addTo(m);
    m.on("contextmenu", (e: L.LeafletMouseEvent) => {   // appui long = « Je suis ici »
      setSt((s) => ({ ...s, me: latLngToGame(e.latlng) }));
      setHint("Position enregistrée");
      setTimeout(() => setHint(""), 1500);
    });
    m.on("click", () => setPicked(null));
    m.on("zoomend", () => setZoom(Math.round(m.getZoom())));
    setZoom(Math.round(m.getZoom()));
    map.current = m;
    return () => { m.remove(); map.current = null; };
  }, []);

  const visible = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return places.filter((p) => {
      const fam = familyOf(p.category, p.id.startsWith("secret:")).id;
      if (st.families.length && !st.families.includes(fam)) return false;
      if (st.hideDone && (p.status === "done" || p.status === "discovered")) return false;
      if (needle && !`${p.name} ${p.category ?? ""} ${p.region ?? ""}`.toLowerCase().includes(needle)) return false;
      return true;
    });
  }, [places, st.families, st.hideDone, q]);

  // Marqueurs (rendu canvas : fluide même avec des milliers de points)
  useEffect(() => {
    const g = layer.current; if (!g) return;
    g.clearLayers();
    visible.forEach((p) => {
      if (p.x == null || p.y == null) return;
      const f = familyOf(p.category, p.id.startsWith("secret:"));
      const done = p.status === "done" || p.status === "discovered";
      L.circleMarker(gameToLatLng(p.x, p.y), {
        radius: zoom >= 5 ? 9 : zoom >= 4 ? 7 : zoom >= 3 ? 5 : 3.5, color: "#0d0b14", weight: zoom >= 3 ? 1.5 : 0.8,
        fillColor: f.color, fillOpacity: done ? 0.35 : 0.95,
      }).on("click", (e) => { L.DomEvent.stopPropagation(e); setPicked(p); }).addTo(g);
    });
  }, [visible, zoom]);

  // Ma position (saisie manuelle)
  useEffect(() => {
    const g = meLayer.current; if (!g) return;
    g.clearLayers();
    if (st.me) {
      const ll = gameToLatLng(...st.me);
      L.circle(ll, { radius: 1500 / 32, color: "#ff4f8b", weight: 1, fillOpacity: 0.06, interactive: false }).addTo(g);
      L.circleMarker(ll, { radius: 10, color: "#fff", weight: 3, fillColor: "#ff4f8b", fillOpacity: 1, interactive: false }).addTo(g);
    }
  }, [st.me]);

  const nearby = useMemo(() => {
    if (!st.me) return [];
    const pos = st.me;
    const withPos = visible.filter((p) => p.x != null).map((p) => ({ p, d: distance(pos, [p.x!, p.y!]) }))
      .sort((a, b) => a.d - b.d).slice(0, 40);
    const region = withPos[0]?.p.region;
    const secrets = visible.filter((p) => p.x == null && region && p.region === region).map((p) => ({ p, d: -1 }));
    return [...secrets, ...withPos];
  }, [st.me, visible]);

  const toggleFam = (id: string) => setSt((s) => ({ ...s, families: s.families.includes(id) ? s.families.filter((x) => x !== id) : [...s.families, id] }));
  const mark = (p: Place, status: string) => api.setStatus(p.id, status).then(() => {
    setPlaces((all) => all.map((x) => (x.id === p.id ? { ...x, status } : x)));
    setPicked((x) => (x && x.id === p.id ? { ...x, status } : x));
  });
  const aroundMe = () => {
    if (!st.me) { setHint("Appui long sur la carte pour indiquer où vous êtes"); setTimeout(() => setHint(""), 2500); return; }
    map.current?.flyTo(gameToLatLng(...st.me), 5, { duration: 0.5 });
    setSheet("nearby");
  };
  const activeCount = st.families.length + (st.hideDone ? 1 : 0);
  const unplaced = visible.filter((p) => p.x == null).length;

  return (
    <div className="mapwrap">
      <div ref={el} className="mapcanvas" />

      <div className="map-top">
        <div className="searchbar">
          <span className="muted">⌕</span>
          <input placeholder="Chercher un lieu, une catégorie, une zone…" value={q} onChange={(e) => setQ(e.target.value)} />
          {q && <button className="iconbtn" onClick={() => setQ("")} aria-label="Effacer">✕</button>}
        </div>
        <div className="chiprow">
          {ALL_FAMILIES.map((f) => (
            <button key={f.id} className={`chip ${st.families.includes(f.id) ? "on" : ""}`} onClick={() => toggleFam(f.id)}>
              <b style={{ color: f.color }}>{f.icon}</b> {f.label}
            </button>
          ))}
        </div>
      </div>

      {(err || hint) && <div className="toast">{err || hint}</div>}

      <div className="fabs">
        <button className={`fab ${activeCount ? "on" : ""}`} onClick={() => setSheet("filters")} aria-label="Filtres">
          ☰{activeCount ? <i>{activeCount}</i> : null}</button>
        <button className={`fab ${st.me ? "on" : ""}`} onClick={aroundMe} aria-label="Autour de moi">◎</button>
      </div>

      {picked && !sheet && (
        <div className="pickcard">
          <div className="row" style={{ flexWrap: "nowrap" }}>
            <span className="dot" style={{ background: familyOf(picked.category, picked.id.startsWith("secret:")).color }} />
            <div style={{ minWidth: 0 }}>
              <div className="title ellipsis">{picked.name}</div>
              <div className="small muted ellipsis">{picked.category} · {picked.region}</div>
            </div>
          </div>
          <div className="row" style={{ marginTop: 10, flexWrap: "nowrap" }}>
            <button className={`btn ghost grow ${picked.status === "done" ? "on" : ""}`}
              onClick={() => mark(picked, picked.status === "done" ? "to_discover" : "done")}>{picked.status === "done" ? "✓ Fait" : "Marquer fait"}</button>
            <button className={`btn ghost ${picked.status === "favorite" ? "on" : ""}`} onClick={() => mark(picked, "favorite")} aria-label="Favori">☆</button>
            <Link className="btn grow" to={entityLink(picked.id)}>Fiche</Link>
          </div>
        </div>
      )}

      {sheet && <div className="scrim" onClick={() => setSheet(null)} />}
      {sheet === "filters" && (
        <div className="sheet">
          <div className="grabber" />
          <div className="row"><h2 style={{ margin: 0 }}>Filtres</h2><span className="spacer" />
            <button className="btn ghost" onClick={() => setSt((s) => ({ ...s, families: [], hideDone: false }))}>Tout afficher</button></div>
          <label className="switch"><input type="checkbox" checked={st.hideDone}
            onChange={(e) => setSt((s) => ({ ...s, hideDone: e.target.checked }))} /> Masquer ce que j'ai déjà fait</label>
          <div className="famgrid">
            {ALL_FAMILIES.map((f) => {
              const n = places.filter((p) => familyOf(p.category, p.id.startsWith("secret:")).id === f.id).length;
              return (
                <button key={f.id} className={`famtile ${st.families.includes(f.id) ? "on" : ""}`} onClick={() => toggleFam(f.id)}>
                  <span style={{ color: f.color, fontSize: 22 }}>{f.icon}</span>
                  <span>{f.label}</span><span className="muted small">{n}</span>
                </button>
              );
            })}
          </div>
          <p className="small muted">Rien de sélectionné = tout afficher · {visible.length} résultats
            {unplaced ? ` · ${unplaced} sans position précise (listés par zone dans « Autour de moi »)` : ""}.</p>
          <div className="sheet-footer"><button className="btn" style={{ width: "100%" }} onClick={() => setSheet(null)}>Voir {visible.length - unplaced} lieux sur la carte</button></div>
        </div>
      )}
      {sheet === "nearby" && (
        <div className="sheet">
          <div className="grabber" />
          <h2 style={{ margin: "0 0 8px" }}>Autour de moi</h2>
          <div style={{ display: "grid", gap: 2 }}>
            {nearby.map(({ p, d }) => (
              <Link key={p.id} to={entityLink(p.id)} className="listrow">
                <span className="dot" style={{ background: familyOf(p.category, p.id.startsWith("secret:")).color }} />
                <span className="grow ellipsis">{p.status === "done" ? "✓ " : ""}{p.name}<span className="small muted"> · {p.category}</span></span>
                <span className="small muted">{d < 0 ? "zone" : d < 1000 ? `${Math.round(d)} m` : `${(d / 1000).toFixed(1)} km`}</span>
              </Link>
            ))}
          </div>
          <p className="small muted">Appui long sur la carte pour changer votre position.</p>
        </div>
      )}
    </div>
  );
}
