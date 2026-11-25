import { offlineGet, offlineWrite } from "./offline";
export type Stats = Record<"speed" | "acceleration" | "handling_road" | "handling_offroad" | "strength", number | null>;

export interface VehicleSummary {
  id: string; name: string; model_id: string; variant_type: string;
  manufacturer: string | null; class: string | null; image: string | null;
  stats: Stats; price: number | null; seats: number | null; drivetrain: string | null;
  score: { value: number; coverage: number } | null;
}

export interface WeaponSummary {
  id: string; name: string; model_id: string; variant_type: string; class: string | null; image: string | null;
  stats: Record<string, number | null>; price: number | null; capacity: number | null; moddable: string | null;
  free_hint: boolean; score: { value: number; coverage: number } | null;
}

export const WEAPON_STAT_LABELS: Record<string, string> = {
  damage: "Dégâts", accuracy: "Précision", weapon_handling: "Maniabilité", range: "Portée",
};

export interface ChatCard { type: string; id: string; name: string; subtitle?: string; image?: string | null }
export interface ChatAction { type: string; x?: number; y?: number; zoom?: number; params?: [string, string][]; ids?: string[] }
export interface ChatReply { text: string; cards: ChatCard[]; actions: ChatAction[]; engine?: string }

export interface XboxSummary { total: number; unlocked_count: number; locked_count: number; unlocked: { name: string; description: string; unlocked_at: string }[] }

export interface FieldValue {
  value: unknown; kind: "official" | "community" | "subjective"; contradiction: boolean;
  sources: { source: string; url: string | null; value: unknown; status: string; observed_at: string }[];
}

export interface VehicleDetail {
  id: string; name: string; kind: string; variant_type?: string; missable_warning: boolean;
  fields: Record<string, FieldValue>; media: string[];
  siblings?: { id: string; name: string; variant_type: string; image?: string | null }[];
  kits?: { id: string; name: string }[]; mods?: { id: string; name: string; category: string }[];
  hidden_fields: number;
}

export interface Place {
  id: string; kind: string; name: string; category: string | null; region: string | null;
  reliability: string; x: number | null; y: number | null; precision: string | null; status: string | null;
  linked_id?: string; image?: string | null; linked_stats?: Record<string, number | null>;
}

export interface EntityFull {
  id: string; kind: string; name: string; name_hidden: boolean; category: string | null; region: string | null;
  reliability: string; missable_warning: boolean; hints_remaining: number; media: string[];
  claims: { field: string; value_json: string; value_kind: string; source_id: string; source_url: string | null; status: string }[];
  content: { level: number; ord: number; body: string }[];
  has_solution?: boolean; status?: string | null;
  linked?: { id: string; image: string | null; stats: Record<string, number | null> };
  location?: { x: number; y: number; precision: string } | null;
}

export interface Progress {
  chapter: number; completed_missions: string[]; met_characters: string[]; discovered_regions: string[];
}

const TOKEN_KEY = "companion_token";
const BASE_KEY = "companion_base_url";
/** Adresse du PC (ex. http://100.64.0.5:8765). Vide = même origine (navigateur sur le PC). */
export const getBaseUrl = () => { try { return localStorage.getItem(BASE_KEY) ?? ""; } catch { return ""; } };
export const setBaseUrl = (u: string) => { try { localStorage.setItem(BASE_KEY, u.replace(/\/+$/, "")); } catch { /* ignore */ } };
export const getToken = () => { try { return localStorage.getItem(TOKEN_KEY) ?? ""; } catch { return ""; } };
export const setToken = (t: string) => { try { localStorage.setItem(TOKEN_KEY, t); } catch { /* ignore */ } };

const isNative = () => !!(window as any).Capacitor?.isNativePlatform?.();

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const base = getBaseUrl();
  // APK sans PC configuré : directement hors ligne
  if (isNative() && !base) {
    return (method === "GET" ? offlineGet(path) : offlineWrite(path, init.body ? JSON.parse(String(init.body)) : null)) as Promise<T>;
  }
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const t = getToken();
  if (t) headers.Authorization = `Bearer ${t}`;
  let r: Response;
  try {
    r = await fetch(base + path, { ...init, headers: { ...headers, ...(init.headers as object) }, signal: AbortSignal.timeout(6000) });
  } catch {
    // PC injoignable : on bascule sur l'instantané embarqué
    return (method === "GET" ? offlineGet(path) : offlineWrite(path, init.body ? JSON.parse(String(init.body)) : null)) as Promise<T>;
  }
  if (!r.ok) throw new Error(r.status === 401 ? "Jeton requis (Réglages)" : r.status === 404 ? "Introuvable ou masqué (anti-spoiler)" : `Erreur ${r.status}`);
  return r.json();
}

