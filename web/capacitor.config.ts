import type { CapacitorConfig } from "@capacitor/cli";

// L'application Android embarque l'interface ; les données viennent du PC via Tailscale.
// Remplacez l'URL par l'adresse Tailscale du PC (ex. http://100.x.y.z:8765).
const config: CapacitorConfig = {
  appId: "fr.perso.gta6companion",
  appName: "Leonida Companion",
  webDir: "dist",
  server: { androidScheme: "http", cleartext: true },
};
export default config;
