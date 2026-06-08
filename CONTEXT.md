# EV Route Planner — Context de reprise

> Ce fichier permet de reprendre le projet dans une nouvelle conversation Claude
> sans perdre le contexte accumulé. À lire en premier.

## 1. Où on en est

App **Qivia EV Route Planner** — planificateur de trajets pour véhicules
électriques avec arrêts de recharge optimisés. Fonctionnel et en prod sur
Streamlit Cloud. Pipeline complet ~13s (limite pratique du tier gratuit, dominée
par la latence HERE).

- **Repo local** : `/Users/hugo/ev-route-planner/`
- **Streamlit Cloud** : https://ev-route-planner-arthur.streamlit.app/
- **PWA wrapper (GitHub Pages)** : https://athurpiat.github.io/ev-route-planner/
- **User** : Arthur Piat (`arthur.piat23@gmail.com`)

## 2. Architecture

```
app.py              Streamlit principal — wizard input → loading → result,
                    thème Qivia, gate password, géoloc, dialog départ.
providers.py        Modèle Tesla M3 LR, DRIVING_STYLES, fetch HERE+TomTom.
routing.py          plan_trip(mode="fast"|"eco"), ChargingStop, TripPlan.
enrichment.py       Weather (Open-Meteo) + elevation (OpenTopoData) parallèles.
stations.py         IRVE data.gouv.fr (~140k bornes), corridor vectorisé numpy.
pricing.py          OPERATOR_PRICES + parse tarification IRVE (defensive).
availability.py     TomTom EV Search + chargingAvailability, cache 2 min.
docs/index.html     PWA wrapper GitHub Pages (splash + redirect Streamlit).
.streamlit/         config.toml (dark theme #5FFFA7) + secrets (cloud only).
```

## 3. Secrets (Streamlit Cloud → Settings → Secrets, PAS dans le code)

```toml
HERE_API_KEY = "..."
TOMTOM_API_KEY = "..."
ACCESS_PASSWORD_HASH = "sha256 du mot de passe"
```

## 4. Voiture / point de départ hardcodés

- **Modèle** : Tesla Model 3 LR (`TESLA_M3_LR` dans `providers.py`), 75 kWh,
  consumption_curve, max DC 250 kW.
- **Charge par défaut** : 67%.
- **Adresse voiture** : `VEHICLE_LOCATION_LABEL = "52 rue de Picpus, 75012 Paris"`
  → `VEHICLE_LOCATION_COORDS = "48.846800,2.394500"`.
- **Styles** : Souple 0.85× / Normal 1.0× / Dynamique 1.18×.

## 5. UX clé — Départ "Google Maps style"

État courant (juste codé, **pas encore pushé**) :

- Bouton-cartouche en mode `gps` ou `car` affichant l'adresse + chevron `▾`.
  Clic → ouvre `st.dialog`.
- Dialog : 3 options
  1. `📍 Votre position (adresse géoloc)` (si dispo)
  2. `🚗 Votre voiture (52 rue de Picpus…)`
  3. `✏️ Saisir une adresse` → set `origin_mode = "type"` puis `st.rerun()`
     (dialog se ferme).
- Mode `type` : un `st_searchbox` (photon) s'affiche dans la page principale,
  plus un petit bouton `Changer la source` pour rouvrir le dialog.

Variables session : `origin_mode` (`gps`/`car`/`type`), `geoloc_coords`,
`geoloc_label`, `typed_origin_coords`.

Titre : `"Bonjour Arthur, où va-t-on ?"` (logo au-dessus, pas en colonne).

## 6. Pipeline résultat

- 2 toggles : **Rapide / Économique** × **Avec / Sans péage** → 4 variantes.
- Variante par défaut (fast+toll) calculée d'abord, autres en threads de fond.
- Métriques : durée, conso, coût recharge, péage, SoC arrivée.
- Map Folium dark CartoDB + arrêts numérotés + popups (pas de cards).
- Enrichissement météo + élévation appliqué sur chaque variante.

## 7. Performance — état actuel

- ~13s typique. Plafond pratique du free tier.
- Optims faites : HERE x2 en parallèle (toll/no-toll), météo `ThreadPoolExecutor`,
  élévation batch OpenTopoData (60 points max), corridor IRVE haversine
  vectorisé numpy (~50× plus rapide qu'avant), TomTom EV Search caché 2 min.
- Bottleneck restant : HERE Routing API ~5-8s par requête.

## 8. Contraintes / trade-offs acceptés

- **Footer "Built with Streamlit"** non supprimable sur free tier — accepté.
- **PWA iOS** : redirect cross-origin github.io → streamlit.app casse le mode
  standalone (chrome de Safari réapparaît). Documenté, pas de fix gratuit.
- **iOS session_state** se vide → on persiste l'auth via query param `?auth=ok`.
- **Géoloc** via `streamlit-js-eval` `get_geolocation()`.

## 9. Bugs résolus notables (pour ne pas y retomber)

- TomTom field : `batteryConsumptionInkWh` (pas `consumptionInkWh`).
- `RoutePoint.kwh_consumed_from_start` — unclamped, sinon planner croit pouvoir
  finir en 1 stop dès que la SoC affichée tape 0.
- IRVE CSV : filtrer sur `etalab/schema-irve-statique` (sinon on chope les
  rapports de validation).
- `parse_irve_tarification` et `estimate_price_per_kwh` : `isinstance(x, str)`
  obligatoire (pandas met des `float('nan')` partout).
- `enrich_route` doit recopier `total_duration_s` et `total_toll_eur` dans le
  `RouteResult` final.
- `st.popover` ne se ferme pas sur clic interne → utiliser `st.dialog` +
  `st.rerun()`.

## 10. À faire en reprenant

1. **Commit + push** des dernières modifs du départ :
   ```bash
   cd /Users/hugo/ev-route-planner
   git status
   git add app.py
   git commit -m "Départ dialog: 'Saisir une adresse' route vers searchbox principale"
   git push
   ```
2. **Tester sur mobile** une fois Streamlit Cloud redéployé (~30s après push).
3. Le user a dit "on reste comme ça pour l'instant" — donc pas de nouvelle
   feature à pousser de soi-même.

## 11. Fichiers à lire en priorité dans une nouvelle conv

1. `CONTEXT.md` (ce fichier).
2. `app.py` — gros fichier (~1100 lignes), c'est là que vit toute l'UX.
3. `providers.py` + `routing.py` — pour comprendre le modèle EV et le planner.
4. Les autres modules au cas par cas selon la tâche.

## 12. Stack rapide pour réinstaller

```bash
cd /Users/hugo/ev-route-planner
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Pour run local, créer .streamlit/secrets.toml avec les 3 clés (cf. §3).
streamlit run app.py
```
