-- Fiches de référence hors carte (codes de triche, trophées, défis) : une ligne par fiche,
-- provenance conservée, drapeau spoiler de la source respecté.
CREATE TABLE reference_item (
    id         TEXT PRIMARY KEY,            -- '<kind>:<slug>'
    kind       TEXT NOT NULL CHECK (kind IN ('cheat','trophy','challenge')),
    name       TEXT NOT NULL,
    data_json  TEXT NOT NULL,
    spoiler    INTEGER NOT NULL DEFAULT 0,
    source_id  TEXT NOT NULL REFERENCES source(id),
    source_url TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE reference_done (id TEXT PRIMARY KEY REFERENCES reference_item(id));
