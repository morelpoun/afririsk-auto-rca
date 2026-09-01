# Architecture — AfriRisk (CIMA, multi-branches)

## Vue d'ensemble

```text
frontend/            interface statique (formulaire de cotation, dashboard)
      │  fetch() JSON
      ▼
backend/app/
  main.py            routes FastAPI, orchestration
  schemas.py          contrats d'entrée/sortie (Pydantic)
  actuarial/           moteurs de tarification, un par branche
    glm_utils.py          décomposition GLM partagée (auto + habitation)
    data_simulation.py   portefeuille auto synthétique documenté
    pricing.py            auto : GLM fréquence (Poisson) + sévérité (Gamma)
    habitation_data_simulation.py  portefeuille habitation synthétique
    habitation_pricing.py           habitation : même principe que pricing.py
    bonus_malus.py         grille de coefficient par défaut (auto, non réglementaire)
  regulatory/          couche réglementaire configurable
    rules.py              modèle de règle + contrôle de tarif minimum
    cima_countries.py       table des 15 pays CIMA (devise, zone monétaire)
  database/            persistance
    models.py             customers, vehicles, policies, claims, pricing_results
    session.py             SQLite (dev/tests) ou PostgreSQL (docker-compose)
    crud.py                 opérations de souscription/sinistres/KPI
  ml/                  benchmarks (pas utilisés par /tarif en production)
    tweedie.py             GLM Tweedie
    xgboost_model.py        XGBoost (objectif Tweedie)
    explain.py               explicabilité SHAP
    comparison_results.json  résultat de la dernière comparaison, exposé par GET /models
```

## Principe directeur : le moteur actuariel est séparé de l'API, un par branche

`main.py` ne calcule jamais de prime lui-même. Il appelle
`ActuarialEngine.price(contrat)` (auto, `actuarial/pricing.py`) ou
`HabitationActuarialEngine.price(contrat)` (habitation,
`actuarial/habitation_pricing.py`), qui renvoient chacun un résultat complet
(fréquence, sévérité, prime pure, chargements, prime commerciale,
décomposition explicative). Chaque branche a son propre moteur, ses propres
formules GLM et son propre portefeuille synthétique — seule la mécanique de
décomposition explicative (`glm_utils.py`) est partagée. Ajouter une branche
ne touche donc pas aux branches existantes.

## Cycle de vie d'une cotation (`POST /tarif`)

1. Validation du contrat entrant (`schemas.ContractInput`, avec `country` parmi
   les 15 pays CIMA)
2. `ActuarialEngine.price(...)` → fréquence, sévérité, prime pure, prime
   commerciale (**identique quel que soit le pays** — voir docs/regulatory.md)
3. `regulatory.check_minimum_tariff(contract.country, ...)` → conformité au
   tarif minimum configuré pour ce pays, s'il existe ; `currency_for_country`
   détermine la devise affichée
4. Écriture d'une ligne dans `pricing_results` : entrées, sorties, version du
   modèle (`model_version`), version réglementaire appliquée — pour pouvoir
   reconstruire exactement un calcul passé
5. Réponse JSON à l'appelant (frontend ou tout autre client de l'API)

## Persistance

Par défaut, l'application utilise SQLite (`afririsk.db`, fichier local, exclu
du dépôt) — zéro configuration pour développer ou lancer les tests.
`docker-compose.yml` démarre un PostgreSQL réel et positionne `DATABASE_URL`
en conséquence, pour un environnement proche de la production.

Depuis v0.3, `POST /policies` alimente réellement `customers`, `vehicles`,
`policies` (et `pricing_results`, avec `policy_id` renseigné) ; `POST /claims`
alimente `claims`. Voir `docs/claims.md` pour le détail du parcours de
souscription, des sinistres et des KPI de rentabilité qui en découlent.

## Modèles benchmark (`ml/`, v0.2)

`ml/tweedie.py` et `ml/xgboost_model.py` (+ `ml/explain.py` pour SHAP) ne sont
**pas** importés par `main.py` : la comparaison se fait hors ligne via
`scripts/compare_models.py`, qui écrit `ml/comparison_results.json`. L'API de
production reste donc légère (pas besoin de `xgboost`/`shap` pour servir
`/tarif`) ; `GET /models` se contente de lire ce fichier JSON s'il existe.
Voir `docs/ml_methodology.md` pour la méthodologie et le résultat de
référence.

## Ce qui n'est pas encore là (volontairement)

- Authentification / RBAC
- Migrations de schéma (Alembic) — pour l'instant `Base.metadata.create_all()`
  au démarrage, suffisant tant que le schéma n'est pas encore stabilisé
- Frontend React/Next.js — l'interface actuelle est volontairement minimale
  (HTML/JS statique) pour rester démontrable sans toolchain supplémentaire

Voir `docs/cahier_des_charges.md` pour la feuille de route complète.
