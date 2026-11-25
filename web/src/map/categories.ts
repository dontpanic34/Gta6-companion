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

/** Style par catégorie réelle (picto + couleur), comme les cartes de référence. */
export interface CatStyle { icon: IconName; color: string }
const C = (icon: IconName, color: string): CatStyle => ({ icon, color });
const CATEGORY_STYLE: [RegExp, CatStyle][] = [
  [/arrêt de bus|gare|ferry|terminal/i, C("Bus", "#94a3b8")],
  [/sous le pont/i, C("Waves", "#38bdf8")],
  [/distributeur/i, C("Banknote", "#4ade80")],
  [/saut spectaculaire/i, C("Rocket", "#2dd4bf")],
  [/base jump/i, C("Plane", "#2dd4bf")],
  [/rase-mottes/i, C("Plane", "#a78bfa")],
  [/street food|fast-food|cafés|delights|food/i, C("UtensilsCrossed", "#fb923c")],
  [/bar|club|alcool/i, C("Beer", "#f59e0b")],
  [/basket/i, C("Dribbble", "#4ade80")],
  [/borne de recharge/i, C("Zap", "#facc15")],
  [/véhicule d.exception|véhicules rares|location/i, C("CarFront", "#facc15")],
  [/supérette|électronique/i, C("Store", "#60a5fa")],
  [/station-service/i, C("Fuel", "#60a5fa")],
  [/coffre-fort/i, C("Vault", "#4ade80")],
  [/argent|caches|prêts/i, C("HandCoins", "#4ade80")],
  [/armes|ammu|stand de tir/i, C("Crosshair", "#f97316")],
  [/pêche/i, C("Fish", "#38bdf8")],
  [/easter|référence|caméo|curiosité|mural|sculpture/i, C("Star", "#ff4f8b")],
  [/mystère/i, C("Eye", "#ff4f8b")],
  [/créature|rencontre/i, C("PawPrint", "#ff4f8b")],
  [/lieux cachés/i, C("MapPin", "#ff4f8b")],
  [/arcade|billard|drones|mini-golf|golf/i, C("Gamepad2", "#c084fc")],
  [/souvenirs|vêtements|tenues|décontracté|friperie|chaussures/i, C("Shirt", "#e879f9")],
  [/coiffure|tatouage/i, C("Scissors", "#e879f9")],
  [/pay 'n' spray|tuning|garage|lavage/i, C("Wrench", "#94a3b8")],
  [/course|raceway|speedway|mud club/i, C("Flag", "#a78bfa")],
  [/activités/i, C("Trophy", "#4ade80")],
  [/méditation/i, C("Flame", "#c084fc")],
  [/magazine|troc de livres|playlist/i, C("BookOpen", "#cbd5e1")],
  [/salle de sport/i, C("Dumbbell", "#4ade80")],
  [/monument/i, C("Landmark", "#cbd5e1")],
];
const catCache = new Map<string, CatStyle>();
export function categoryStyle(category: string | null, isSecret: boolean): CatStyle {
  const key = `${isSecret ? "s:" : ""}${category ?? ""}`;
  if (!catCache.has(key)) {
    const hit = CATEGORY_STYLE.find(([rx]) => rx.test(category ?? ""));
    const fam = familyOf(category, isSecret);
    catCache.set(key, hit ? hit[1] : { icon: fam.icon, color: fam.color });
  }
  return catCache.get(key)!;
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

const esc = (t: string) => t.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));

/** Marqueur : picto coloré à liseré sombre (lisible sur la carte), libellé optionnel dessous. */
export function markerHtml(st: CatStyle, size: number, done: boolean, label?: string): string {
  const g = Math.round(size * 0.62);
  return `<div class="mk${done ? " done" : ""}"><div class="pin" style="width:${size}px;height:${size}px;background:${st.color}">` +
    `<svg width="${g}" height="${g}" viewBox="0 0 24 24" fill="none" stroke="#0d0b14" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">${iconInner(st.icon)}</svg></div>` +
    (label ? `<span class="mk-label">${esc(label)}</span>` : "") + `</div>`;
}

/** Pictos par classe de véhicule / d'arme (catalogue). */
const CLASS_STYLE: [RegExp, CatStyle][] = [
  [/super/i, C("Gauge", "#ff4f8b")], [/sport/i, C("CarFront", "#f97316")], [/muscle/i, C("Flame", "#ef4444")],
  [/off-?road|tout/i, C("Mountain", "#a3e635")], [/suv|pickup/i, C("Truck", "#84cc16")], [/sedan|berline/i, C("Car", "#60a5fa")],
  [/coupe|compact/i, C("Car", "#38bdf8")], [/moto|motorcycle/i, C("Bike", "#facc15")], [/cycle|vélo/i, C("Bike", "#a3e635")],
  [/boat|bateau/i, C("Sailboat", "#38bdf8")], [/plane|avion|aircraft/i, C("Plane", "#c084fc")], [/heli/i, C("Plane", "#c084fc")],
  [/van|commercial|industrial/i, C("Truck", "#94a3b8")], [/emergency|police|urgence/i, C("Siren", "#3b82f6")],
  [/handgun|pistol/i, C("Crosshair", "#f97316")], [/smg/i, C("Crosshair", "#fb923c")], [/assault|tactical/i, C("Crosshair", "#ef4444")],
  [/sniper/i, C("Target", "#c084fc")], [/shotgun/i, C("Crosshair", "#facc15")], [/lmg|heavy|launcher/i, C("Bomb", "#ef4444")],
  [/melee|mêlée/i, C("Sword", "#94a3b8")], [/throw/i, C("Bomb", "#a3e635")],
];
export function classStyle(cls: string | null): CatStyle {
  const hit = CLASS_STYLE.find(([rx]) => rx.test(cls ?? ""));
  return hit ? hit[1] : C("CircleDot", "#cbd5e1");
}
