import { icons } from "lucide";

/** Familles de lieux : couleur + pictogramme Lucide (ISC), comme les pastilles des cartes de référence. */
type IconName = keyof typeof icons;
export interface Family { id: string; label: string; color: string; icon: IconName; match: RegExp }

export const FAMILIES: Family[] = [
  { id: "secrets", label: "Secrets", color: "#ff3d8b", icon: "Sparkles", match: /easter|myst|créature|rencontre|référence|caméo|lieux cachés|curiosit|astuce|sculpture|monument|secret/i },
  { id: "collect", label: "Caches & objets", color: "#ffd166", icon: "Gem", match: /coffre|argent|cache|trésor|carte|flamant|magazine|playlist|mural|collect/i },
  { id: "vehicles", label: "Véhicules", color: "#2ee6d6", icon: "CarFront", match: /véhicule|vehicle/i },
  { id: "weapons", label: "Armes", color: "#ff7a1a", icon: "Crosshair", match: /arme|ammu|stand de tir|weapon/i },
  { id: "stunts", label: "Sauts & courses", color: "#a78bfa", icon: "Flag", match: /saut|sous le pont|rase-mottes|course|raceway|speedway|mud club/i },
  { id: "activities", label: "Activités", color: "#4ade80", icon: "Trophy", match: /activit|basket|pêche|arcade|billard|golf|salle de sport|méditation/i },
  { id: "garages", label: "Garages & tuning", color: "#60a5fa", icon: "Wrench", match: /garage|tuning|pay 'n' spray/i },
];
export const OTHER: Family = { id: "other", label: "Autres", color: "#cbd5e1", icon: "MapPin", match: /.*/ };
export const ALL_FAMILIES = [...FAMILIES, OTHER];

/** Table EXPLICITE catégorie réelle -> famille (une catégorie = une seule famille).
 *  Les regex ci-dessus ne servent que de repli pour une catégorie nouvelle. */
const CATEGORY_FAMILY: Record<string, string> = {
  "Easter eggs": "secrets", "Références et caméos": "secrets", "Lieux cachés": "secrets", "Créatures et rencontres": "secrets",
  "Mystères": "secrets", "Curiosité": "secrets", "Astuces et mécaniques": "secrets", "Sculpture": "secrets", "Monument": "secrets",
  "Coffre-fort": "collect", "Argent et caches": "collect", "Cartes, flamants et plus": "collect", "Trésors et sous-marin": "collect",
  "Magazine": "collect", "Playlist unique": "collect", "1010 Mural": "collect",
  "Véhicule d’exception": "vehicles", "Véhicules rares": "vehicles", "Moses Vehicle": "vehicles",
  "Armes cachées et uniques": "weapons", "Ammu-Nation": "weapons", "Stand de tir": "weapons",
  "Sous le pont": "stunts", "Saut spectaculaire": "stunts", "Vol en rase-mottes": "stunts", "Saut en base jump": "stunts",
  "Défi de course": "stunts", "Thrillbilly Mud Club": "stunts", "Gellhorn Raceway": "stunts", "Ambrosia Raceway": "stunts",
  "Hamlet Boone Speedway": "stunts", "Intro aux courses": "stunts",
  "Activités": "activities", "Panier de basket": "activities", "Spot de pêche": "activities", "Borne d’arcade": "activities",
  "Billard": "activities", "Mini-golf": "activities", "Terrain de golf": "activities", "Salle de sport": "activities",
  "Lieux de méditation": "activities",
  "Pay 'n' Spray": "garages", "Garage de tuning": "garages", "Garage à vendre": "garages", "Garage": "garages",
};

