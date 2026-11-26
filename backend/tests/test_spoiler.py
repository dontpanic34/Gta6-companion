"""Tests anti-spoiler avec des « canaris » : de faux contenus révélateurs
contenant le mot CANARI. Aucune lecture publique ne doit jamais les exposer
tant que la progression ne l'autorise pas."""
import json

import pytest

from companion import db, spoiler
from companion.spoiler import Progress

CANARY = "CANARI"


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    c.executescript("""
    INSERT INTO source VALUES ('manual','Saisie manuelle',NULL,'full_sync',90);

    -- Région + mission de référence pour les portes
    INSERT INTO entity(id,kind,canonical_name,spoiler_status) VALUES
      ('region:port-gellhorn','region','Port Gellhorn','evaluated'),
      ('mission:ch2-finale','mission','Mission finale chapitre 2','evaluated'),
      ('character:inconnu','character','Personnage CANARI secret','evaluated');
    INSERT INTO spoiler_gate(entity_id,field,kind,ref) VALUES
      ('character:inconnu',NULL,'character','character:inconnu');

    -- Quête secrète : nom révélateur protégé, contenu en 3 niveaux
    INSERT INTO entity(id,kind,canonical_name,neutral_alias,spoiler_status,missable) VALUES
      ('quest:q1','secret_quest','La trahison CANARI','Quête secrète — Port Gellhorn','evaluated',1);
    INSERT INTO spoiler_gate(entity_id,field,kind,ref) VALUES
      ('quest:q1','name','mission','mission:ch2-finale');
    INSERT INTO activity_content(entity_id,level,ord,body,spoiler_status) VALUES
      ('quest:q1',1,0,'Commencer au phare, la nuit entre 22h et 4h.','evaluated'),
      ('quest:q1',2,0,'Indice 1 : regardez le phare.','evaluated'),
      ('quest:q1',2,1,'Indice 2 : CANARI indice avancé.','evaluated'),
      ('quest:q1',3,0,'Solution : CANARI dénouement.','evaluated'),
      ('quest:q1',1,1,'Texte non évalué CANARI.','unknown');

    -- Entité jamais évaluée : invisible par défaut
    INSERT INTO entity(id,kind,canonical_name) VALUES ('easter:x','easter_egg','Secret CANARI non évalué');

    -- Entité gardée par chapitre
    INSERT INTO entity(id,kind,canonical_name,spoiler_status) VALUES
      ('location:late','location','Lieu CANARI chapitre 5','evaluated');
    INSERT INTO spoiler_gate(entity_id,field,kind,chapter) VALUES ('location:late',NULL,'chapter',5);

    -- Véhicule : une stat protégée (la récompense révèle un événement), image protégée
    INSERT INTO entity(id,kind,canonical_name,spoiler_status) VALUES
      ('vehicle:karin-futo','vehicle_model','Karin Futo','evaluated'),
      ('vehicle:karin-futo:std','vehicle_variant','Karin Futo','evaluated');
    INSERT INTO vehicle_model VALUES ('vehicle:karin-futo','Karin','sports');
    INSERT INTO vehicle_variant VALUES ('vehicle:karin-futo:std','vehicle:karin-futo','standard');
    """)
    c.execute("INSERT INTO claim(entity_id,field,value_json,value_kind,source_id,status,spoiler_status) "
              "VALUES ('vehicle:karin-futo:std','drivetrain',?, 'official','manual','confirmed','evaluated')",
              (json.dumps("RWD"),))
    c.execute("INSERT INTO claim(entity_id,field,value_json,value_kind,source_id,status,spoiler_status) "
              "VALUES ('vehicle:karin-futo:std','unlock',?, 'official','manual','confirmed','evaluated')",
              (json.dumps("Récompense CANARI après la mort de X"),))
    c.execute("INSERT INTO claim(entity_id,field,value_json,value_kind,source_id,spoiler_status) "
              "VALUES ('vehicle:karin-futo:std','note',?, 'subjective','manual','unknown')",
              (json.dumps("note CANARI non évaluée"),))
    c.execute("INSERT INTO spoiler_gate(entity_id,field,kind,ref) VALUES "
              "('vehicle:karin-futo:std','unlock','mission','mission:ch2-finale')")
    c.execute("INSERT INTO media(id,entity_id,url,spoiler_status) VALUES "
              "(1,'vehicle:karin-futo:std','https://img/futo.jpg','evaluated'),"
              "(2,'vehicle:karin-futo:std','https://img/CANARI.jpg','evaluated')")
    c.execute("INSERT INTO spoiler_gate(entity_id,field,kind,chapter) VALUES "
              "('vehicle:karin-futo:std','media:2','chapter',4)")
    c.execute("UPDATE entity SET name_status='safe' WHERE spoiler_status='evaluated'")
    c.commit()
    spoiler.reindex(c)
    return c


def everything_public(c) -> str:
    """Concatène TOUT ce qu'une lecture publique peut exposer."""
    out = [json.dumps(spoiler.list_visible(c), ensure_ascii=False)]
    for e in spoiler.list_visible(c):
        out.append(json.dumps(spoiler.get_entity(c, e["id"]), ensure_ascii=False))
    for q in ["canari", "trahison", "secret", "phare", "récompense", "lieu", "futo", "note", "solution"]:
        out.append(json.dumps(spoiler.search(c, q), ensure_ascii=False))
    return "\n".join(out)


