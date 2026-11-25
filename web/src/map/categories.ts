import { icons } from "lucide";

/** Familles de lieux : couleur + pictogramme Lucide (ISC), comme les pastilles des cartes de référence. */
type IconName = keyof typeof icons;
export interface Family { id: string; label: string; color: string; icon: IconName; match: RegExp }

export const FAMILIES: Family[] = [
  { id: "secrets", label: "Secrets", color: "#ff4f8b", icon: "Sparkles", match: /secret|myst|easter|créature|rencontre|référence|caméo|cachés?/i },
  { id: "collect", label: "Caches & objets", color: "#f5b82e", icon: "Gem", match: /coffre|safe|planque|argent|collect|trésor|cache|carte|card|signal/i },
  { id: "vehicles", label: "Véhicules", color: "#2dd4bf", icon: "CarFront", match: /véhicule|vehicle|voiture|garage|concession|bateau|avion/i },
  { id: "weapons", label: "Armes", color: "#f97316", icon: "Crosshair", match: /arme|weapon|ammu|munition/i },
  { id: "stunts", label: "Sauts & courses", color: "#a78bfa", icon: "Flag", match: /saut|stunt|course|race|knife|couteau|pont|bridge/i },
  { id: "activities", label: "Activités", color: "#4ade80", icon: "Trophy", match: /activit|sport|pêche|fishing|basket|golf|tennis|méditation|tir|shooting|arcade|club/i },
  { id: "shops", label: "Commerces", color: "#60a5fa", icon: "ShoppingBag", match: /magasin|store|shop|bar|café|restau|food|station|essence|gas|atm|distributeur|coiffeur|tatou|vêtement|pharmac|banque|borne|charg/i },
  { id: "properties", label: "Propriétés", color: "#e879f9", icon: "House", match: /propriét|property|safehouse|maison|appart/i },
  { id: "transport", label: "Transports", color: "#94a3b8", icon: "BusFront", match: /bus|arrêt|métro|train|taxi|transport/i },
];
export const OTHER: Family = { id: "other", label: "Autres", color: "#cbd5e1", icon: "MapPin", match: /.*/ };
export const ALL_FAMILIES = [...FAMILIES, OTHER];

const cache = new Map<string, Family>();
export function familyOf(category: string | null, isSecret: boolean): Family {
  if (isSecret) return FAMILIES[0];
  const key = category ?? "";
  if (!cache.has(key)) cache.set(key, FAMILIES.find((f) => f.match.test(key)) ?? OTHER);
  return cache.get(key)!;
}

/** Chemins SVG internes d'une icône Lucide (sans la balise <svg>). */
const inner = new Map<string, string>();
export function iconInner(name: IconName): string {
  if (!inner.has(name)) {
    const raw = icons[name] as unknown as unknown[];
    // Selon la version : [["path",{…}],…] ou ["svg",{…},[["path",{…}],…]]
    const node = (raw[0] === "svg" ? raw[2] : raw) as [string, Record<string, string | number>][];
    inner.set(name, node.map(([tag, attrs]) =>
      `<${tag} ${Object.entries(attrs).map(([k, v]) => `${k}="${v}"`).join(" ")}/>`).join(""));
  }
  return inner.get(name)!;
}

/** Pastille de carte : disque coloré, liseré sombre, pictogramme blanc. */
export function markerHtml(f: Family, size: number, done: boolean): string {
  const g = Math.round(size * 0.56);
  return `<div class="pin${done ? " done" : ""}" style="width:${size}px;height:${size}px;background:${f.color}">` +
    `<svg width="${g}" height="${g}" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">${iconInner(f.icon)}</svg></div>`;
}