const cache = new Map<string, Family>();
/** Famille d'un lieu : d'après sa CATÉGORIE (un secret « Véhicules rares » est un véhicule). */
export function familyOf(category: string | null, isSecret: boolean): Family {
  const key = `${isSecret ? "s:" : ""}${category ?? ""}`;
  if (!cache.has(key)) {
    const id = category ? CATEGORY_FAMILY[category] : undefined;
    const fam = (id && FAMILIES.find((f) => f.id === id))
      || (category && FAMILIES.find((f) => f.match.test(category)))
      || (isSecret ? FAMILIES[0] : OTHER);
    cache.set(key, fam);
  }
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
    catCache.set(key, { icon: hit ? hit[1].icon : fam.icon, color: fam.color });
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
/** Icônes illustrées (planche générée avec Gemini, découpée par scripts/cut_icons.py) : catégorie -> n° d'icône. */
const CATEGORY_IMG: Record<string, number> = {
  "Saut spectaculaire": 0, "Sous le pont": 1, "Vol en rase-mottes": 2, "Saut en base jump": 3,
  "Défi de course": 4, "Thrillbilly Mud Club": 4, "Gellhorn Raceway": 4, "Ambrosia Raceway": 4, "Hamlet Boone Speedway": 4, "Intro aux courses": 4,
  "Coffre-fort": 5, "Argent et caches": 6, "Cartes, flamants et plus": 8, "Trésors et sous-marin": 9, "Magazine": 10, "Playlist unique": 11,
  "Véhicules rares": 12, "Véhicule d’exception": 13, "Moses Vehicle": 13,
  "Armes cachées et uniques": 14, "Ammu-Nation": 14, "Stand de tir": 16,
  "Easter eggs": 17, "Mystères": 18, "Créatures et rencontres": 19, "Lieux cachés": 20, "Activités": 21,
  "Panier de basket": 22, "Spot de pêche": 23, "Borne d’arcade": 24, "Billard": 25, "Mini-golf": 26, "Terrain de golf": 26,
  "Salle de sport": 27, "Lieux de méditation": 28, "Garage de tuning": 29, "Pay 'n' Spray": 30, "Garage": 31, "Garage à vendre": 31,
  "Curiosité": 33, "Astuces et mécaniques": 34, "Sculpture": 36, "Monument": 36, "Références et caméos": 37, "1010 Mural": 38,
};
export function categoryImage(category: string | null): string | null {
  const n = category != null ? CATEGORY_IMG[category] : undefined;
  return n == null ? null : `icons/map/${String(n).padStart(2, "0")}.png`;
}

export function markerHtml(st: CatStyle, size: number, done: boolean, label?: string, category?: string | null): string {
  const img = categoryImage(category ?? null);
  if (img) {
    return `<div class="mk${done ? " done" : ""}"><img class="pin3" src="${img}" width="${Math.round(size * 1.35)}" height="${Math.round(size * 1.35)}" alt="" draggable="false">` +
      (label ? `<span class="mk-label">${esc(label)}</span>` : "") + `</div>`;
  }
  // Style « autocollant » (comme les cartes de référence) : pas de pastille, le picto lui-même
  // est coloré, cerné d'un épais contour sombre puis d'un liseré clair -> lisible sur toute la carte.
  const g = iconInner(st.icon);
  const layer = (stroke: string, w: number) =>
    `<g fill="none" stroke="${stroke}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round">${g}</g>`;
  return `<div class="mk${done ? " done" : ""}"><svg class="pin2" width="${size}" height="${size}" viewBox="-3 -3 30 30">` +
    layer("#140a24", 7.2) + layer("#ffffff", 4.6) + layer(st.color, 2.6) + `</svg>` +
    (label ? `<span class="mk-label">${esc(label)}</span>` : "") + `</div>`;
}

/** Pictos par classe de véhicule / d'arme (catalogue). */
const CLASS_STYLE: [RegExp, CatStyle][] = [
  [/super/i, C("Gauge", "#ff4f8b")], [/sport/i, C("CarFront", "#f97316")], [/muscle/i, C("Flame", "#ef4444")],
  [/off-?road|tout/i, C("Mountain", "#a3e635")], [/suv|pickup/i, C("Truck", "#84cc16")], [/sedan|berline/i, C("Car", "#60a5fa")],
  [/coupe|compact/i, C("Car", "#38bdf8")], [/moto|motorcycle/i, C("Bike", "#facc15")], [/cycle|vélo/i, C("Bike", "#a3e635")],
  [/boat|bateau/i, C("Sailboat", "#38bdf8")], [/plane|avion|aircraft/i, C("Plane", "#c084fc")], [/heli/i, C("Plane", "#c084fc")],
  [/van|commercial|industrial/i, C("Truck", "#94a3b8")], [/train/i, C("TrainFront", "#94a3b8")], [/emergency|police|urgence/i, C("Siren", "#3b82f6")],
  [/handgun|pistol/i, C("Crosshair", "#f97316")], [/smg/i, C("Crosshair", "#fb923c")], [/assault|tactical/i, C("Crosshair", "#ef4444")],
  [/sniper/i, C("Target", "#c084fc")], [/shotgun/i, C("Crosshair", "#facc15")], [/lmg|heavy|launcher/i, C("Bomb", "#ef4444")],
  [/melee|mêlée/i, C("Sword", "#94a3b8")], [/throw/i, C("Bomb", "#a3e635")], [/gear|équipement/i, C("Backpack", "#cbd5e1")],
];
export function classStyle(cls: string | null): CatStyle {
  const hit = CLASS_STYLE.find(([rx]) => rx.test(cls ?? ""));
  return hit ? hit[1] : C("CircleDot", "#cbd5e1");
}
