# GTA VI Companion — Phase 1 (audit) & Phase 2 (conception)

_Audit réalisé le 24/11/2026 (le jeu est sorti le 19/11/2026). Tout ce qui est indiqué « vérifié » a été lu directement sur les sites ; le reste est marqué « non vérifié »._

---

## 1. Audit des sources

### 1.1 GTACity — gtacity.gg/fr/gta-6

| Point | Constat (vérifié) |
|---|---|
| Langue | Français natif (avec les URL de catégories en français). |
| Rubriques | Carte, Missions, Armes (par classe + comparateur), Véhicules (14 catégories, classement tout-terrain, comparateur), Équipement, Lieux, Personnages, Objets, Radio, Tier lists, Codes des coffres, Codes de triche, Guides, Actualités, « Ma progression ». |
| Variantes | **Oui, structurées** : `/vehicules/super/emerus/black-widow-emerus` → modèle de base « Emerus » + variante nommée. Idem pour Vitello, Kamacho, etc. |
| Données structurées | JSON-LD schema.org `Product` sur chaque véhicule : marque, places, et notes /10 (Vitesse, Accélération, Maniabilité, Tout-terrain, Robustesse, Score global). |
| API | Les CGU mentionnent une « API publique » avec ses propres limites, mais **aucune documentation n'a été trouvée** (`/api`, `/developers`, `/docs` → 404). `robots.txt` : `Disallow: /api/`. |
| CGU (citées) | « Tu peux partager des liens et de courtes citations en indiquant la source. **Tu ne peux pas copier le Service ou sa base de données en masse sans notre autorisation écrite.** » et « ne l'aspire pas en masse ». |
| Fréquence | Actualités quotidiennes visibles. Pas de date de mise à jour par fiche relevée. |

**Verdict** : c'est la meilleure source pour les variantes et les notes chiffrées en français. **L'aspiration en masse est interdite sans autorisation écrite.**

### 1.2 GTA6Map.city — gta6map.city/fr/

| Point | Constat (vérifié, page « À propos ») |
|---|---|
| Contenu | **3 002 marqueurs** : 2 456 issus de la carte du jeu (81 catégories), 216 lieux nommés, 330 secrets et easter eggs. Pages par région (27 : Vice City, Port Gellhorn, Key Lento, Ambrosia…) et par catégorie (sauts, coffres, véhicules remarquables, pêche, etc.), bâtiments accessibles, itinéraires. |
| Méthode | Positions recalées depuis des captures de la carte du jeu. Secrets extraits de clips YouTube/TikTok/X/Reddit, **analysés toutes les 30 minutes**. Chaque secret porte une **précision : exact / à proximité / zone**, ce qui est très utile pour notre indice de fiabilité. |
| Données/tuiles | `robots.txt` : **`Disallow: /data/` et `Disallow: /tiles/`**. Les données brutes et les tuiles sont donc explicitement exclues de la collecte automatisée. |
| Fond de carte | Provient de **« GTA VI Landmarks » — licence CC BY 4.0 — map.gtadb.org**. C'est la seule ressource cartographique **librement réutilisable** identifiée. |
| CGU | Aucune page de conditions dédiée (seulement À propos et Confidentialité). Carte réalisée par un fan, contact : @phosphenq sur X. |

**Verdict** : c'est la meilleure source de positions et de secrets, mais les données et les tuiles ne doivent pas être aspirées. On peut en revanche **utiliser directement la source amont CC BY 4.0** (GTA VI Landmarks) et **demander l'autorisation** à l'auteur.

### 1.3 GTABase — gtabase.com/gta-6/

