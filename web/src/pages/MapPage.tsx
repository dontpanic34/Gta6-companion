import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Check, ChevronUp, Crosshair as Target, ExternalLink, Eye, Lightbulb, LocateFixed, MapPinned, Play, Search, SlidersHorizontal, X } from "lucide-react";
import { api, EntityFull, entityLink, getBaseUrl, Place, RELIABILITY_FR } from "../api";
import { ALL_FAMILIES, categoryImage, categoryStyle, Family, familyOf, iconInner, markerHtml } from "../map/categories";
import { onBack } from "../back";
import { createTileLayer, distance, gameToLatLng, latLngToGame, LEONIDA_BOUNDS, TILE_BOUNDS } from "../map/leonida";

const STORE = "map_state_v2";
interface MapState { families: string[]; hideDone: boolean; me: [number, number] | null; zone: string | null }
const load = (): MapState => {
  try { return { families: [], hideDone: false, me: null, zone: null, ...JSON.parse(localStorage.getItem(STORE) ?? "{}") }; }
  catch { return { families: [], hideDone: false, me: null, zone: null }; }
};
const norm = (t: string) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const isSecret = (p: { id: string }) => p.id.startsWith("secret:");
const PRECISION_FR: Record<string, string> = { exact: "Emplacement exact", nearby: "Secteur", zone: "Zone seulement" };

export function FamIcon({ f, size = 16, color }: { f: Family | { icon: Family["icon"]; color: string }; size?: number; color?: string }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color ?? f.color} strokeWidth={2.2}
    strokeLinecap="round" strokeLinejoin="round" dangerouslySetInnerHTML={{ __html: iconInner(f.icon) }} />;
}

const iconCache = new Map<string, L.DivIcon>();
function markerIcon(p: Place, size: number, withLabel: boolean, selected: boolean) {
  const done = p.status === "done" || p.status === "discovered";
  const key = withLabel || selected ? "" : `${p.category}|${isSecret(p)}|${size}|${done}`;
  if (key && iconCache.has(key)) return iconCache.get(key)!;
  const st = categoryStyle(p.category, isSecret(p));
  const px = categoryImage(p.category) ? Math.round(size * 1.35) : size;   // icônes illustrées un peu plus grandes
  const icon = L.divIcon({
    html: markerHtml(st, selected ? size + 8 : size, done, withLabel ? p.name : undefined, p.category),
    className: `mkwrap${selected ? " sel" : ""}`, iconSize: [px, px], iconAnchor: [px / 2, px / 2],
  });
  if (key) iconCache.set(key, icon);
  return icon;
}

