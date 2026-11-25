"""Classification spoiler par règles (avant toute IA).

Règle d'or : en cas de doute -> 'unknown' (masqué, mis en quarantaine).
Seuls les champs techniques sans portée narrative sont auto-évalués.
"""
from __future__ import annotations

import re

# Champs purement techniques : aucune portée narrative.
SAFE_FIELDS = {
    "manufacturer", "class", "seats", "drivetrain", "gears", "weight_kg", "model_year",
    "based_on", "price", "sell_price_stolen", "speed", "acceleration", "handling_road",
    "handling_offroad", "strength", "style", "era", "security", "access", "tracker",
    "can_register", "standout_set", "specialist", "body_condition", "game_edition",
    "damage", "fire_rate", "range", "accuracy", "recoil", "capacity", "base_model",
    "weapon_handling", "purchase_from", "moddable", "ammo_upgrade",
}

# Champs textuels : auto-évalués seulement si le texte est « sûr ».
TEXT_FIELDS = {"how_to_unlock", "location_text", "description"}

SAFE_TEXT = re.compile(
    r"^(?:\s*(?:ultimate|special|standard|collector'?s?)\s+edition(?:\s+reward)?\.?\s*"
    r"|\s*(?:buy|purchase|available)\b[^.]{0,80}(?:website|dealership|store|shop)\.?\s*"
    r"|\s*(?:spawns?|found)\s+(?:randomly\s+)?(?:in|on|around)\s+(?:traffic|the streets|parking lots)\.?\s*)+$",
    re.I,
)
NARRATIVE_HINTS = re.compile(
    r"\b(mission|chapter|chapitre|story|after|complete|completing|reward from|unlock(?:ed)? by|"
    r"death|dies|kill|betray|ending|finale|penthouse|'s\b|’s\b)", re.I)


def field_spoiler_status(field: str, value: object) -> str:
    if field in SAFE_FIELDS:
        return "evaluated"
    if field in TEXT_FIELDS and isinstance(value, str):
        if SAFE_TEXT.match(value) and not NARRATIVE_HINTS.search(value):
            return "evaluated"
    return "unknown"


CATALOG_KINDS = {"vehicle_model", "vehicle_variant", "weapon_model", "weapon_variant", "mod_option"}


def entity_spoiler_status(kind: str, name: str) -> str:
    """Les fiches catalogue (véhicules/armes) sont visibles ; le reste en quarantaine."""
    return "evaluated" if kind in CATALOG_KINDS else "unknown"


def name_status(kind: str, name: str) -> str:
    """« Raul's Tempesta », « Dante's Vitello » : le nom révèle un personnage -> alias neutre."""
    if kind in CATALOG_KINDS and not re.search(r"['’]s\b", name):
        return "safe"
    return "unknown"


# Indices narratifs en français (textes de secrets/quêtes).
FR_NARRATIVE = re.compile(
    r"\b(mission|chapitre|histoire|scénario|après avoir|termin|finit|se termine|récompense|"
    r"dénouement|fin de|mort|meurt|tué|trahi|trahison|révél|boss|chaîne de quêtes|débloqu|"
    r"post-?générique|épilogue)", re.I)


def secret_text_status(text: str | None) -> str:
    """Texte FR d'un secret : 'evaluated' seulement sans aucun indice narratif."""
    if not text:
        return "unknown"
    return "unknown" if FR_NARRATIVE.search(text) else "evaluated"


# Catégories de marqueurs dont l'existence ou le nom révèle l'histoire ou un personnage :
# masquées jusqu'à évaluation manuelle (ou mapping de progression).
SENSITIVE_CATEGORIES = re.compile(
    r"chapitre|final|mission|contact|criminel|troph|manquable|épilogue|epilogue|histoire|story|personnage", re.I)


def category_status(category: str | None) -> str:
    return "unknown" if category and SENSITIVE_CATEGORIES.search(category) else "evaluated"


# Points d'intérêt : on écarte les commerces/services du quotidien, déjà visibles en jeu
# (distributeurs, nourriture, boissons, vêtements, transports…). Ammu-Nation, tuning,
# Pay 'n' Spray, garages à vendre, stands de tir restent : ils ont un vrai intérêt.
NON_POI = re.compile(
    r"arrêt de bus|^gare$|ferry|distributeur|borne de recharge|street food|fast-food|cafés|^bar$|^club$|alcool|"
    r"supérette|électronique|station-service|souvenirs|vêtements|tenues|décontracté|friperie|chaussures|coiffure|"
    r"tatouage|prêts|lavage|location|troc|delights|hit 'n' run|animal crackers|san4san|kolt|guardia|ptt youngin|"
    r"kingfishers|^m7$|polilla|nineinine|top fun drones|bus", re.I)


def is_poi(category: str | None) -> bool:
    return not (category and NON_POI.search(category))
