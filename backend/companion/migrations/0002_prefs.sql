-- Préférences utilisateur (style de conduite, pondérations du comparateur…)
CREATE TABLE user_pref (
    key        TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Profil de conduite par défaut : compactes agiles, accélération, adhérence,
-- polyvalence route/hors route, pas de muscle cars ni de drift systématique.
INSERT INTO user_pref(key, value_json) VALUES
 ('vehicle_weights', '{"acceleration":0.30,"handling_road":0.25,"handling_offroad":0.20,"speed":0.15,"strength":0.10}'),
 ('vehicle_exclude_classes', '["Muscle"]'),
 ('vehicle_favorites_style', '"Sportives japonaises compactes (ex. Karin Futo)"');
