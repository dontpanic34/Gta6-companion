export type Stats = Record<"speed" | "acceleration" | "handling_road" | "handling_offroad" | "strength", number | null>;

export interface VehicleSummary {
  id: string; name: string; model_id: string; variant_type: string;
  manufacturer: string | null; class: string | null; image: string | null;
  stats: Stats; price: number | null; seats: number | null; drivetrain: string | null;
  score: { value: number; coverage: number } | null;
}

export interface FieldValue {
  value: unknown; kind: "official" | "community" | "subjective"; contradiction: boolean;
  sources: { source: string; url: string | null; value: unknown; status: string; observed_at: string }[];
}

export interface VehicleDetail {
  id: string; name: string; kind: string; variant_type?: string; missable_warning: boolean;
  fields: Record<string, FieldValue>; media: string[];
  siblings?: { id: string; name: string; variant_type: string }[];
  kits?: { id: string; name: string }[]; mods?: { id: string; name: string; category: string }[];
  hidden_fields: number;
}

export interface Progress {
  chapter: number; completed_missions: string[]; met_characters: string[]; discovered_regions: string[];
}

const TOKEN_KEY = "companion_token";
export const getToken = () => { try { return localStorage.getItem(TOKEN_KEY) ?? ""; } catch { return ""; } };
export const setToken = (t: string) => { try { localStorage.setItem(TOKEN_KEY, t); } catch { /* ignore */ } };

async function req<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const t = getToken();
  if (t) headers.Authorization = `Bearer ${t}`;
  const r = await fetch(path, { ...init, headers: { ...headers, ...(init.headers as object) } });
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
  game_edition: "Édition", how_to_unlock: "Déblocage", location_text: "Emplacement",
  ...STAT_LABELS,
};

export const KIND_LABELS = { official: "Officiel (jeu)", community: "Mesure communautaire", subjective: "Appréciation" };
export const DRIVETRAIN_FR: Record<string, string> = { RWD: "Propulsion", FWD: "Traction", AWD: "Intégrale" };