export const api = {
  vehicles: (params: URLSearchParams) => req<VehicleSummary[]>(`/api/vehicles?${params}`),
  vehicle: (id: string) => req<VehicleDetail>(`/api/vehicles/${encodeURIComponent(id)}`),
  search: (q: string) => req<{ entity_id: string; display_name: string; field: string; snip: string }[]>(`/api/search?q=${encodeURIComponent(q)}`),
  progress: () => req<Progress>("/api/progress"),
  setProgress: (p: Progress) => req<Progress>("/api/progress", { method: "PUT", body: JSON.stringify(p) }),
  pref: <T,>(k: string) => req<T>(`/api/prefs/${k}`),
  setPref: (k: string, v: unknown) => req(`/api/prefs/${k}`, { method: "PUT", body: JSON.stringify(v) }),
  places: (params: URLSearchParams) => req<Place[]>(`/api/places?${params}`),
  facets: () => req<{ regions: { name: string; n: number }[]; categories: { name: string; n: number; secret: number }[] }>("/api/places/facets"),
  entity: (id: string) => req<EntityFull>(`/api/entity/${encodeURIComponent(id)}`),
  hint: (id: string) => req<EntityFull>(`/api/entity/${encodeURIComponent(id)}/hint`, { method: "POST" }),
  revealName: (id: string) => req<EntityFull>(`/api/entity/${encodeURIComponent(id)}/reveal-name?confirm=true`, { method: "POST" }),
  solution: (id: string) => req<EntityFull>(`/api/entity/${encodeURIComponent(id)}/solution?confirm=true`, { method: "POST" }),
  weapons: (params: URLSearchParams) => req<WeaponSummary[]>(`/api/weapons?${params}`),
  chat: (message: string, history: { role: string; content: string }[]) =>
    req<ChatReply>("/api/assistant", { method: "POST", body: JSON.stringify({ message, history, session: "phone" }) }),
  xbox: () => req<XboxSummary>("/api/xbox"),
  xboxSync: () => req<XboxSummary & { ok?: boolean; error?: string; new_unlocked?: number }>("/api/xbox/sync", { method: "POST" }),
  garage: () => req<{ id: string; name: string; status: string }[]>("/api/garage"),
  setStatus: (id: string, status: string) => req(`/api/status/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify({ status }) }),
};

export const STAT_LABELS: Record<keyof Stats, string> = {
  speed: "Vitesse", acceleration: "Accélération", handling_road: "Maniabilité route",
  handling_offroad: "Tout-terrain", strength: "Solidité",
};

export const FIELD_LABELS: Record<string, string> = {
  manufacturer: "Constructeur", class: "Catégorie", seats: "Places", drivetrain: "Transmission",
  gears: "Rapports", weight_kg: "Masse (kg)", model_year: "Année", based_on: "Inspiré de",
  price: "Prix", sell_price_stolen: "Revente (volé)", style: "Style", era: "Époque",
  security: "Sécurité", access: "Accès", tracker: "Traceur", can_register: "Immatriculable",
  standout_set: "Collection", specialist: "Spécialiste", body_condition: "État",
  game_edition: "Édition", body_style: "Carrosserie", capacity: "Capacité", purchase_from: "Achat", moddable: "Personnalisable",
  ammo_upgrade: "Amélioration munitions", ...{ damage: "Dégâts", accuracy: "Précision", weapon_handling: "Maniabilité", range: "Portée" }, how_to_unlock: "Déblocage", location_text: "Emplacement",
  ...STAT_LABELS,
};

export const KIND_LABELS = { official: "Officiel (jeu)", community: "Mesure communautaire", subjective: "Appréciation" };
export const DRIVETRAIN_FR: Record<string, string> = { RWD: "Propulsion", FWD: "Traction", AWD: "Intégrale" };

export const RELIABILITY_FR: Record<string, string> = {
  confirmed: "Confirmé", probable: "Probable", to_verify: "À vérifier", theory: "Théorie",
  contradicted: "Contredit", obsolete: "Obsolète",
};
export const entityLink = (id: string) =>
  id.startsWith("vehicle:") ? `/vehicules/${encodeURIComponent(id)}`
  : id.startsWith("weapon:") ? `/armes/${encodeURIComponent(id)}` : `/fiche/${encodeURIComponent(id)}`;
