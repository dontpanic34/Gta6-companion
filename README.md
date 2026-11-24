# GTA VI Companion (« Leonida Companion »)

Application compagnon **personnelle** pour GTA VI, sur PC et Android, en français. Elle est conçue autour de la protection anti-spoiler.

## Contenu du dépôt

| Dossier | Rôle |
|---|---|
| `docs/` | Audit des sources, architecture, plan, message GTACity |
| `backend/companion/` | Base SQLite (migrations), moteur anti-spoiler, connecteurs, API FastAPI, synchro, sauvegardes |
| `backend/tests/` | Tests (anti-spoiler avec « canaris », connecteurs, catalogue, API, sauvegardes) |
| `web/` | Interface React + TypeScript (Vite), projet Android Capacitor dans `web/android/` |
| `scripts/windows/` | Installation, tâche quotidienne, serveur au démarrage |

## Installation sur le PC Windows

Prérequis : Python 3.11+, Node 20+, Git, Tailscale.

```powershell
cd scripts\windows
.\install.ps1          # venv, dépendances, tests, build web, jeton d'accès
.\register-tasks.ps1   # synchro quotidienne 04:17 + serveur au démarrage
.\daily.ps1            # première synchro immédiate (~45 min, polie : 1 requête / 3 s)
```

L'interface est alors accessible sur `http://<IP-Tailscale-du-PC>:8765`. Elle n'est **pas** exposée sur Internet : seuls vos appareils Tailscale peuvent y accéder, avec un jeton obligatoire.

## Application Android (Pixel)

```bash
cd web && npm run build && npx cap sync android && npx cap open android   # puis Run dans Android Studio
```

Dans l'application : **Réglages → Connexion au PC**, avec l'adresse Tailscale du PC et le jeton.
*(La consultation hors ligne, avec une copie locale de la base sur le téléphone, est prévue en phase 7.)*

## Sources et politique de collecte

| Source | Méthode | Notes |
|---|---|---|
| GTABase | Synchro complète quotidienne (sitemap + cache conditionnel) | Véhicules, armes, variantes, stats |
| GTA6Map.city | Pages publiques uniquement (lieux, secrets) | `/data/` et `/tiles/` jamais touchés (robots.txt) |
| GTACity | À la demande, en attente de leur réponse (voir `docs/message-gtacity.md`) | — |
| GTA VI Landmarks | Fond de carte CC BY 4.0 (à intégrer) | — |

Le client HTTP vérifie le robots.txt avant chaque requête, limite le débit et réessaie en cas d'erreur réseau. Une source en panne ne bloque pas les autres, et aucune donnée n'est jamais supprimée.

## Anti-spoiler (résumé)

- Le filtrage se fait **dans la base** (vues `visible_*`). La recherche, l'API et la future IA ne lisent que ces vues.
- Une donnée non évaluée est **masquée par défaut**. Les textes narratifs sont mis en **quarantaine** par des règles.
- Les titres révélateurs sont remplacés par un nom neutre (« Créatures et rencontres — Mariana County »).
- Les niveaux : 1 = commencer, 2 = indices un par un, 3 = solution après confirmation. Chaque révélation ne vaut que pour ce contenu.

## Tests

```bash
cd backend && python -m pytest -q
```
