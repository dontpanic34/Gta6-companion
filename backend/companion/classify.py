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


def entity_spoiler_status(kind: str, name: str) -> str:
    """Les noms de véhicules/armes sont publics (vitrine du jeu) ; le reste en quarantaine."""
    if kind in {"vehicle_model", "vehicle_variant", "weapon_model", "weapon_variant", "mod_option"}:
        # « Raul's Tempesta », « Dante's Vitello » : le nom révèle un personnage.
        if re.search(r"['’]s\b", name):
            return "unknown"
        return "evaluated"
    return "unknown"