| Point | Constat (vérifié) |
|---|---|
| Rubriques | Véhicules (+ comparateur, meilleurs véhicules), Armes, Missions, Missions secondaires, Strangers, Événements aléatoires, Propriétés, Personnages, Gangs, Animaux, Radio, Carte et lieux, Checklist 100 %, Guides, Codes de triche. |
| Fiche véhicule (ex. Preziosa Cheetah) | **La plus riche** : modèle de base (« Cheetah '95 »), véhicule réel (« Ferrari Testarossa, 512 BB »), classe, constructeur, année, style, époque, places, masse (1 630 kg), transmission (RWD), rapports (5), prix (32 750 $), valeur de revente volée, traceur, sécurité (Key Cloner), immatriculable, set « Standout », méthode d'obtention (Ultimate Edition), emplacement, liste des variantes liées. |
| Données structurées | `llms.txt` publié (index des rubriques). `sitemap-4seo.xml`. Pas d'API publique documentée. |
| robots.txt | Permissif sur les fiches. Il interdit les comparaisons de 3 véhicules ou plus, la recherche interne, les profils et `wblapi=`. |
| CGU | **Aucune page de conditions d'utilisation trouvée.** Pied de page : « © 2014-2026 GTABase.com. All Rights Reserved. » |
| Remarque | Plusieurs requêtes rapprochées ont reçu des connexions refusées (code 000), signe probable d'une limitation de débit ou d'un anti-bot. |

**Verdict** : c'est la source la plus complète en faits techniques (transmission, masse, véhicule réel, variantes, déblocage). Tous les droits sont réservés : **reprise en masse interdite par défaut**.

### 1.4 Ce que l'audit n'a pas pu vérifier
- L'API publique de GTACity (existence d'une documentation, conditions).
- Les conditions de licence exactes de GTA VI Landmarks : l'hôte map.gtadb.org est encore bloqué par le réseau de cette session.
- Les statistiques d'armes détaillées, à auditer à l'étape suivante (les pages ont été téléchargées, pas encore analysées en détail).
- Le niveau de spoiler des contenus « missions » sur chaque site.

### 1.5 Conclusion juridique et stratégie de données

**Aucune des trois plateformes n'autorise la copie en masse de sa base.** Les aspirer chaque nuit contreviendrait à leurs conditions (GTACity explicitement, GTA6Map via robots.txt, GTABase par réserve de droits). Je propose donc :

1. **Demander une autorisation écrite** aux trois sites (je fournirai les modèles de messages) : accès à l'API GTACity, permission de synchroniser pour un usage strictement personnel et non diffusé. C'est la voie qui débloque la synchronisation quotidienne automatique.
2. **En attendant, utiliser des sources ouvertes** : GTA VI Landmarks (CC BY 4.0) pour le fond de carte et les lieux, wikis sous licence libre et sources officielles Rockstar.
3. **Utiliser les trois sites de façon conforme** dès maintenant :
   - **Veille légère** : lecture des sitemaps et des pages « Actualités » à faible fréquence, pour **détecter** les nouveautés (titre + lien), sans copier le contenu.
   - **Fiches « lien profond »** : chaque entrée de l'application pointe vers la page source.
   - **Saisie assistée** : l'assistant IA local m'aide à créer une fiche à partir d'une page que je consulte. C'est un usage personnel, ponctuel, avec citation de la source, et non une aspiration en masse.
4. **Architecture prête** : chaque source est un connecteur avec un statut `autorisé / restreint / interdit`. Dès qu'une autorisation arrive, on active le connecteur complet sans rien refaire.

> Usage personnel ou pas, je ne contournerai ni robots.txt, ni les limitations de débit, ni les CGU.

---

## 2. Architecture proposée

```
 PC Windows (toujours allumé)                         Pixel 10 Pro
 ┌──────────────────────────────────────────┐        ┌─────────────────────────┐
 │ Collecteur (Python, Planificateur Win)   │        │ App Capacitor (React)   │
 │  ├ connecteurs/ (1 par source, isolés)    │        │  ├ SQLite local (copie) │
 │  ├ normalisation · dédoublonnage          │        │  ├ carte MapLibre       │
 │  ├ recoupement · fiabilité · spoiler      │        │  ├ filtres/comparateur  │
 │  └ quarantaine → validation → publication │        │  │  (100 % hors ligne)  │
 │                                           │ Tail-  │  └ assistant (si PC     │
 │ SQLite maître (+ FTS5 + sqlite-vec)       │ scale  │     joignable)          │
 │ API FastAPI (auth jeton) ─────────────────┼───────►│                         │
 │ Ollama (Qwen 2.5 14B / Mistral Small)     │ delta  └─────────────────────────┘
 │ Sauvegardes quotidiennes versionnées      │ sync
 └──────────────────────────────────────────┘
```

