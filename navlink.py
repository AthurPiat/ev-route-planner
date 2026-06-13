"""Détourne Google Maps comme moteur de navigation.

La rupture : on n'écrit AUCUN turn-by-turn. Le cerveau Python (déjà écrit)
calcule où/quand recharger, puis on remet à Google Maps un deeplink prêt à
rouler, avec la/les borne(s) en waypoint. Sur un téléphone, le lien ouvre
l'app Google Maps directement en mode navigation.
"""
from __future__ import annotations

from urllib.parse import urlencode

from routing import ChargingStop


def gmaps_nav_url(
    origin: tuple[float, float],
    destination: tuple[float, float],
    stops: list[ChargingStop] | None = None,
) -> str:
    """Deeplink universel Google Maps Directions (api=1).
    Ouvre l'app Google Maps en navigation sur iOS/Android."""
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
    return "https://www.google.com/maps/dir/?" + urlencode(params)


def qr_url(data: str, size: int = 240) -> str:
    """QR sans dépendance (API publique goqr.me). On scanne le QR affiché à
    l'écran de démo → le téléphone lance la nav Google Maps droit sur la borne
    choisie par le cerveau. Aucune app à installer."""
    q = urlencode({"size": f"{size}x{size}", "data": data})
    return f"https://api.qrserver.com/v1/create-qr-code/?{q}"
