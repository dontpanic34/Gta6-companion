"""Couche d'accès protégée contre les spoilers.

Toute lecture destinée à l'utilisateur (UI, recherche, notifications, IA)
DOIT passer par ce module, qui ne lit que les vues visible_* de la base.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field


@dataclass
class Progress:
    chapter: int = 0
    completed_missions: set[str] = field(default_factory=set)
    met_characters: set[str] = field(default_factory=set)
    discovered_regions: set[str] = field(default_factory=set)


def set_progress(conn: sqlite3.Connection, p: Progress) -> None:
    with conn:
        conn.execute("UPDATE progress_state SET chapter = ? WHERE id = 1", (p.chapter,))
        for table, ids in (("progress_mission", p.completed_missions),
                           ("progress_character", p.met_characters),
                           ("progress_region", p.discovered_regions)):
            conn.execute(f"DELETE FROM {table}")
            conn.executemany(f"INSERT INTO {table}(entity_id) VALUES (?)", [(i,) for i in ids])


def reveal_next_hint(conn: sqlite3.Connection, entity_id: str) -> None:
    """Niveau 2 : révèle UN indice de plus, uniquement pour ce contenu."""
    with conn:
        conn.execute("""INSERT INTO hint_reveal(entity_id, upto_ord) VALUES (?, 0)
                        ON CONFLICT(entity_id) DO UPDATE SET upto_ord = upto_ord + 1""", (entity_id,))


def unlock_solution(conn: sqlite3.Connection, entity_id: str, *, confirmed: bool) -> None:
    """Niveau 3 : exige une confirmation explicite, et ne vaut que pour ce contenu."""
    if not confirmed:
        raise PermissionError("Confirmation explicite requise pour afficher la solution.")
    with conn:
        conn.execute("INSERT OR IGNORE INTO solution_unlock(entity_id) VALUES (?)", (entity_id,))


def reveal_name(conn: sqlite3.Connection, entity_id: str, *, confirmed: bool) -> None:
    """Révèle le vrai titre d'UN contenu (les portes de progression restent actives)."""
    if not confirmed:
        raise PermissionError("Confirmation explicite requise pour révéler le titre.")
    with conn:
        conn.execute("INSERT OR IGNORE INTO name_reveal(entity_id) VALUES (?)", (entity_id,))


def get_entity(conn: sqlite3.Connection, entity_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM visible_entity WHERE id = ?", (entity_id,)).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "kind": row["kind"],
        "name": row["display_name"],
        "name_hidden": not row["name_visible"],
        "category": row["category"],
        "region": row["region_label"],
        "reliability": row["reliability"],
        "missable_warning": bool(row["missable"]),
        "claims": [dict(r) for r in conn.execute(
            "SELECT field, value_json, value_kind, source_id, source_url, status, observed_at "
            "FROM visible_claim WHERE entity_id = ? AND (field <> 'video' OR EXISTS "
            "(SELECT 1 FROM solution_unlock u WHERE u.entity_id = ?)) ORDER BY field", (entity_id, entity_id))],
        "content": [dict(r) for r in conn.execute(
            "SELECT level, ord, body FROM visible_activity_content WHERE entity_id = ? "
            "ORDER BY level, ord", (entity_id,))],
        "media": [r["url"] for r in conn.execute(
            "SELECT url FROM visible_media WHERE entity_id = ?", (entity_id,))],
        "hints_remaining": conn.execute(
            "SELECT COUNT(*) FROM activity_content a WHERE a.entity_id = ? AND a.level = 2 "
            "AND a.id NOT IN (SELECT id FROM visible_activity_content)", (entity_id,)).fetchone()[0],
    }


def list_visible(conn: sqlite3.Connection, kind: str | None = None) -> list[dict]:
    sql = "SELECT id, kind, display_name FROM visible_entity"
    args: tuple = ()
    if kind:
        sql += " WHERE kind = ?"
        args = (kind,)
    return [dict(r) for r in conn.execute(sql + " ORDER BY display_name", args)]


def search(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[dict]:
    """Recherche plein texte filtrée par visible_search (jamais l'index brut)."""
    terms = " ".join(f'"{t}"*' for t in query.replace('"', " ").split() if t)
    if not terms:
        return []
    rows = conn.execute(
        """SELECT f.entity_id, v.display_name, f.field, snippet(search_fts, 0, '[', ']', '…', 12) AS snip
           FROM search_fts f JOIN visible_entity v ON v.id = f.entity_id
           WHERE search_fts MATCH ? AND f.rowid IN (SELECT rowid FROM visible_search)
           ORDER BY rank LIMIT ?""", (terms, limit)).fetchall()
    return [dict(r) for r in rows]


def reindex(conn: sqlite3.Connection) -> None:
    """Reconstruit l'index plein texte à partir des tables (pas des vues)."""
    with conn:
        conn.execute("DELETE FROM search_fts")
        conn.execute("INSERT INTO search_fts(body, entity_id, field, ref_id) "
                     "SELECT canonical_name, id, 'name', NULL FROM entity")
        conn.execute("INSERT INTO search_fts(body, entity_id, field, ref_id) "
                     "SELECT neutral_alias, id, 'alias', NULL FROM entity WHERE neutral_alias IS NOT NULL")
        conn.execute("INSERT INTO search_fts(body, entity_id, field, ref_id) "
                     "SELECT body, entity_id, 'content', id FROM activity_content")
        conn.execute("INSERT INTO search_fts(body, entity_id, field, ref_id) "
                     "SELECT value_json, entity_id, 'claim', id FROM claim")