| Brique | Choix | Pourquoi |
|---|---|---|
| UI | React + TypeScript + Vite | Un seul code pour PC (navigateur ou PWA) et Android. |
| Android | **Capacitor** | Il réutilise le code web, gère le SQLite natif (`@capacitor-community/sqlite`) et le mode hors ligne. Une application Kotlin native doublerait le travail. |
| Backend | FastAPI (Python) | Même langage que le collecteur et l'écosystème IA. |
| Base | **SQLite** + migrations (Alembic) | Local, gratuit, copiable tel quel sur le téléphone. |
| Recherche | FTS5 (français, sans accents) + **sqlite-vec** | Tout reste dans un seul fichier. Pas de serveur vectoriel à maintenir. |
| Carte | **MapLibre GL** + tuiles générées localement depuis GTA VI Landmarks (CC BY 4.0) | Rendu vectoriel fluide, rotation, hors ligne. |
| IA | Ollama : modèle 14B quantifié (≈ 9–10 Go VRAM) + `nomic-embed-text` / `bge-m3` pour les embeddings | Tient dans 16 Go de VRAM. Aucun coût d'API. |
| Accès distant | Tailscale (votre tailnet existe déjà) + jeton applicatif | Rien n'est exposé publiquement sur Internet. |
| Planification | Planificateur de tâches Windows | Natif, et il relance la tâche après un redémarrage. |

L'application fonctionne **sans IA** : carte, fiches, filtres, recherche et comparateurs sont du SQL pur, exécuté sur le téléphone.

---

## 3. Modèle de données (extrait)

### 3.1 Principes
- **Identifiants stables** : slug canonique (`vehicle:grotti-cheetah-95:preziosa`), jamais l'URL d'une source.
- **Chaque valeur est une « affirmation » sourcée** : la table `claim` contient entité, champ, valeur, source, date, type (`officiel_jeu` / `mesure_communautaire` / `appreciation`) et statut. Les contradictions sont conservées côte à côte, et la valeur affichée est choisie par règle (fiabilité de la source, puis fraîcheur, puis vérification manuelle).
- **Historique complet** : rien n'est écrasé. Une table `revision` permet le retour arrière.

### 3.2 Variantes et personnalisations (armes ET véhicules)

C'est une exigence de premier plan. GTACity et GTABase exposent déjà la relation « modèle de base → variante ».

```
vehicle_model        (Cheetah '95)            weapon_model     (Akulus)
  └─ vehicle_variant (Preziosa, Black Widow…)   └─ weapon_variant (finitions, versions uniques)
       ├ type : standard | nommée | unique | police | édition | secrète
       ├ stats propres (claims)                 ├ stats propres (claims)
       └ obtention / emplacements               └ obtention / emplacements
mod_category  (carrosserie, moteur, kit, livrée, jantes, accessoire d'arme…)
mod_option    (option précise, prix, prérequis, effet sur stats si connu)
variant_mod   (compatibilité variante ↔ option)
kit           (ensemble nommé d'options : « kit large », « kit rallye »…)
```

Le comparateur et les filtres travaillent **au niveau de la variante**. Les kits et options apparaissent dans la fiche et peuvent être filtrés (« a un kit tout-terrain »).

### 3.3 Anti-spoiler au niveau des données

Chaque entité et **chaque champ sensible** porte :
- `spoiler_gate` : condition de progression (`chapitre >= 3`, `mission:x terminée`, `personnage:y rencontré`, `région:z découverte`) ;
- `disclosure_level` : 1 = découverte, 2 = indice, 3 = solution ;
- `spoiler_status` : `évalué` / **`inconnu` (masqué par défaut)**.

