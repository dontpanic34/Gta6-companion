"""Connecteur GTA Town (gtatown.com/creators/data) — exports JSON officiels, licence CC BY 4.0.

Attribution obligatoire : « Source: gtatown.com ». Chaque ligne garde l'URL de sa page.
Les images (© Rockstar Games) ne sont PAS récupérées : la licence couvre les données, pas les visuels.
Coordonnées : map_x/map_y sont en demi-unités, origine en haut à gauche ;
  x_jeu = map_x / 2 − 16384, y_jeu = 16384 − map_y / 2 (calé sur 330 repères gtadb, écart médian < 2).
"""
from __future__ import annotations

import json

SOURCE_ID = "gtatown"
BASE = "https://gtatown.com/creators/data"
DATASETS = ["vehicles", "weapons", "missions", "cheats", "trophies", "challenges", "collectibles", "locations"]


def to_game(mx, my):
    if mx is None or my is None:
        return None
    return mx / 2 - 16384, 16384 - my / 2


def fetch_all(client, max_age: float = 20 * 3600) -> dict[str, dict]:
    """Un fichier par jeu de données ; relu au plus une fois toutes les 20 h (ETag sinon)."""
    out = {}
    for name in DATASETS:
        r = client.get(f"{BASE}/{name}.json", max_age=max_age)
        d = json.loads(r.text)
        if d.get("licence") != "CC BY 4.0":   # licence changée : on n'importe plus rien de ce fichier
            raise PermissionError(f"Licence inattendue pour {name} : {d.get('licence')}")
        out[name] = d
    return out


# Types GTA Town -> catégories françaises de la carte (mêmes noms que l'existant quand ils existent)
COLLECTIBLE_CAT = {
    "Collectible card": "Carte à collectionner", "Standout vehicle": "Véhicule d’exception", "Rare car": "Véhicules rares",
    "Vehicle spawn": "Apparition de véhicule", "Girlypop": "Véhicule d’exception", "1010 mural": "1010 Mural",
    "Under the bridge": "Sous le pont", "Stunt jump": "Saut spectaculaire", "Knife flight": "Vol en rase-mottes",
    "Base jump": "Saut en base jump", "Basketball hoop": "Panier de basket", "Safe": "Coffre-fort",
    "Magazine": "Magazine", "Weapon pickup": "Armes cachées et uniques", "Unique weapon": "Armes cachées et uniques",
    "Meteorite fragment": "Fragment de météorite", "Hidden package": "Paquet caché", "Ahol street art": "Street art Ahol",
    "Cocaine flamingo": "Flamant de cocaïne", "Smash 'n' Grab": "Smash 'n' Grab", "WAiNK curiosity": "Curiosité",
    "WAiNK landmark": "Monument", "WAiNK sculpture": "Sculpture", "Waink no flusher": "Curiosité",
    "Easter egg": "Easter eggs", "Bank job": "Braquage de banque", "Money spot": "Argent et caches",
    "Illegal operation": "Activité illégale", "Yellow loot box": "Caisse jaune", "Meditation spot": "Lieux de méditation",
    "Payday loan store": "Prêts express", "Book swap": "Troc de livres", "Treasure": "Trésors et sous-marin",
    "Message in a bottle": "Message dans une bouteille", "Glitch": "Astuces et mécaniques", "Money glitch": "Astuces et mécaniques",
    "Secret area": "Lieux cachés",
}
CATEGORY_DEFAULT = {"Cash": "Argent et caches", "Collectibles": "Objet à collectionner", "Secrets": "Easter eggs",
                    "Weapons": "Armes cachées et uniques", "Free cars": "Véhicule gratuit", "Stunts": "Saut spectaculaire"}
# Lieux : seuls les vrais points d'intérêt (les bâtiments génériques restent hors carte)
LOCATION_CAT = {"Landmarks": "Monument", "Leisure": "Loisirs", "Hotels": "Hôtel", "Nature": "Nature",
                "Food & drink": "Restaurant", "Shops": "Boutique"}

VEHICLE_TYPE_FR = {"car": "Voiture", "motorcycle": "Moto", "bike": "Vélo", "bicycle": "Vélo", "boat": "Bateau",
                   "plane": "Avion", "helicopter": "Hélicoptère", "truck": "Camion", "trailer": "Remorque"}


def collectible_category(e: dict) -> str:
    return COLLECTIBLE_CAT.get(e.get("type") or "") or CATEGORY_DEFAULT.get(e.get("category") or "", e.get("category") or "Divers")
