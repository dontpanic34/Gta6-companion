/** Fonctions « appareil » : micro (reconnaissance vocale), lecture à voix haute, écran toujours allumé.
 *  Sur le téléphone : modules Capacitor natifs. Dans un navigateur : API Web équivalentes si disponibles. */
import { SpeechRecognition } from "@capacitor-community/speech-recognition";
import { KeepAwake } from "@capacitor-community/keep-awake";

const native = () => !!(window as any).Capacitor?.isNativePlatform?.();

export async function voiceAvailable(): Promise<boolean> {
  if (native()) {
    try { return (await SpeechRecognition.available()).available; } catch { return false; }
  }
  return !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);
}

/** Écoute une phrase en français et renvoie le texte reconnu. */
export async function listen(): Promise<string> {
  if (native()) {
    const perm = await SpeechRecognition.requestPermissions();
    if (perm.speechRecognition !== "granted") throw new Error("Autorisez le micro pour parler à l'assistant.");
    const r = await SpeechRecognition.start({ language: "fr-FR", maxResults: 1, partialResults: false, popup: false,
      prompt: "Je vous écoute…" });
    return r.matches?.[0] ?? "";
  }
  const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  if (!SR) throw new Error("La reconnaissance vocale n'est pas disponible ici.");
  return new Promise((resolve, reject) => {
    const rec = new SR(); rec.lang = "fr-FR"; rec.interimResults = false; rec.maxAlternatives = 1;
    rec.onresult = (e: any) => resolve(e.results[0][0].transcript);
    rec.onerror = (e: any) => reject(new Error(e.error === "not-allowed" ? "Micro refusé." : "Je n'ai rien entendu."));
    rec.start();
  });
}

export async function stopListening() {
  if (native()) { try { await SpeechRecognition.stop(); } catch { /* déjà arrêté */ } }
}

/** Lit un texte à voix haute (voix française du téléphone). */
export function speak(text: string) {
  const s = (window as any).speechSynthesis as SpeechSynthesis | undefined;
  if (!s || !text) return;
  s.cancel();
  const u = new SpeechSynthesisUtterance(text.replace(/[*_#]/g, ""));
  u.lang = "fr-FR";
  const fr = s.getVoices().find((v) => v.lang?.startsWith("fr"));
  if (fr) u.voice = fr;
  s.speak(u);
}
export const canSpeak = () => !!(window as any).speechSynthesis;

let lock: any = null;
/** Garde l'écran allumé (mode « je joue »). */
export async function keepScreenOn(on: boolean) {
  if (native()) { try { await (on ? KeepAwake.keepAwake() : KeepAwake.allowSleep()); } catch { /* ignore */ } return; }
  try {
    if (on && (navigator as any).wakeLock) lock = await (navigator as any).wakeLock.request("screen");
    if (!on && lock) { await lock.release(); lock = null; }
  } catch { /* non supporté */ }
}
