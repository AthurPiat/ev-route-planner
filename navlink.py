"""Détourne Google Maps comme moteur de navigation.

La rupture : on n'écrit AUCUN turn-by-turn. Le cerveau Python (déjà écrit)
calcule où/quand recharger, puis on remet à Google Maps un deeplink prêt à
rouler, avec la/les borne(s) en waypoint. Sur un téléphone, le lien ouvre
l'app Google Maps directement en mode navigation.

Pour afficher un *nom* d'étape (au lieu de « Repère placé »), on résout un
`place_id` Google pour chaque borne via la Places API — mais uniquement si
Google place ce point à < ~350 m de la borne réelle. Sinon on retombe sur les
coordonnées exactes : la précision de navigation n'est jamais sacrifiée.
"""
from __future__ import annotations

import math
from urllib.parse import urlencode

import requests

from routing import ChargingStop


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance en mètres entre deux points (formule de haversine)."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def find_place_id(
    lat: float,
    lng: float,
    query: str,
    api_key: str,
    max_dist_m: float = 350.0,
) -> str | None:
    """Résout un `place_id` Google pour une borne, ancré sur sa position.

    On interroge « Find Place From Text » biaisé sur un cercle de 300 m autour
    de la borne, puis on VÉRIFIE que le candidat retourné est bien à
    < `max_dist_m` des coordonnées réelles. Sinon → None (on gardera les
    coordonnées exactes pour ne pas dégrader la navigation).
    """
    if not api_key or not query:
        return None
    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/place/findplacefromtext/json",
            params={
                "input": query,
                "inputtype": "textquery",
                "fields": "place_id,geometry",
                "locationbias": f"circle:300@{lat:.6f},{lng:.6f}",
                "key": api_key,
            },
            timeout=8,
        )
        r.raise_for_status()
        candidates = r.json().get("candidates", [])
        if not candidates:
            return None
        best = candidates[0]
        loc = best.get("geometry", {}).get("location", {})
        c_lat, c_lng = loc.get("lat"), loc.get("lng")
        if c_lat is None or c_lng is None:
            return None
        if _haversine_m(lat, lng, c_lat, c_lng) > max_dist_m:
            return None  # trop loin : on ne fait pas confiance au nom
        return best.get("place_id") or None
    except Exception as e:  # réseau, quota, etc. → fallback silencieux
        print(f"[navlink.find_place_id] {e}")
        return None


def gmaps_nav_url(
    origin: tuple[float, float],
    destination: tuple[float, float],
    stops: list[ChargingStop] | None = None,
    stop_place_ids: list[str | None] | None = None,
    destination_place_id: str | None = None,
) -> str:
    """Deeplink universel Google Maps Directions (api=1).
    Ouvre l'app Google Maps en navigation sur iOS/Android.

    Si `stop_place_ids` est fourni ET complet (un id non vide par étape, dans
    l'ordre), on ajoute `waypoint_place_ids` pour que Google affiche le *nom*
    des bornes au lieu de « Repère placé ». Idem pour `destination_place_id`.
    Les coordonnées restent toujours présentes : précision garantie.
    """
    params = {
        "api": "1",
        "origin": f"{origin[0]:.6f},{origin[1]:.6f}",
        "destination": f"{destination[0]:.6f},{destination[1]:.6f}",
        "travelmode": "driving",
        "dir_action": "navigate",
    }
    if stops:
        # Google Maps api=1 accepte plusieurs waypoints séparés par '|'.
        params["waypoints"] = "|".join(f"{s.lat:.6f},{s.lng:.6f}" for s in stops)
        # On n'aligne les place_ids QUE s'ils couvrent toutes les étapes :
        # Google exige une correspondance 1:1 et dans le même ordre.
        if (
            stop_place_ids
            and len(stop_place_ids) == len(stops)
            and all(stop_place_ids)
        ):
            params["waypoint_place_ids"] = "|".join(stop_place_ids)
    if destination_place_id:
        params["destination_place_id"] = destination_place_id
    return "https://www.google.com/maps/dir/?" + urlencode(params)


def qr_url(data: str, size: int = 240) -> str:
    """QR sans dépendance (API publique goqr.me). On scanne le QR affiché à
    l'écran de démo → le téléphone lance la nav Google Maps droit sur la borne
    choisie par le cerveau. Aucune app à installer."""
    q = urlencode({"size": f"{size}x{size}", "data": data})
    return f"https://api.qrserver.com/v1/create-qr-code/?{q}"
