-- GTA VI Companion — schéma initial.
-- Principe anti-spoiler : toute donnée est MASQUÉE tant qu'elle n'a pas été
-- évaluée ('unknown' par défaut) ET que toutes ses portes de progression ne
-- sont pas satisfaites. L'application, la recherche et l'IA ne lisent QUE les
-- vues visible_* définies en fin de fichier.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------- sources
CREATE TABLE source (
    id          TEXT PRIMARY KEY,                 -- 'gtabase', 'gta6map', 'gtacity', 'manual'
    name        TEXT NOT NULL,
    base_url    TEXT,
    policy      TEXT NOT NULL CHECK (policy IN ('full_sync','on_demand','links_only','disabled')),
    reliability INTEGER NOT NULL DEFAULT 50 CHECK (reliability BETWEEN 0 AND 100)
);

-- ---------------------------------------------------------------- entités
-- Identifiant stable et lisible : 'vehicle:grotti-cheetah-95:preziosa'.
CREATE TABLE entity (
    id             TEXT PRIMARY KEY,
    kind           TEXT NOT NULL CHECK (kind IN (
                     'vehicle_model','vehicle_variant','weapon_model','weapon_variant',
                     'mod_option','kit','location','mission','side_mission','secret_quest',
                     'random_encounter','dynamic_event','easter_egg','mystery','theory',
                     'activity','collectible','property','character','region')),
    canonical_name TEXT NOT NULL,
    neutral_alias  TEXT,                          -- nom affiché si le vrai nom est un spoiler
    spoiler_status TEXT NOT NULL DEFAULT 'unknown' CHECK (spoiler_status IN ('evaluated','unknown')),
    missable       INTEGER NOT NULL DEFAULT 0,    -- avertir sans expliquer pourquoi
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Une porte = une condition de progression. Plusieurs portes = ET logique.
-- field NULL : protège l'entité entière. Sinon protège un champ précis :
--   'name', 'media:<id>', 'content:<level>', ou le nom d'un champ de claim.
CREATE TABLE spoiler_gate (
    id        INTEGER PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
    field     TEXT,
    kind      TEXT NOT NULL CHECK (kind IN ('chapter','mission','character','region')),
    ref       TEXT,                                -- entity_id de la mission/perso/région
    chapter   INTEGER,                             -- pour kind='chapter'
    CHECK ((kind = 'chapter' AND chapter IS NOT NULL) OR (kind <> 'chapter' AND ref IS NOT NULL))
);
CREATE INDEX idx_gate_entity ON spoiler_gate(entity_id, field);

-- ---------------------------------------------------------------- affirmations sourcées
-- Chaque valeur est une affirmation traçable. Les contradictions coexistent.
CREATE TABLE claim (
    id             INTEGER PRIMARY KEY,
    entity_id      TEXT NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
    field          TEXT NOT NULL,                  -- 'top_speed', 'drivetrain', 'price'…
    value_json     TEXT NOT NULL,
    value_kind     TEXT NOT NULL CHECK (value_kind IN ('official','community','subjective')),
    source_id      TEXT NOT NULL REFERENCES source(id),
    source_url     TEXT,
    observed_at    TEXT NOT NULL DEFAULT (datetime('now')),
    status         TEXT NOT NULL DEFAULT 'to_verify' CHECK (status IN (
                     'confirmed','probable','to_verify','theory','contradicted','obsolete')),
    spoiler_status TEXT NOT NULL DEFAULT 'unknown' CHECK (spoiler_status IN ('evaluated','unknown'))
);
CREATE INDEX idx_claim_entity ON claim(entity_id, field);

-- ---------------------------------------------------------------- véhicules / armes + variantes
CREATE TABLE vehicle_model (
    entity_id    TEXT PRIMARY KEY REFERENCES entity(id) ON DELETE CASCADE,
    manufacturer TEXT,
    class        TEXT                              -- 'super','sports','muscle','off_road'…
);
CREATE TABLE vehicle_variant (
    entity_id    TEXT PRIMARY KEY REFERENCES entity(id) ON DELETE CASCADE,
    model_id     TEXT NOT NULL REFERENCES vehicle_model(entity_id),
    variant_type TEXT NOT NULL CHECK (variant_type IN
                   ('standard','named','unique','police','edition','secret'))
);
CREATE TABLE weapon_model (
    entity_id    TEXT PRIMARY KEY REFERENCES entity(id) ON DELETE CASCADE,
    manufacturer TEXT,
    class        TEXT                              -- 'handgun','smg','melee','equipment'…
);
CREATE TABLE weapon_variant (
    entity_id    TEXT PRIMARY KEY REFERENCES entity(id) ON DELETE CASCADE,
    model_id     TEXT NOT NULL REFERENCES weapon_model(entity_id),
    variant_type TEXT NOT NULL CHECK (variant_type IN
                   ('standard','named','unique','edition','secret','finish'))
);

-- Personnalisation : catégories -> options ; kits = ensembles nommés d'options.
CREATE TABLE mod_category (
    id         TEXT PRIMARY KEY,                   -- 'vehicle:bodykit', 'weapon:scope'…
    applies_to TEXT NOT NULL CHECK (applies_to IN ('vehicle','weapon')),
    name_fr    TEXT NOT NULL
);
CREATE TABLE mod_option (
    entity_id   TEXT PRIMARY KEY REFERENCES entity(id) ON DELETE CASCADE,
    category_id TEXT NOT NULL REFERENCES mod_category(id)
);
CREATE TABLE variant_mod (                         -- compatibilité variante <-> option
    variant_id TEXT NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
    option_id  TEXT NOT NULL REFERENCES mod_option(entity_id) ON DELETE CASCADE,
    PRIMARY KEY (variant_id, option_id)
);
CREATE TABLE kit (
    entity_id  TEXT PRIMARY KEY REFERENCES entity(id) ON DELETE CASCADE,
    variant_id TEXT NOT NULL REFERENCES entity(id) ON DELETE CASCADE
);
CREATE TABLE kit_option (
    kit_id    TEXT NOT NULL REFERENCES kit(entity_id) ON DELETE CASCADE,
    option_id TEXT NOT NULL REFERENCES mod_option(entity_id) ON DELETE CASCADE,
    PRIMARY KEY (kit_id, option_id)
);

-- ---------------------------------------------------------------- contenus d'activité
-- Séparation physique : niveau 1 = commencer, 2 = indices, 3 = solution.
CREATE TABLE activity_content (
    id             INTEGER PRIMARY KEY,
    entity_id      TEXT NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
    level          INTEGER NOT NULL CHECK (level IN (1,2,3)),
    ord            INTEGER NOT NULL DEFAULT 0,
    body           TEXT NOT NULL,
    spoiler_status TEXT NOT NULL DEFAULT 'unknown' CHECK (spoiler_status IN ('evaluated','unknown'))
);

CREATE TABLE media (
    id             INTEGER PRIMARY KEY,
    entity_id      TEXT NOT NULL REFERENCES entity(id) ON DELETE CASCADE,
    url            TEXT NOT NULL,
    source_id      TEXT REFERENCES source(id),
    spoiler_status TEXT NOT NULL DEFAULT 'unknown' CHECK (spoiler_status IN ('evaluated','unknown'))
);

CREATE TABLE location_point (
    entity_id TEXT PRIMARY KEY REFERENCES entity(id) ON DELETE CASCADE,
    region_id TEXT REFERENCES entity(id),
    x REAL NOT NULL, y REAL NOT NULL,
    precision TEXT NOT NULL DEFAULT 'unknown' CHECK (precision IN ('exact','nearby','zone','unknown'))
);

-- ---------------------------------------------------------------- progression du joueur
CREATE TABLE progress_state (
    id      INTEGER PRIMARY KEY CHECK (id = 1),
    chapter INTEGER NOT NULL DEFAULT 0
);
INSERT INTO progress_state (id, chapter) VALUES (1, 0);
CREATE TABLE progress_mission   (entity_id TEXT PRIMARY KEY REFERENCES entity(id));
CREATE TABLE progress_character (entity_id TEXT PRIMARY KEY REFERENCES entity(id));
CREATE TABLE progress_region    (entity_id TEXT PRIMARY KEY REFERENCES entity(id));

-- Déverrouillages explicites, PAR CONTENU (jamais globaux).
CREATE TABLE hint_reveal     (entity_id TEXT PRIMARY KEY REFERENCES entity(id), upto_ord INTEGER NOT NULL);
CREATE TABLE solution_unlock (entity_id TEXT PRIMARY KEY REFERENCES entity(id),
                              unlocked_at TEXT NOT NULL DEFAULT (datetime('now')));

CREATE TABLE user_item_status (
    entity_id TEXT PRIMARY KEY REFERENCES entity(id),
    status    TEXT NOT NULL CHECK (status IN ('to_discover','discovered','done','favorite',
                                              'owned','wanted','lost'))
);

-- ---------------------------------------------------------------- historique
CREATE TABLE revision (
    id         INTEGER PRIMARY KEY,
    table_name TEXT NOT NULL,
    row_key    TEXT NOT NULL,
    before_json TEXT,
    after_json  TEXT,
    changed_at TEXT NOT NULL DEFAULT (datetime('now')),
    origin     TEXT NOT NULL                       -- 'sync:gtabase', 'manual'…
);

-- ================================================================ VUES DE VISIBILITÉ
-- gate_ok : 1 si la porte est satisfaite par la progression actuelle.
CREATE VIEW gate_state AS
SELECT g.id, g.entity_id, g.field,
       CASE g.kind
         WHEN 'chapter'   THEN (SELECT chapter FROM progress_state WHERE id = 1) >= g.chapter
         WHEN 'mission'   THEN EXISTS (SELECT 1 FROM progress_mission   m WHERE m.entity_id = g.ref)
         WHEN 'character' THEN EXISTS (SELECT 1 FROM progress_character c WHERE c.entity_id = g.ref)
         WHEN 'region'    THEN EXISTS (SELECT 1 FROM progress_region    r WHERE r.entity_id = g.ref)
       END AS ok
FROM spoiler_gate g;

-- Entités visibles : évaluées ET aucune porte d'entité non satisfaite.
CREATE VIEW visible_entity AS
SELECT e.id, e.kind, e.missable,
       CASE WHEN EXISTS (SELECT 1 FROM gate_state s
                         WHERE s.entity_id = e.id AND s.field = 'name' AND NOT s.ok)
            THEN COALESCE(e.neutral_alias, 'Contenu non découvert')
            ELSE e.canonical_name END AS display_name
FROM entity e
WHERE e.spoiler_status = 'evaluated'
  AND NOT EXISTS (SELECT 1 FROM gate_state s
                  WHERE s.entity_id = e.id AND s.field IS NULL AND NOT s.ok);

CREATE VIEW visible_claim AS
SELECT c.* FROM claim c
JOIN visible_entity v ON v.id = c.entity_id
WHERE c.spoiler_status = 'evaluated'
  AND NOT EXISTS (SELECT 1 FROM gate_state s
                  WHERE s.entity_id = c.entity_id AND s.field = c.field AND NOT s.ok);

CREATE VIEW visible_media AS
SELECT m.* FROM media m
JOIN visible_entity v ON v.id = m.entity_id
WHERE m.spoiler_status = 'evaluated'
  AND NOT EXISTS (SELECT 1 FROM gate_state s
                  WHERE s.entity_id = m.entity_id AND s.field = 'media:' || m.id AND NOT s.ok);

-- Niveau 1 : toujours (si visible). Niveau 2 : seulement les indices demandés.
-- Niveau 3 : seulement si la solution de CE contenu a été déverrouillée.
CREATE VIEW visible_activity_content AS
SELECT a.* FROM activity_content a
JOIN visible_entity v ON v.id = a.entity_id
WHERE a.spoiler_status = 'evaluated'
  AND NOT EXISTS (SELECT 1 FROM gate_state s
                  WHERE s.entity_id = a.entity_id AND s.field = 'content:' || a.level AND NOT s.ok)
  AND (   a.level = 1
       OR (a.level = 2 AND a.ord <= COALESCE((SELECT upto_ord FROM hint_reveal h
                                              WHERE h.entity_id = a.entity_id), -1))
       OR (a.level = 3 AND EXISTS (SELECT 1 FROM solution_unlock u WHERE u.entity_id = a.entity_id)));

CREATE VIEW visible_location AS
SELECT p.* FROM location_point p
JOIN visible_entity v ON v.id = p.entity_id
WHERE NOT EXISTS (SELECT 1 FROM gate_state s
                  WHERE s.entity_id = p.entity_id AND s.field = 'location' AND NOT s.ok);

-- ================================================================ RECHERCHE
-- L'index ne contient que des textes étiquetés (entité, champ). La recherche
-- passe TOUJOURS par visible_search, qui recoupe avec les vues ci-dessus.
CREATE VIRTUAL TABLE search_fts USING fts5(
    body, entity_id UNINDEXED, field UNINDEXED, ref_id UNINDEXED,
    tokenize = 'unicode61 remove_diacritics 2'
);
-- field : 'name' (ref_id NULL) | 'content' (ref_id = activity_content.id) | 'claim' (ref_id = claim.id)
CREATE VIEW visible_search AS
SELECT f.rowid AS rowid, f.entity_id, f.field, f.ref_id, f.body
FROM search_fts f
JOIN visible_entity v ON v.id = f.entity_id
WHERE (f.field = 'name' AND NOT EXISTS (SELECT 1 FROM gate_state s
                                        WHERE s.entity_id = f.entity_id AND s.field = 'name' AND NOT s.ok))
   OR (f.field = 'content' AND f.ref_id IN (SELECT id FROM visible_activity_content))
   OR (f.field = 'claim'   AND f.ref_id IN (SELECT id FROM visible_claim));