export default function MapPage() {
  const nav = useNavigate();
  const [sp] = useSearchParams();
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const layer = useRef<L.LayerGroup | null>(null);
  const over = useRef<L.LayerGroup | null>(null);
  const zoneLayer = useRef<L.LayerGroup | null>(null);
  const [zoneNames, setZoneNames] = useState<{ name: string; x: number; y: number; tier: number }[]>([]);
  const [places, setPlaces] = useState<Place[]>([]);
  const [st, setSt] = useState<MapState>(load);
  const [q, setQ] = useState("");
  const [searching, setSearching] = useState(false);
  const [picked, setPicked] = useState<Place | null>(null);
  const [detail, setDetail] = useState<EntityFull | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [confirm, setConfirm] = useState<"solution" | "name" | null>(null);
  const [filters, setFilters] = useState(false);
  const [nearbyOpen, setNearbyOpen] = useState(false);
  const [view, setView] = useState<{ z: number; b: L.LatLngBounds | null }>({ z: 2, b: null });
  const [toast, setToast] = useState("");

  // bouton retour Android : ferme la fiche / le panneau ouvert avant de quitter la carte
  useEffect(() => onBack(() => {
    if (filters) { setFilters(false); return true; }
    if (nearbyOpen) { setNearbyOpen(false); return true; }
    if (picked) { setPicked(null); return true; }
    if (searching) { setSearching(false); return true; }
    return false;
  }), [filters, nearbyOpen, picked, searching]);
  const flash = (t: string) => { setToast(t); setTimeout(() => setToast(""), 2200); };
  useEffect(() => { try { localStorage.setItem(STORE, JSON.stringify(st)); } catch { /* ignore */ } }, [st]);
  useEffect(() => { api.places(new URLSearchParams()).then(setPlaces).catch((e) => flash(e.message)); }, []);
  useEffect(() => { api.zones().then(setZoneNames).catch(() => {}); }, []);

  // --- carte
  useEffect(() => {
    if (!el.current || map.current) return;
    const m = L.map(el.current, {
      crs: L.CRS.Simple, zoomControl: false, minZoom: 0, maxZoom: 7, attributionControl: true,
      // bornes larges : on peut dézoomer jusqu'à voir toute la carte sans retour forcé
      maxBounds: TILE_BOUNDS.pad(1.2), maxBoundsViscosity: 0.3, zoomSnap: 0.25, preferCanvas: true,
    });
    createTileLayer(getBaseUrl()).addTo(m);
    const fx = sp.get("x"), fy = sp.get("y");
    if (fx && fy) m.setView(gameToLatLng(+fx, +fy), +(sp.get("z") ?? 5)); else m.fitBounds(LEONIDA_BOUNDS);
    // noms de zones : sous les icônes, jamais cliquables
    m.createPane("zones"); const zp = m.getPane("zones")!; zp.style.zIndex = "450"; zp.style.pointerEvents = "none";
    zoneLayer.current = L.layerGroup([], { pane: "zones" }).addTo(m);
    layer.current = L.layerGroup().addTo(m);
    over.current = L.layerGroup().addTo(m);
    const sync = () => setView({ z: m.getZoom(), b: m.getBounds().pad(0.25) });
    m.on("moveend zoomend", sync); sync();
    m.on("contextmenu", (e: L.LeafletMouseEvent) => { setSt((s) => ({ ...s, me: latLngToGame(e.latlng) })); flash("Position enregistrée"); });
    m.on("click", () => { setPicked(null); setSearching(false); });
    map.current = m;
    return () => { m.remove(); map.current = null; };
  }, []);

  // recherche : seuls les lieux correspondants restent sur la carte (texte normalisé, sans accents)
  const [query, setQuery] = useState("");
  useEffect(() => { const t = setTimeout(() => setQuery(norm(q.trim())), 250); return () => clearTimeout(t); }, [q]);
  const matches = (p: Place) => query.length < 2 || norm(`${p.name} ${p.category ?? ""} ${p.region ?? ""}`).includes(query);

  const filtered = useMemo(() => places.filter((p) => {
    if (p.x == null) return false;
    if (st.zone && p.region !== st.zone) return false;
    const fam = familyOf(p.category, isSecret(p));
    if (fam.hidden && !st.families.includes(fam.id)) return false;          // masqué par défaut
    if (st.families.filter((f) => f !== "extras").length && !st.families.includes(fam.id)) return false;
    if (st.hideDone && (p.status === "done" || p.status === "discovered")) return false;
    return matches(p);
  }), [places, st.families, st.hideDone, st.zone, query]);

  const results = useMemo(() => query.length < 2 ? [] : filtered.slice(0, 40), [filtered, query]);

  const zones = useMemo(() => {
    const n: Record<string, number> = {};
    places.forEach((p) => { if (p.x != null && p.region) n[p.region] = (n[p.region] ?? 0) + 1; });
    return Object.entries(n).sort((a, b) => b[1] - a[1]);
  }, [places]);

  // cadrage automatique sur la zone choisie ou sur les résultats de recherche
  useEffect(() => {
    const m = map.current;
    if (!m || (!st.zone && query.length < 2) || !filtered.length) return;
    const b = L.latLngBounds(filtered.map((p) => gameToLatLng(p.x!, p.y!) as L.LatLngTuple));
    m.flyToBounds(b.pad(0.2), { maxZoom: 5, duration: 0.6, paddingBottomRight: [0, 160] });
  }, [st.zone, query, filtered.length]);

  // --- marqueurs (seulement ceux à l'écran, libellés à fort zoom)
  const inView = useMemo(() => view.b ? filtered.filter((p) => view.b!.contains(gameToLatLng(p.x!, p.y!))) : [], [filtered, view]);
  useEffect(() => {
    const g = layer.current; if (!g) return;
    g.clearLayers();
    const z = view.z, m = map.current;
    // Libellés sans chevauchement : on place d'abord les lieux exacts, puis les autres s'il reste de la place
    const labeled = new Set<string>();
    if (z >= 4.5 && m) {
      const boxes: [number, number, number, number][] = [];
      const order = [...inView].sort((a, b) => (a.precision === "exact" ? 0 : 1) - (b.precision === "exact" ? 0 : 1));
      for (const p of order) {
        const pt = m.latLngToContainerPoint(gameToLatLng(p.x!, p.y!));
        const w = Math.min(p.name.length * 6.6, 190), box: [number, number, number, number] = [pt.x - w / 2 - 14, pt.y - 14, pt.x + w / 2 + 14, pt.y + 34];
        if (!boxes.some((o) => box[0] < o[2] && box[2] > o[0] && box[1] < o[3] && box[3] > o[1])) { boxes.push(box); labeled.add(p.id); }
      }
    }
    inView.forEach((p) => {
      const ll = gameToLatLng(p.x!, p.y!);
      const click = (e: L.LeafletEvent) => { L.DomEvent.stopPropagation(e as L.LeafletMouseEvent); pick(p); };
      if (z >= 3) {
        L.marker(ll, { icon: markerIcon(p, z >= 5 ? 34 : z >= 4 ? 30 : 24, labeled.has(p.id), picked?.id === p.id), keyboard: false,
          zIndexOffset: picked?.id === p.id ? 1000 : 0 }).on("click", click).addTo(g);
      } else {
        L.circleMarker(ll, { radius: 3.5, weight: 0.8, color: "#0d0b14", fillColor: categoryStyle(p.category, isSecret(p)).color, fillOpacity: 0.95 })
          .on("click", click).addTo(g);
      }
    });
  }, [inView, view.z, picked?.id]);

  // --- noms de zones, comme en jeu : grands noms dézoomé, quartiers en zoomant
  useEffect(() => {
    const g = zoneLayer.current; if (!g) return;
    g.clearLayers();
    const z = view.z;
    const tiers = z < 2.6 ? [1] : z < 3.8 ? [1, 2] : z < 4.8 ? [2, 3] : [3];
    zoneNames.filter((n) => tiers.includes(n.tier) && (!view.b || view.b.contains(gameToLatLng(n.x, n.y)))).forEach((n) => {
      L.marker(gameToLatLng(n.x, n.y), {
        pane: "zones", interactive: false, keyboard: false,
        icon: L.divIcon({ className: "zone-wrap", html: `<span class="zone-lbl t${n.tier}">${n.name}</span>`, iconSize: [0, 0] }),
      }).addTo(g);
    });
  }, [zoneNames, view]);

  // --- surcouche : ma position + cercle de zone du lieu sélectionné
  useEffect(() => {
    const g = over.current; if (!g) return;
    g.clearLayers();
    if (st.me) L.circleMarker(gameToLatLng(...st.me), { radius: 9, color: "#fff", weight: 3, fillColor: "#ff4f8b", fillOpacity: 1, interactive: false }).addTo(g);
    if (picked?.x != null && picked.precision && picked.precision !== "exact")
      L.circle(gameToLatLng(picked.x, picked.y!), { radius: (picked.precision === "zone" ? 450 : 250) / 32, color: "#fff", weight: 2,
        dashArray: "6 6", fillOpacity: 0.05, interactive: false }).addTo(g);
  }, [st.me, picked]);

  // --- sélection
  function pick(p: Place, fly = false) {
    setPicked(p); setDetail(null); setExpanded(false); setConfirm(null); setSearching(false);
    if (fly && p.x != null) map.current?.flyTo(gameToLatLng(p.x, p.y!), Math.max(map.current.getZoom(), 5), { duration: 0.5 });
    api.entity(p.id).then((e) => {
      setDetail(e);
      if (e.linked) setPlaces((all) => all.map((x) => (x.id === p.id ? { ...x, linked_id: e.linked!.id, image: e.linked!.image, linked_stats: e.linked!.stats } : x)));
    }).catch(() => {});
  }
  const mark = (p: Place) => {
    const status = p.status === "done" ? "to_discover" : "done";
    api.setStatus(p.id, status).then(() => {
      setPlaces((all) => all.map((x) => (x.id === p.id ? { ...x, status } : x)));
      setPicked((x) => (x && x.id === p.id ? { ...x, status } : x));
      flash(status === "done" ? "Marqué comme trouvé" : "Remis à faire");
    });
  };
  const reveal = (kind: "hint" | "solution" | "name") => {
    if (!detail) return;
    const call = kind === "hint" ? api.hint : kind === "solution" ? api.solution : api.revealName;
    call(detail.id).then((e) => { setDetail({ ...detail, ...e }); setConfirm(null); setExpanded(true); })
      .catch((e) => flash(e.message));
  };

  const famCount = useMemo(() => {
    const n: Record<string, number> = {};
    places.forEach((p) => { if (p.x != null) { const k = familyOf(p.category, isSecret(p)).id; n[k] = (n[k] ?? 0) + 1; } });
    return n;
  }, [places]);
  const toggleFam = (id: string) => setSt((s) => ({ ...s, families: s.families.includes(id) ? s.families.filter((x) => x !== id) : [...s.families, id] }));
  const nearby = useMemo(() => !st.me ? [] : filtered.map((p) => ({ p, d: distance(st.me!, [p.x!, p.y!]) })).sort((a, b) => a.d - b.d).slice(0, 40), [st.me, filtered]);
  const activeCount = st.families.length + (st.hideDone ? 1 : 0) + (st.zone ? 1 : 0);

  // --- contenu de la fiche
  const d = detail;
  const level = (n: number) => (d?.content ?? []).filter((c) => c.level === n);
  const claim = (f: string) => { const c = d?.claims.find((x) => x.field === f); return c ? JSON.parse(c.value_json) : null; };
  const video = claim("video") as { provider: string; id: string; start: number } | null;
  const videoUrl = video ? (video.provider === "yt" ? `https://www.youtube.com/watch?v=${video.id}&t=${video.start}s` : `https://www.tiktok.com/video/${video.id}`) : null;
  const hero = video?.provider === "yt" ? `https://img.youtube.com/vi/${video.id}/hqdefault.jpg` : (picked?.image ?? d?.linked?.image ?? d?.media?.[0]);
  const pst = picked ? categoryStyle(picked.category, isSecret(picked)) : null;

  return (
    <div className="mapwrap">
      <div ref={el} className="mapcanvas" />

      <div className="counter"><i />{inView.length} <span>sur la carte</span><b>·</b>{filtered.length} <span>au total</span></div>
      {toast && <div className="toast">{toast}</div>}

      {!picked && (
        <div className="fabs">
          <button className={`fab ${st.me ? "on" : ""}`} aria-label="Autour de moi"
            onClick={() => st.me ? (map.current?.flyTo(gameToLatLng(...st.me), 5, { duration: 0.5 }), setNearbyOpen(true)) : flash("Appui long sur la carte : « je suis ici »")}>
            <LocateFixed size={22} /></button>
        </div>
      )}

      {/* --- barre basse : familles + recherche (à portée de pouce) */}
      {!picked && (
        <div className="map-bottom">
          {searching && query.length >= 2 && (
            <div className="results">
              <button className="listrow results-head" onClick={() => setSearching(false)}>
                <span className="grow" style={{ textAlign: "left" }}><b>{filtered.length}</b> résultat{filtered.length > 1 ? "s" : ""}{st.zone ? ` à ${st.zone}` : ""}</span>
                <span className="small" style={{ color: "var(--accent)" }}>Voir sur la carte</span>
              </button>
              {results.length === 0 && <div className="small muted" style={{ padding: 12 }}>Aucun lieu ne correspond.</div>}
              {results.map((p) => { const s = categoryStyle(p.category, isSecret(p)); return (
                <button key={p.id} className="listrow" onClick={() => pick(p, true)}>
                  <span className="famicon" style={{ background: s.color }}><FamIcon f={s} size={16} color="#0d0b14" /></span>
                  <span className="grow ellipsis">{p.name}<span className="small muted"> · {p.category}</span></span>
                </button>); })}
            </div>
          )}
          {!searching && (
            <div className="chiprow">
              {query.length >= 2 && <button className="chip on" onClick={() => setQ("")}><Search size={14} /> « {q.trim()} » <X size={14} /></button>}
              {st.zone
                ? <button className="chip on" onClick={() => setSt((s) => ({ ...s, zone: null }))}><MapPinned size={14} /> {st.zone} <X size={14} /></button>
                : <button className="chip" onClick={() => setFilters(true)}><MapPinned size={14} /> Zone</button>}
              {ALL_FAMILIES.filter((f) => famCount[f.id] && !f.hidden).map((f) => (
                <button key={f.id} className={`chip ${st.families.includes(f.id) ? "on" : ""}`} onClick={() => toggleFam(f.id)}>
                  <FamIcon f={f} /> {f.label}
                </button>
              ))}
            </div>
          )}
          <div className="row" style={{ flexWrap: "nowrap", gap: 8 }}>
            <div className="searchbar grow">
              <Search size={18} className="muted" />
              <input placeholder="Chercher des lieux et des secrets" value={q} onFocus={() => setSearching(true)}
                onChange={(e) => { setQ(e.target.value); setSearching(true); }} />
              {(q || searching) && <button className="iconbtn" onClick={() => { setQ(""); setSearching(false); }} aria-label="Fermer"><X size={18} /></button>}
            </div>
            <button className={`sqbtn ${activeCount ? "on" : ""}`} onClick={() => setFilters(true)} aria-label="Filtres">
              <SlidersHorizontal size={22} />{activeCount ? <i>{activeCount}</i> : null}</button>
          </div>
        </div>
      )}

      {/* --- fiche du lieu, sur la carte */}
      {picked && pst && (
        <div className={`placesheet ${expanded ? "full" : ""}`}>
          <button className="grabber-btn" onClick={() => setExpanded(!expanded)} aria-label="Agrandir"><span className="grabber" /></button>
          <div className="ps-scroll">
            {hero && (
              <a className="ps-hero" href={videoUrl ?? undefined} target="_blank" rel="noreferrer" onClick={(e) => { if (!videoUrl) e.preventDefault(); }}>
                <img src={hero} alt="" referrerPolicy="no-referrer" onError={(e) => ((e.currentTarget.parentElement as HTMLElement).style.display = "none")} />
                {videoUrl && <span className="play"><Play size={26} fill="#0d0b14" /></span>}
              </a>
            )}
            <div className="ps-head">
              {categoryImage(picked.category)
                ? <img src={categoryImage(picked.category)!} width={48} height={48} alt="" />
                : <span className="famicon big" style={{ background: pst.color }}><FamIcon f={pst} size={22} color="#0d0b14" /></span>}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="ps-title">{d?.name ?? picked.name}</div>
                <div className="row small" style={{ marginTop: 6 }}>
                  <span className="tag">{picked.category}</span>
                  {d && <span className="tag">{RELIABILITY_FR[d.reliability] ?? d.reliability}</span>}
                  {picked.precision && <span className="tag">{PRECISION_FR[picked.precision] ?? picked.precision}</span>}
                  {picked.region && <span className="tag">{picked.region}</span>}
                </div>
              </div>
              <button className="iconbtn" onClick={() => setPicked(null)} aria-label="Fermer"><X size={20} /></button>
            </div>
            {d?.name_hidden && (
              confirm === "name"
                ? <button className="btn ghost wide" onClick={() => reveal("name")}><Eye size={16} /> Confirmer : afficher le vrai titre</button>
                : <button className="linkbtn" onClick={() => setConfirm("name")}>Titre masqué (anti-spoiler) · révéler</button>
            )}
            {picked.linked_stats && <div className="ministats big">{Object.entries({ speed: "Vitesse", acceleration: "Accél.", handling_road: "Route", handling_offroad: "Tout-terrain" })
              .filter(([k]) => picked.linked_stats![k] != null).map(([k, l]) => <span key={k}><b>{picked.linked_stats![k]}</b>{l}</span>)}</div>}

            <section><h4>Emplacement</h4>
              {level(1).filter((c) => c.ord === 0).map((c, i) => <p key={i}>{c.body}</p>)}
              {!level(1).some((c) => c.ord === 0) && <p>{claim("description") ?? (d ? "Pas de détail vérifié." : "Chargement…")}</p>}
              {claim("subarea") && <p className="small muted">Secteur : {claim("subarea")}</p>}
            </section>
            {level(1).filter((c) => c.ord > 0).length > 0 && (
              <section><h4>Il te faut</h4>{level(1).filter((c) => c.ord > 0).map((c, i) => <p key={i}>{c.body}</p>)}</section>
            )}
            {d && (level(2).length > 0 || d.hints_remaining > 0) && (
              <section><h4>De quoi s'agit-il</h4>
                {level(2).map((c, i) => <p key={i}>{c.body}</p>)}
                {d.hints_remaining > 0 && <button className="btn ghost wide" onClick={() => reveal("hint")}><Lightbulb size={16} /> Afficher l'indice</button>}
              </section>
            )}
            {d && (level(3).length > 0 || d.has_solution) && (
              <section><h4>Comment y aller</h4>
                {level(3).map((c, i) => <p key={i}>{c.body}</p>)}
                {!level(3).length && (confirm === "solution"
                  ? <button className="btn wide" onClick={() => reveal("solution")}><Eye size={16} /> Confirmer : révéler toute la solution</button>
                  : <button className="btn ghost wide" onClick={() => setConfirm("solution")}><Eye size={16} /> Afficher la solution</button>)}
                {videoUrl && level(3).length > 0 && <a className="btn ghost wide" href={videoUrl} target="_blank" rel="noreferrer"><Play size={16} /> Voir la vidéo</a>}
              </section>
            )}
            {d?.missable_warning && <p className="notice">Peut devenir définitivement inaccessible.</p>}
          </div>
          <div className="ps-actions">
            <button className={`act ${picked.status === "done" ? "on" : ""}`} onClick={() => mark(picked)}><Check size={20} />{picked.status === "done" ? "Trouvé" : "Marquer trouvé"}</button>
            <button className="act" onClick={() => picked.x != null && map.current?.flyTo(gameToLatLng(picked.x, picked.y!), 6, { duration: 0.5 })}><Target size={20} />Centrer</button>
            <button className="act" onClick={() => nav(entityLink(picked.linked_id ?? picked.id))}><ExternalLink size={20} />{picked.linked_id ? "Fiche véhicule" : "Fiche"}</button>
          </div>
        </div>
      )}

      {(filters || nearbyOpen) && <div className="scrim" onClick={() => { setFilters(false); setNearbyOpen(false); }} />}
      {filters && (
        <div className="sheet">
          <div className="grabber" />
          <div className="row"><h2 style={{ margin: 0 }}>Filtres</h2><span className="spacer" />
            <button className="btn ghost small" onClick={() => { setSt((s) => ({ ...s, families: [], hideDone: false, zone: null })); setQ(""); }}>Tout afficher</button></div>
          <label className="switch"><input type="checkbox" checked={st.hideDone} onChange={(e) => setSt((s) => ({ ...s, hideDone: e.target.checked }))} /> Masquer ce que j'ai déjà trouvé</label>
          <h4 className="sheet-h">Zone</h4>
          <div className="row">
            <button className={`chip ${!st.zone ? "on" : ""}`} onClick={() => setSt((s) => ({ ...s, zone: null }))}>Toute Leonida</button>
            {zones.map(([z, n]) => (
              <button key={z} className={`chip ${st.zone === z ? "on" : ""}`} onClick={() => setSt((s) => ({ ...s, zone: s.zone === z ? null : z }))}>{z} <span className="muted small">{n}</span></button>
            ))}
          </div>
          <h4 className="sheet-h">Catégories</h4>
          <div className="famgrid">
            {ALL_FAMILIES.filter((f) => famCount[f.id]).map((f) => (
              <button key={f.id} className={`famtile ${st.families.includes(f.id) ? "on" : ""}`} onClick={() => toggleFam(f.id)}>
                <span className="famicon" style={{ background: f.color }}><FamIcon f={f} size={18} color="#0d0b14" /></span>
                <span>{f.label}{f.hidden && <span className="small muted" style={{ display: "block" }}>masqué par défaut</span>}</span><span className="muted small">{famCount[f.id]}</span>
              </button>
            ))}
          </div>
          <div className="sheet-footer"><button className="btn wide" onClick={() => setFilters(false)}>Voir {filtered.length} lieux</button></div>
        </div>
      )}
      {nearbyOpen && (
        <div className="sheet">
          <div className="grabber" />
          <div className="row"><h2 style={{ margin: 0 }}>Autour de moi</h2><span className="spacer" /><ChevronUp size={18} className="muted" /></div>
          {nearby.map(({ p, d: dist }) => { const s = categoryStyle(p.category, isSecret(p)); return (
            <button key={p.id} className="listrow" onClick={() => { setNearbyOpen(false); pick(p, true); }}>
              <span className="famicon" style={{ background: s.color }}><FamIcon f={s} size={16} color="#0d0b14" /></span>
              <span className="grow ellipsis">{p.status === "done" ? "✓ " : ""}{p.name}<span className="small muted"> · {p.category}</span></span>
              <span className="small muted">{dist < 1000 ? `${Math.round(dist)} m` : `${(dist / 1000).toFixed(1)} km`}</span>
            </button>); })}
        </div>
      )}
    </div>
  );
}
