/* eslint-disable @typescript-eslint/no-explicit-any */
/** Mode hors ligne : répond aux lectures depuis l'instantané embarqué (filtré au niveau
 *  anti-spoiler le plus strict) et garde les statuts personnels sur le téléphone. */
type Locked = { hints: string[]; solution: string[]; video: unknown; name: string | null };
type Story = { chapters: { num: number; title: string }[]; missions: { id: string; name: string; alias: string; kind: string; name_safe: boolean; chapter: number | null }[];
  characters: { id: string; name: string; chapter: number | null }[] };
type Snap = { locked?: Record<string, Locked>; story?: Story;
  vehicles: any[]; weapons: any[]; places: any[]; facets: unknown; details: Record<string, any>;
  prefs: Record<string, unknown>;
};
let snap: Promise<Snap> | null = null;
const load = () => (snap ??= fetch("data/snapshot.json").then((r) => r.json()));

const STATUS_KEY = "offline_status_v1";
const statuses = (): Record<string, string> => { try { return JSON.parse(localStorage.getItem(STATUS_KEY) ?? "{}"); } catch { return {}; } };
export function saveLocalStatus(id: string, status: string) {
  const s = statuses(); s[id] = status;
  try { localStorage.setItem(STATUS_KEY, JSON.stringify(s)); } catch { /* ignore */ }
}
const REVEAL_KEY = "offline_reveal_v1";
type Reveal = { hints?: number; solution?: boolean; name?: boolean };
const reveals = (): Record<string, Reveal> => { try { return JSON.parse(localStorage.getItem(REVEAL_KEY) ?? "{}"); } catch { return {}; } };
function setReveal(id: string, patch: Reveal) {
  const r = reveals(); r[id] = { ...r[id], ...patch };
  try { localStorage.setItem(REVEAL_KEY, JSON.stringify(r)); } catch { /* ignore */ }
}

/** Applique à une fiche ce que l'utilisateur a explicitement révélé (indices, solution, titre). */
function withReveals(d: any, lk: Locked | undefined) {
  if (!lk) return d;
  const r = reveals()[d.id] ?? {};
  const n = Math.min(r.hints ?? 0, lk.hints.length);
  const content = [...(d.content ?? []).filter((c: any) => c.level === 1),
    ...lk.hints.slice(0, n).map((body, ord) => ({ level: 2, ord, body })),
    ...(r.solution ? lk.solution.map((body, ord) => ({ level: 3, ord, body })) : [])];
  const claims = [...(d.claims ?? []), ...(r.solution && lk.video ? [{ field: "video", value_json: JSON.stringify(lk.video), value_kind: "community", source_id: "gta6map", source_url: null, status: "probable" }] : [])];
  return { ...d, content, claims, hints_remaining: lk.hints.length - n, has_solution: lk.solution.length > 0 || !!lk.video,
    ...(r.name && lk.name ? { name: lk.name, name_hidden: false } : {}) };
}

const PROG_KEY = "offline_progress_v1";
type Prog = { chapter: number; completed_missions: string[]; met_characters: string[]; discovered_regions: string[] };
const progress = (): Prog => { try { return { chapter: 0, completed_missions: [], met_characters: [], discovered_regions: [], ...JSON.parse(localStorage.getItem(PROG_KEY) ?? "{}") }; } catch { return { chapter: 0, completed_missions: [], met_characters: [], discovered_regions: [] }; } };
const saveProgress = (p: Prog) => { try { localStorage.setItem(PROG_KEY, JSON.stringify(p)); } catch { /* ignore */ } };

