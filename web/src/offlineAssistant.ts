/** Assistant de secours, sans le PC : il ne « comprend » pas comme l'IA, mais cherche dans les données
 *  gardées sur le téléphone (déjà filtrées par l'anti-spoiler). Zone citée -> quoi faire là-bas ;
 *  sinon -> lieux, missions, personnages, véhicules dont le nom correspond. */
import { api, ChatReply, Place } from "./api";
import { ALL_FAMILIES, familyOf } from "./map/categories";

const norm = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
const STOP = new Set("comment faire pour je tu il on de la le les des du un une est que qui quoi ou dans sur avec viens arriver peux retourner voir aller trouver est-ce ce cette".split(" "));
const RADIUS: Record<number, number> = { 1: 2500, 2: 1400, 3: 700 };

export async function offlineChat(question: string): Promise<ChatReply> {
  const [places, zones, opts] = await Promise.all([
    api.places(new URLSearchParams()).catch(() => [] as Place[]),
    api.zones().catch(() => []),
    api.progressOptions().catch(() => null),
  ]);
  const q = ` ${norm(question)} `;
  const head = "(Hors ligne : le PC n'est pas joignable, je cherche dans les données du téléphone.)\n\n";

  // 1) une zone est citée : ce qu'on peut y faire
  const zone = [...zones].sort((a, b) => b.name.length - a.name.length).find((z) => q.includes(` ${norm(z.name)} `));
  if (zone) {
    const r = RADIUS[zone.tier] ?? 1500;
    const exact = places.filter((p) => p.x != null && p.precision === "exact");
    const byRegion = exact.filter((p) => norm(p.region ?? "") === norm(zone.name));
    // le nom de zone des fiches d'abord ; sinon un rayon autour du centre (plus serré pour les comtés)
    const here = byRegion.length >= 5 ? byRegion : exact.filter((p) => Math.hypot(p.x! - zone.x, p.y! - zone.y) < r);
    const groups = new Map<string, Place[]>();
    here.forEach((p) => { const f = familyOf(p.category, p.id.startsWith("secret:")); if (!f.hidden) groups.set(f.id, [...(groups.get(f.id) ?? []), p]); });
    const lines = [...groups.entries()].sort((a, b) => b[1].length - a[1].length).map(([id, l]) => {
      const fam = ALL_FAMILIES.find((f) => f.id === id);
      return `• ${fam?.label ?? id} : ${l.length} (${l.slice(0, 3).map((p) => p.name).join(", ")}${l.length > 3 ? "…" : ""})`;
    });
    return {
      text: head + (lines.length ? `À ${zone.name}, il y a :\n${lines.join("\n")}` : `Je n'ai rien de précis autour de ${zone.name} pour l'instant.`),
      cards: here.slice(0, 6).map((p) => ({ type: "place", id: p.id, name: p.name, subtitle: p.category ?? undefined, image: p.image })),
      actions: [{ type: "open_map", x: zone.x, y: zone.y, zoom: zone.tier === 1 ? 3 : zone.tier === 2 ? 4 : 5 }],
    };
  }

  // 2) recherche par nom
  const words = norm(question).split(" ").filter((w) => w.length >= 3 && !STOP.has(w));
  const hit = (name: string) => { const n = ` ${norm(name)} `; return words.length > 0 && words.some((w) => n.includes(` ${w}`)); };
  const chars = (opts?.characters ?? []).filter((c) => hit(c.name));
  const missions = (opts?.missions ?? []).filter((m) => hit(m.name));
  const found = places.filter((p) => hit(p.name)).slice(0, 6);
  const parts: string[] = [];
  if (chars.length) parts.push(`Personnage : ${chars.map((c) => c.name).join(", ")}. Ses missions et lieux sont dans l'Encyclopédie ; la position exacte d'un personnage n'est pas dans les données hors ligne.`);
  if (missions.length) parts.push(`Missions : ${missions.slice(0, 5).map((m) => m.name + (m.done ? " (faite)" : "")).join(", ")}.`);
  if (found.length) parts.push(`Sur la carte : ${found.map((p) => p.name).join(", ")}.`);
  return {
    text: head + (parts.length ? parts.join("\n\n")
      : "Je n'ai rien trouvé. Hors ligne, cite un lieu (ex. « Port Gellhorn »), un personnage ou un objet. Pour une vraie discussion, il faut être sur le Wi-Fi de la maison avec le PC allumé."),
    cards: found.map((p) => ({ type: "place", id: p.id, name: p.name, subtitle: p.category ?? undefined, image: p.image })),
    actions: found[0]?.x != null ? [{ type: "open_map", x: found[0].x!, y: found[0].y!, zoom: 5 }] : [],
  };
}
