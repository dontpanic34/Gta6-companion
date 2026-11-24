-- Le nom d'une entité a son propre statut : une fiche peut être visible
-- (ex. « Variante unique — Tempesta ») sans révéler son vrai titre.
ALTER TABLE entity ADD COLUMN name_status TEXT NOT NULL DEFAULT 'unknown'
    CHECK (name_status IN ('safe','unknown'));
UPDATE entity SET name_status = 'safe' WHERE spoiler_status = 'evaluated';

-- Révélation explicite du titre, par contenu (jamais globale).
CREATE TABLE name_reveal (entity_id TEXT PRIMARY KEY REFERENCES entity(id));

-- Métadonnées de fiabilité pour lieux et secrets
ALTER TABLE entity ADD COLUMN region_label TEXT;
ALTER TABLE entity ADD COLUMN category TEXT;
ALTER TABLE entity ADD COLUMN reliability TEXT NOT NULL DEFAULT 'to_verify'
    CHECK (reliability IN ('confirmed','probable','to_verify','theory','contradicted','obsolete'));

DROP VIEW visible_entity;
CREATE VIEW visible_entity AS
SELECT e.id, e.kind, e.missable, e.category, e.region_label, e.reliability,
       CASE WHEN EXISTS (SELECT 1 FROM name_reveal r WHERE r.entity_id = e.id)
                 AND NOT EXISTS (SELECT 1 FROM gate_state s
                                 WHERE s.entity_id = e.id AND s.field = 'name' AND NOT s.ok)
              THEN e.canonical_name
            WHEN e.name_status = 'safe'
                 AND NOT EXISTS (SELECT 1 FROM gate_state s
                                 WHERE s.entity_id = e.id AND s.field = 'name' AND NOT s.ok)
              THEN e.canonical_name
            ELSE COALESCE(e.neutral_alias, 'Contenu non découvert') END AS display_name,
       CASE WHEN e.name_status = 'safe' OR EXISTS (SELECT 1 FROM name_reveal r WHERE r.entity_id = e.id)
            THEN NOT EXISTS (SELECT 1 FROM gate_state s
                             WHERE s.entity_id = e.id AND s.field = 'name' AND NOT s.ok)
            ELSE 0 END AS name_visible
FROM entity e
WHERE e.spoiler_status = 'evaluated'
  AND NOT EXISTS (SELECT 1 FROM gate_state s
                  WHERE s.entity_id = e.id AND s.field IS NULL AND NOT s.ok);

DROP VIEW visible_search;
CREATE VIEW visible_search AS
SELECT f.rowid AS rowid, f.entity_id, f.field, f.ref_id, f.body
FROM search_fts f
JOIN visible_entity v ON v.id = f.entity_id
WHERE (f.field = 'name'    AND v.name_visible)
   OR (f.field = 'alias')
   OR (f.field = 'content' AND f.ref_id IN (SELECT id FROM visible_activity_content))
   OR (f.field = 'claim'   AND f.ref_id IN (SELECT id FROM visible_claim));