/** Options de progression filtrées par chapitre (même règle que la base sur le PC). */
function options(s: Snap) {
  const p = progress(), st = s.story ?? { chapters: [], missions: [], characters: [] };
  const rv = reveals();
  return {
    chapter: p.chapter, max_chapter: Math.max(5, ...st.chapters.map((c) => c.num)),
    chapters: st.chapters.map((c) => ({ num: c.num, title: c.num <= p.chapter ? c.title : null })),
    missions: st.missions.filter((m) => m.chapter == null || m.chapter <= p.chapter)
      .map((m) => ({ id: m.id, kind: m.kind, chapter: m.chapter, done: p.completed_missions.includes(m.id),
        name: m.name_safe || rv[m.id]?.name ? m.name : m.alias }))
      .sort((a, b) => (a.chapter ?? 99) - (b.chapter ?? 99)),
    characters: st.characters.filter((c) => c.chapter == null || c.chapter <= p.chapter)
      .map((c) => ({ id: c.id, name: c.name, met: p.met_characters.includes(c.id) })),
  };
}

const PREF_KEY = "offline_prefs_v1";
const prefs = (): Record<string, unknown> => { try { return JSON.parse(localStorage.getItem(PREF_KEY) ?? "{}"); } catch { return {}; } };
export function saveLocalPref(k: string, v: unknown) {
  const p = prefs(); p[k] = v;
  try { localStorage.setItem(PREF_KEY, JSON.stringify(p)); } catch { /* ignore */ }
}

const STATS_V = ["speed", "acceleration", "handling_road", "handling_offroad", "strength"];

function score(stats: Record<string, number | null>, w: Record<string, number>) {
  const known = Object.entries(w).filter(([k, x]) => x > 0 && typeof stats[k] === "number");
  if (!known.length) return null;
  const tw = known.reduce((a, [, x]) => a + x, 0);
  const all = Object.values(w).filter((x) => x > 0).reduce((a, x) => a + x, 0) || 1;
  return { value: +(known.reduce((a, [k, x]) => a + (stats[k] as number) * x, 0) / tw).toFixed(2), coverage: +(tw / all).toFixed(2) };
}

