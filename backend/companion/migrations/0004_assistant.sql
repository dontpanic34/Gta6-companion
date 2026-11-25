-- Mémoire de session de l'assistant (zone actuelle, derniers résultats, véhicule recherché…)
CREATE TABLE assistant_session (
    id         TEXT PRIMARY KEY,
    state_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Succès Xbox (OpenXBL). Le nom/la description d'un succès non débloqué peut
-- être un spoiler : affichés seulement si débloqué ou explicitement jugé sûr.
CREATE TABLE xbox_achievement (
    id            TEXT PRIMARY KEY,
    title_id      TEXT NOT NULL,
    name          TEXT NOT NULL,
    description   TEXT,
    unlocked      INTEGER NOT NULL DEFAULT 0,
    unlocked_at   TEXT,
    name_safe     INTEGER NOT NULL DEFAULT 0,
    -- effet sur la progression quand le succès est débloqué (ex. {"chapter": 3})
    progress_json TEXT,
    synced_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
