/** Regroupe les ~80 catégories des sources en familles lisibles, avec couleur + pictogramme. */
export interface Family { id: string; label: string; color: string; icon: string; match: RegExp }

export const FAMILIES: Family[] = [
  { id: "secrets", label: "Secrets & mystères", color: "#ff4f8b", icon: "✦", match: /secret|myst|easter|créature|rencontre|référence|caméo|cachés?/i },
  { id: "collect", label: "Objets & caches", color: "#facc15", icon: "◆", match: /coffre|safe|planque|argent|collect|trésor|cache|carte|card|signal/i },
  { id: "vehicles", label: "Véhicules", color: "#38d6c4", icon: "🚗", match: /véhicule|vehicle|voiture|garage|concession|bateau|avion/i },
  { id: "weapons", label: "Armes", color: "#f97316", icon: "✚", match: /arme|weapon|ammu|munition/i },
  { id: "stunts", label: "Sauts & courses", color: "#a78bfa", icon: "↗", match: /saut|stunt|course|race|knife|couteau|pont|bridge/i },
  { id: "activities", label: "Activités & sports", color: "#4ade80", icon: "●", match: /activit|sport|pêche|fishing|basket|golf|tennis|méditation|tir|shooting|arcade|club/i },
  { id: "shops", label: "Commerces & services", color: "#60a5fa", icon: "■", match: /magasin|store|shop|bar|café|restau|food|station|essence|gas|atm|distributeur|coiffeur|tatou|vêtement|pharmac|banque|borne|charg/i },
  { id: "properties", label: "Propriétés", color: "#e879f9", icon: "⌂", match: /propriét|property|planque|safehouse|maison|appart/i },
  { id: "transport", label: "Transports", color: "#94a3b8", icon: "▲", match: /bus|arrêt|métro|train|taxi|transport/i },
];
export const OTHER: Family = { id: "other", label: "Autres lieux", color: "#cbd5e1", icon: "•", match: /.*/ };

const cache = new Map<string, Family>();
export function familyOf(category: string | null, isSecret: boolean): Family {
  if (isSecret) return FAMILIES[0];
  const key = category ?? "";
  if (!cache.has(key)) cache.set(key, FAMILIES.find((f) => f.match.test(key)) ?? OTHER);
  return cache.get(key)!;
}
export const ALL_FAMILIES = [...FAMILIES, OTHER];
