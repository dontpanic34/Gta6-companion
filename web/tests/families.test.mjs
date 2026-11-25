// Vérifie que chaque catégorie réelle de la base tombe dans la bonne famille de filtres,
// et que la pastille d'un lieu a la même couleur que le bouton de sa famille.
import { readFileSync } from "node:fs";
const mod = await import(process.argv[2]);
const cats = JSON.parse(readFileSync(process.argv[3], "utf8"));   // [[catégorie, estSecret, nb], …]
const EXPECT = { "Véhicules rares": "vehicles", "Armes cachées et uniques": "weapons", "Argent et caches": "collect",
  "Activités": "activities", "Sous le pont": "stunts", "Lieux cachés": "secrets", "Garage": "garages", "Easter eggs": "secrets" };
let fail = 0;
for (const [cat, secret] of cats) {
  const f = mod.familyOf(cat, secret);
  const st = mod.categoryStyle(cat, secret);
  if (f.id === "other") { console.log("SANS FAMILLE:", cat); fail++; }
  if (EXPECT[cat] && EXPECT[cat] !== f.id) { console.log(`MAUVAISE FAMILLE: ${cat} -> ${f.id} (attendu ${EXPECT[cat]})`); fail++; }
  if (st.color !== f.color) { console.log(`COULEUR DIFFÉRENTE: ${cat}`); fail++; }
}
console.log(fail ? `${fail} erreur(s)` : `OK : ${cats.length} catégories, toutes bien rangées`);
process.exit(fail ? 1 : 0);