def test_new_player_sees_no_canary(conn):
    assert CANARY not in everything_public(conn)


def test_unknown_status_hidden_by_default(conn):
    assert spoiler.get_entity(conn, "easter:x") is None
    spoiler.set_progress(conn, Progress(chapter=99, completed_missions={"mission:ch2-finale"},
                                        met_characters={"character:inconnu"}))
    # même avec une progression maximale, une entité non évaluée reste masquée
    assert spoiler.get_entity(conn, "easter:x") is None
    futo = spoiler.get_entity(conn, "vehicle:karin-futo:std")
    assert all(c["field"] != "note" for c in futo["claims"])


def test_level1_shows_start_only_with_neutral_name(conn):
    q = spoiler.get_entity(conn, "quest:q1")
    assert q["name"] == "Quête secrète — Port Gellhorn"
    assert [c["body"] for c in q["content"]] == ["Commencer au phare, la nuit entre 22h et 4h."]
    assert q["hints_remaining"] == 2
    assert q["missable_warning"] is True


def test_hints_are_progressive_and_local(conn):
    spoiler.reveal_next_hint(conn, "quest:q1")
    bodies = [c["body"] for c in spoiler.get_entity(conn, "quest:q1")["content"]]
    assert "Indice 1 : regardez le phare." in bodies
    assert not any(CANARY in b for b in bodies)
    spoiler.reveal_next_hint(conn, "quest:q1")
    bodies = [c["body"] for c in spoiler.get_entity(conn, "quest:q1")["content"]]
    assert any("Indice 2" in b for b in bodies)
    assert not any("Solution" in b for b in bodies)


def test_solution_requires_confirmation_and_is_per_content(conn):
    with pytest.raises(PermissionError):
        spoiler.unlock_solution(conn, "quest:q1", confirmed=False)
    spoiler.unlock_solution(conn, "quest:q1", confirmed=True)
    bodies = [c["body"] for c in spoiler.get_entity(conn, "quest:q1")["content"]]
    assert "Solution : CANARI dénouement." in bodies
    # Les autres contenus restent protégés
    assert spoiler.get_entity(conn, "location:late") is None
    assert spoiler.get_entity(conn, "character:inconnu") is None
    # Le texte non évalué reste masqué même après déverrouillage
    assert "Texte non évalué CANARI." not in bodies


def test_field_and_media_gates(conn):
    futo = spoiler.get_entity(conn, "vehicle:karin-futo:std")
    assert {c["field"] for c in futo["claims"]} == {"drivetrain"}
    assert futo["media"] == ["https://img/futo.jpg"]
    spoiler.set_progress(conn, Progress(chapter=4, completed_missions={"mission:ch2-finale"}))
    futo = spoiler.get_entity(conn, "vehicle:karin-futo:std")
    assert {c["field"] for c in futo["claims"]} == {"drivetrain", "unlock"}
    assert len(futo["media"]) == 2


def test_progress_unlocks_name_and_chapter_content(conn):
    spoiler.set_progress(conn, Progress(chapter=5, completed_missions={"mission:ch2-finale"}))
    assert spoiler.get_entity(conn, "quest:q1")["name"] == "La trahison CANARI"
    assert spoiler.get_entity(conn, "location:late") is not None
    assert any(r["entity_id"] == "quest:q1" for r in spoiler.search(conn, "trahison"))


def test_search_never_leaks_hidden_text(conn):
    assert spoiler.search(conn, "dénouement") == []
    assert spoiler.search(conn, "trahison") == []
    assert spoiler.search(conn, "chapitre 5") == []
    assert [r["entity_id"] for r in spoiler.search(conn, "phare")] == ["quest:q1"]


def test_migrations_idempotent(conn):
    assert db.migrate(conn) == db.migrate(conn) == 7


def test_unsafe_name_shows_alias_until_explicit_reveal(conn):
    conn.execute("INSERT INTO entity(id,kind,canonical_name,neutral_alias,spoiler_status,name_status) VALUES "
                 "('secret:s1','secret_quest','Quête CANARI qui finit par un fusil','Secret — Mariana County','evaluated','unknown')")
    conn.commit(); spoiler.reindex(conn)
    e = spoiler.get_entity(conn, "secret:s1")
    assert e["name"] == "Secret — Mariana County" and e["name_hidden"]
    assert CANARY not in everything_public(conn)
    assert [r["entity_id"] for r in spoiler.search(conn, "Mariana")] == ["secret:s1"]
    with pytest.raises(PermissionError):
        spoiler.reveal_name(conn, "secret:s1", confirmed=False)
    spoiler.reveal_name(conn, "secret:s1", confirmed=True)
    assert spoiler.get_entity(conn, "secret:s1")["name"].startswith("Quête CANARI")
    # la révélation ne vaut que pour ce contenu
    assert spoiler.get_entity(conn, "quest:q1")["name"] == "Quête secrète — Port Gellhorn"
