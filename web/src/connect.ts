/** Connexion automatique au PC sur le Wi-Fi de la maison (sans Tailscale, sans saisie) et
 *  mémorisation des données de la nuit pour le hors ligne. */
import { getBaseUrl, setBaseUrl } from "./api";

const SUBNETS = ["192.168.1", "192.168.0", "192.168.2", "192.168.10", "192.168.100", "192.168.50", "192.168.68",
  "192.168.178", "192.168.31", "192.168.86", "10.0.0", "10.0.1", "10.1.1", "172.16.0"];
const PORT = 8765;
const DATA_CACHE = "gta-data-v1";

async function probe(base: string, ms = 900): Promise<boolean> {
  try {
    const r = await fetch(`${base}/api/health`, { signal: AbortSignal.timeout(ms) });
    return r.ok && (await r.json()).app === "gta6-companion";
  } catch { return false; }
}

/** Cherche le PC : d'abord la dernière adresse connue, puis un balayage rapide des réseaux domestiques courants. */
export async function discoverPC(onProgress?: (t: string) => void): Promise<string | null> {
  const saved = getBaseUrl();
  if (saved && await probe(saved, 1500)) return saved;
  for (const net of SUBNETS) {
    onProgress?.(`Recherche du PC sur ${net}.x…`);
    const hosts = Array.from({ length: 254 }, (_, i) => `http://${net}.${i + 1}:${PORT}`);
    const found = await new Promise<string | null>((resolve) => {
      let pending = hosts.length, done = false;
      hosts.forEach((h) => probe(h).then((ok) => {
        if (ok && !done) { done = true; resolve(h); }
        if (--pending === 0 && !done) resolve(null);
      }));
    });
    if (found) { setBaseUrl(found); return found; }
  }
  return null;
}

/** Télécharge les données de la nuit depuis le PC et les garde sur le téléphone. */
export async function refreshCachedData(base: string): Promise<boolean> {
  try {
    const r = await fetch(`${base}/api/snapshot`, { signal: AbortSignal.timeout(20000) });
    if (!r.ok) return false;
    const c = await caches.open(DATA_CACHE);
    await c.put("snapshot.json", r.clone());
    try { localStorage.setItem("data_updated_at", new Date().toISOString()); } catch { /* ignore */ }
    return true;
  } catch { return false; }
}

/** Données hors ligne : la dernière version reçue du PC, sinon celle embarquée dans l'APK. */
export async function loadSnapshot(): Promise<any> {
  try {
    const c = await caches.open(DATA_CACHE);
    const hit = await c.match("snapshot.json");
    if (hit) return await hit.json();
  } catch { /* Cache API indisponible */ }
  return (await fetch("data/snapshot.json")).json();
}

export const dataUpdatedAt = () => { try { return localStorage.getItem("data_updated_at"); } catch { return null; } };

/** Au démarrage : trouver le PC (en arrière-plan) puis rafraîchir les données gardées. */
export async function autoConnect(onState?: (s: { base: string | null; msg: string }) => void) {
  onState?.({ base: null, msg: "Recherche du PC…" });
  const base = await discoverPC((m) => onState?.({ base: null, msg: m }));
  if (!base) { onState?.({ base: null, msg: "PC introuvable : mode hors ligne" }); return null; }
  onState?.({ base, msg: "Connecté au PC" });
  await refreshCachedData(base);
  return base;
}
