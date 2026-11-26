-- GTABase bloque l'affichage de ses images dans une autre appli (protection anti-hotlink) :
-- on ne les affiche plus. Photos prises chez les sources qui l'autorisent (GTA Wiki, GTACity).
DROP VIEW visible_media;
CREATE VIEW visible_media AS
SELECT m.* FROM media m
JOIN visible_entity v ON v.id = m.entity_id
WHERE m.spoiler_status = 'evaluated'
  AND COALESCE(m.source_id, '') <> 'gtabase'
  AND NOT EXISTS (SELECT 1 FROM gate_state s
                  WHERE s.entity_id = m.entity_id AND s.field = 'media:' || m.id AND NOT s.ok);