Les fiches de mission sont **physiquement scindées** : `activity_start` (lieu, horaires, prérequis), `activity_hint[]` (indices ordonnés), `activity_solution` (déroulement et conclusion, chiffré au repos et déverrouillé fiche par fiche). Les noms et les images ont leur propre porte : un titre révélateur est remplacé par un alias neutre (« Mission secondaire — Port Gellhorn »).

**Filtrage** : une vue SQL `visible_*` est paramétrée par le profil de progression. La recherche FTS, la recherche vectorielle, l'API, les notifications et l'IA lisent **uniquement** ces vues. Le modèle IA ne reçoit jamais une donnée non autorisée. Des tests automatisés (« canaris » : fausses entrées spoilers) vérifient qu'aucune route ne les laisse passer.

---

## 4. Assistant IA

1. **Routeur d'intention** (petit modèle ou règles) : question factuelle structurée, exploration, comparaison ou conversation libre.
2. **Outils déterministes** appelés par le modèle (tool calling Ollama) : `rechercher_vehicules(filtres)`, `comparer(ids, pondérations)`, `activites_autour(région|point)`, `fiche(id, niveau)`, `nouveautes(période)`, `ouvrir_ui(écran, filtres)`. **Les calculs, classements et coordonnées viennent du SQL, jamais du modèle.**
3. **RAG** sur les vues filtrées uniquement, avec citation de la source pour chaque fait.
4. **Réponse riche** : JSON de composants (`fiche`, `tableau`, `graphique`, `marqueur_carte`, `action_ui`) rendus par l'application.
5. **Mémoire de session** : région actuelle, véhicule recherché, préférences, historique. Stockée localement.
6. **Garde-fous** : le contenu web est encapsulé comme donnée, jamais comme instruction. Statuts « théorie / à vérifier » affichés. Le modèle répond « je ne sais pas » quand l'outil ne renvoie rien.

---

## 5. Collecte quotidienne (Phase 6, selon les autorisations)

Les 15 étapes demandées sont implémentées comme un pipeline :
`fetch (ETag/If-Modified-Since, sitemap diff) → extract → traduire (Ollama) → normaliser → dédoublonner → recouper → fiabilité → spoiler (classification IA + règles ; doute ⇒ quarantaine) → valider → publier → delta vers mobile → rapport`.
- Une source en panne ne bloque que son connecteur. Aucune donnée validée n'est supprimée.
- Une valeur vérifiée n'est jamais remplacée par une valeur moins fiable.
- Une file de quarantaine est consultable dans l'application, avec validation en un geste.

---

## 6. Plan de réalisation

| Phase | Contenu | Critère de « terminé » (testé) |
|---|---|---|
| **2b** (prochaine) | Squelette du monorepo, schéma SQL + migrations, moteur anti-spoiler + tests canaris, envoi des demandes d'autorisation | Tests anti-spoiler verts. Schéma variantes/kits validé avec vous. |
| **3** Prototype | Carte MapLibre (fond CC BY 4.0), fiches, catalogue véhicules + variantes + filtres + comparateur pondéré, profil de progression, garage virtuel, premières données saisies et sourcées | Utilisable sur PC et APK de test sur le Pixel, hors ligne. |
| **4** IA | Ollama, outils structurés, RAG, mémoire, pilotage de l'interface | Jeu de questions de référence (dont vos 11 exemples) sans hallucination ni spoiler. |
| **5** Encyclopédie | Armes + variantes + accessoires, missions scindées, secrets, mystères, théories | Couverture mesurée par rapport aux sources. |
| **6** Autonomie | Connecteurs, planificateur, quarantaine, rapports, rollback | 7 jours de collecte sans intervention. |
| **7** Finition | UX à une main, performances, sauvegardes, sécurité Tailscale | Audit final, y compris spoilers. |

---

## 7. Décisions à prendre

1. **Autorisations** : OK pour que je rédige les demandes aux trois sites (vous les envoyez) ?
2. **Emplacement du code** : dossier `gta6-companion/` dans ce dépôt (actuellement un launcher Android), ou un dépôt dédié (recommandé) ?
3. **Réseau** : autoriser `map.gtadb.org` pour vérifier la licence et les données de GTA VI Landmarks.