export async function offlineGet(path: string): Promise<unknown> {
  const s = await load();
  const [p, qs] = path.split("?");
  const q = new URLSearchParams(qs ?? "");
  const st = statuses();
  const withStatus = <T extends { id: string }>(x: T) => ({ ...x, status: st[x.id] ?? (x as any).status ?? null });

  if (p === "/api/health") return { ok: true, offline: true };
  if (p === "/api/progress") return progress();
  if (p === "/api/progress/options") return options(s);
  if (p === "/api/places/facets") return s.facets;
  if (p === "/api/places") return s.places.map(withStatus);
  if (p.startsWith("/api/prefs/")) { const k = p.slice(11); return prefs()[k] ?? s.prefs[k] ?? null; }
  if (p === "/api/garage") {
    return Object.entries(st).filter(([, v]) => ["owned", "wanted", "favorite", "lost"].includes(v))
      .map(([id, status]) => ({ id, name: s.details[id]?.name ?? id, status })).filter((x) => s.details[x.id]);
  }
  if (p === "/api/search") {
    const n = (q.get("q") ?? "").toLowerCase();
    return Object.values(s.details).filter((d: any) => d?.name?.toLowerCase().includes(n)).slice(0, 30)
      .map((d: any) => ({ entity_id: d.id, display_name: d.name, field: "name", snip: d.category ?? d.kind }));
  }
  const detail = p.match(/^\/api\/(?:vehicles|entity)\/(.+)$/);
  if (detail) {
    const d = s.details[decodeURIComponent(detail[1])];
    if (!d) throw new Error("Introuvable ou masqué (anti-spoiler)");
    return withReveals({ ...d, status: st[d.id] ?? d.status ?? null }, s.locked?.[d.id]);
  }
  if (p === "/api/vehicles") {
    const w = q.get("use_profile") ? ((prefs().vehicle_weights ?? s.prefs.vehicle_weights) as Record<string, number>) : null;
    const excl = q.getAll("exclude_class").length ? q.getAll("exclude_class")
      : q.get("use_profile") ? ((prefs().vehicle_exclude_classes ?? s.prefs.vehicle_exclude_classes) as string[]) : [];
    let list = s.vehicles.filter((v: any) => {
      if (q.get("q") && !v.name.toLowerCase().includes(q.get("q")!.toLowerCase())) return false;
      for (const k of STATS_V) { const m = q.get(`min_${k}`); if (m && !(v.stats[k] >= +m)) return false; }
      if (q.get("max_price") && !(v.price != null && v.price <= +q.get("max_price")!)) return false;
      if (q.get("seats_min") && !((v.seats ?? 0) >= +q.get("seats_min")!)) return false;
      if (q.getAll("drivetrain").length && !q.getAll("drivetrain").includes(v.drivetrain)) return false;
      if (q.getAll("vclass").length && !q.getAll("vclass").includes(v.class)) return false;
      if (excl.includes(v.class)) return false;
      if (q.getAll("variant_type").length && !q.getAll("variant_type").includes(v.variant_type)) return false;
      return true;
    });
    if (w) list = list.map((v: any) => ({ ...v, score: score(v.stats, w) }))
      .sort((a: any, b: any) => (b.score?.value ?? -1) - (a.score?.value ?? -1));
    return list;
  }
  if (p === "/api/weapons") {
    const w = q.get("ranked") ? { damage: 0.4, accuracy: 0.25, range: 0.2, weapon_handling: 0.15 } : null;
    let list = s.weapons.filter((x: any) => {
      if (q.get("q") && !x.name.toLowerCase().includes(q.get("q")!.toLowerCase())) return false;
      if (q.get("wclass") && x.class !== q.get("wclass")) return false;
      if (q.get("free_only") && !x.free_hint) return false;
      for (const [param, k] of [["min_damage", "damage"], ["min_accuracy", "accuracy"], ["min_range", "range"], ["min_handling", "weapon_handling"]]) {
        const m = q.get(param); if (m && !(x.stats[k] >= +m)) return false;
      }
      if (q.get("max_price") && x.price != null && x.price > +q.get("max_price")!) return false;
      return true;
    });
    if (w) list = list.map((x: any) => ({ ...x, score: score(x.stats, w) })).sort((a: any, b: any) => (b.score?.value ?? -1) - (a.score?.value ?? -1));
    return list;
  }
  throw new Error("Indisponible hors ligne");
}

export async function offlineWrite(path: string, body: unknown): Promise<unknown> {
  if (path === "/api/progress") { saveProgress({ ...progress(), ...(body as Prog) }); return progress(); }
  const pm = path.match(/^\/api\/progress\/(mission|character)\/(.+)$/);
  if (pm) {
    const id = decodeURIComponent(pm[2]), on = (body as { value: boolean }).value, pr = progress();
    const key = pm[1] === "mission" ? "completed_missions" : "met_characters";
    pr[key] = on ? [...new Set([...pr[key], id])] : pr[key].filter((x) => x !== id);
    saveProgress(pr);
    return options(await load());
  }
  const rv = path.match(/^\/api\/entity\/(.+)\/(hint|solution|reveal-name)/);
  if (rv) {
    const id = decodeURIComponent(rv[1]);
    const cur = reveals()[id] ?? {};
    if (rv[2] === "hint") setReveal(id, { hints: (cur.hints ?? 0) + 1 });
    if (rv[2] === "solution") setReveal(id, { solution: true });
    if (rv[2] === "reveal-name") setReveal(id, { name: true });
    return offlineGet(`/api/entity/${rv[1]}`);
  }
  const status = path.match(/^\/api\/status\/(.+)$/);
  if (status) { const id = decodeURIComponent(status[1]); saveLocalStatus(id, (body as any).status); return { id, status: (body as any).status }; }
  const pref = path.match(/^\/api\/prefs\/(.+)$/);
  if (pref) { saveLocalPref(pref[1], body); return body; }
  throw new Error("Action disponible uniquement connecté au PC");
}
